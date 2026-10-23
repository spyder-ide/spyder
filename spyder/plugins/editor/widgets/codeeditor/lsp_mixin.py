# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""
Editor mixin and utils to manage connection with the LSP
"""

# Standard library imports
from __future__ import annotations
import functools
import logging
import random
import re
import typing as typ

# Third party imports
from lsprotocol import types as lsp
from qtpy.QtCore import (
    QEventLoop,
    Qt,
    QTimer,
    QThread,
    Signal,
    Slot,
)
from qtpy.QtGui import QColor, QTextCursor
from three_merge import merge

# Local imports
from spyder.api.asyncdispatcher import AsyncDispatcher, DispatcherFuture
from spyder.config.base import running_under_pytest
from spyder.plugins.editor.panels.utils import (
    merge_folding,
    collect_folding_regions,
)
from spyder.plugins.editor.utils.editor import BlockUserData
from spyder.plugins.languageservices.api.errors import DocumentNotOpenError
from spyder.plugins.languageservices.api.languages import Language
from spyder.plugins.languageservices.api.provider import FEATURE_METHODS
from spyder.plugins.languageservices.api.uri import path_as_uri, uri_as_path
from spyder.utils import sourcecode

if typ.TYPE_CHECKING:
    from spyder.plugins.languageservices.plugin import LanguageServices
    from spyder.plugins.editor.widgets.codeeditor.stack_mixin import (
        EditBlock,
        TextDelta,
    )


logger = logging.getLogger(__name__)

# Regexp to detect noqa inline comments.
NOQA_INLINE_REGEXP = re.compile(r"#?noqa", re.IGNORECASE)

# LSP method -> LanguageServices plugin method answering it.
PLUGIN_METHODS = {
    **FEATURE_METHODS,
    lsp.TEXT_DOCUMENT_DID_OPEN: "open_document",
    lsp.TEXT_DOCUMENT_DID_CHANGE: "change_document",
    lsp.TEXT_DOCUMENT_DID_SAVE: "save_document",
    lsp.TEXT_DOCUMENT_DID_CLOSE: "close_document",
}


def request(req=None, method=None, requires_response=True):
    """Call ``req`` and send its result to the language services plugin."""
    if req is None:
        return functools.partial(
            request, method=method, requires_response=requires_response
        )

    @functools.wraps(req)
    def wrapper(self, *args, **kwargs):
        if not self.completions_available:
            return
        params = req(self, *args, **kwargs)
        if params is not None:
            self.emit_request(method, params, requires_response)

    return wrapper


def handles(method_name):
    """Mark a method as the handler of the responses to ``method_name``."""

    def wrapper(func):
        func._handle = method_name
        return func

    return wrapper


def class_register(cls):
    """Build ``cls.handler_registry`` from the methods marked by ``handles``."""
    cls.handler_registry = {}
    for method_name in dir(cls):
        method = getattr(cls, method_name)
        if hasattr(method, "_handle"):
            cls.handler_registry[method._handle] = method_name
    return cls


def schedule_request(
    req=None, method=None, requires_response=True, cancel_previous=False
):
    """Call function req and then emit its results to the completion server."""
    if req is None:
        return functools.partial(
            schedule_request,
            method=method,
            requires_response=requires_response,
            cancel_previous=cancel_previous,
        )

    @functools.wraps(req)
    def wrapper(self, *args, _cancel_previous=False, **kwargs):
        if _cancel_previous or cancel_previous:
            pending_reqeusts = self._pending_server_requests
            index = next(
                (
                    i
                    for i, item in enumerate(pending_reqeusts)
                    if item[0] == method
                ),
                None,
            )
            if index is not None:
                self._pending_server_requests = (
                    pending_reqeusts[:index] + pending_reqeusts[index + 1 :]
                )

        if not self.completions_available:
            return

        params = req(self, *args, **kwargs)
        if params is not None:
            self._pending_server_requests.append(
                (method, params, requires_response)
            )
            self._server_requests_timer.start()

    return wrapper


class LSPHandleError(Exception):
    """Error raised if there is an error handling an LSP response."""


@class_register
class LSPMixin:
    # -- LSP constants
    # Timeouts (in milliseconds) to sychronize symbols and folding after
    # linting results arrive, according to the number of lines in the file.
    SYNC_SYMBOLS_AND_FOLDING_TIMEOUTS = {
        # Lines: Timeout
        500: 600,
        1500: 800,
        2500: 1000,
        6500: 1500,
    }

    # Timeout (in milliseconds) to send pending requests to LSP server
    LSP_REQUESTS_DELAY = 50

    # Requests whose results describe the document as a whole, so a response
    # is only meaningful while it's the answer to the last request we sent.
    # See _is_outdated_response.
    WHOLE_DOCUMENT_REQUESTS = frozenset({
        lsp.TEXT_DOCUMENT_DOCUMENT_SYMBOL,
        lsp.TEXT_DOCUMENT_FOLDING_RANGE,
    })

    # -- LSP signals
    #: Signal emitted when a response is received from the completion plugin
    # For now it's only used on tests, but it could be used to track
    # and profile completion diagnostics.
    completions_response_signal = Signal(str, object)

    #: Signal to display object information on the Help plugin
    sig_display_object_info = Signal(str, bool)

    #: Signal only used for tests
    # TODO: Remove it!
    sig_signature_invoked = Signal(object)

    #: Signal emitted when processing code analysis warnings is finished
    sig_process_code_analysis = Signal()

    #: Signal emitted to tell cloned editors that they need to update their
    # code folding.
    sig_update_code_folding = Signal(tuple)

    # Used to start the status spinner in the editor
    sig_start_operation_in_progress = Signal()

    # Used to start the status spinner in the editor
    sig_stop_operation_in_progress = Signal()

    def __init__(self):
        # Request symbols and folding after a timeout.
        # See: process_diagnostics
        # Connecting the timeout signal is performed in document_did_open()
        self._timer_sync_symbols_and_folding = QTimer(self)
        self._timer_sync_symbols_and_folding.setSingleShot(True)
        self.blockCountChanged.connect(
            self.set_sync_symbols_and_folding_timeout)

        # LSP requests handling
        # self.textChanged.connect(self._schedule_document_did_change)
        self._pending_server_requests = []
        self._server_requests_timer = QTimer(self)
        self._server_requests_timer.setSingleShot(True)
        self._server_requests_timer.setInterval(self.LSP_REQUESTS_DELAY)
        self._server_requests_timer.timeout.connect(
            self._process_server_requests)

        self.sig_document_change.connect(self._handle_document_change)
        self.new_text_set.connect(self._handle_new_text_set)

        # Code Folding
        self.code_folding = True
        self.update_folding_thread = QThread(None)
        self.update_folding_thread.finished.connect(
            self._finish_update_folding)

        # Autoformat on save
        self.format_on_save = False
        self.format_eventloop = QEventLoop(None)
        self.format_timer = QTimer(self)
        self.__cursor_position_before_format = 0

        # Outline explorer
        self.oe_proxy = None

        # Diagnostics
        self.update_diagnostics_thread = QThread(None)
        self.update_diagnostics_thread.run = self.set_errors
        self.update_diagnostics_thread.finished.connect(
            self.finish_code_analysis)
        self._diagnostics = []

        self.leading_whitespaces = {}

        # Other attributes
        self.filename = None
        self.file_uri = None
        self.position_encoding = lsp.PositionEncodingKind.Utf16
        self.completions_available = False
        self.save_include_text = True
        self.open_close_notifications = True
        self.sync_mode = lsp.TextDocumentSyncKind.Incremental
        self.will_save_notify = False
        self.will_save_until_notify = False
        self.enable_hover = False
        self.auto_completion_characters = []
        self.resolve_completions_enabled = False
        self.signature_completion_characters = []
        self.go_to_definition_enabled = False
        self.find_references_enabled = False
        self.highlight_enabled = False
        self.formatting_enabled = False
        self.range_formatting_enabled = False
        self.document_symbols_enabled = False
        self.formatting_characters = []
        self.completion_args = None
        self.folding_supported = False
        self._folding_info = None
        self.is_cloned = False
        self.operation_in_progress = False
        self.formatting_in_progress = False
        self.symbols_sync_version = 0
        self.folding_sync_version = 0
        self.pyflakes_linting_enabled = True

        self._text_version = 0

        # Number of requests already sent to the server that are still waiting
        # for a response, per method. Only tracked for WHOLE_DOCUMENT_REQUESTS.
        self._requests_in_flight = {}

        # LanguageServices plugin answering the requests (None means no services)
        self.language_services: LanguageServices | None = None

        # Last future issued per request method. A new request cancels it.
        self._futures: dict[str, DispatcherFuture] = {}

    @property
    def text_version(self):
        """Return the current text version."""
        return self._text_version

    # ---- Helper private methods
    # -------------------------------------------------------------------------
    def _process_server_requests(self):
        """Process server requests."""
        # Send pending requests
        for method, params, requires_response in self._pending_server_requests:
            if method in self.WHOLE_DOCUMENT_REQUESTS:
                self._requests_in_flight[method] = (
                    self._requests_in_flight.get(method, 0) + 1
                )
            self.emit_request(method, params, requires_response)

        # Clear pending requests
        self._pending_server_requests = []

    def _is_outdated_response(self, method: str, sync_version: int) -> bool:
        """
        Check if the response for `method` doesn't describe the current text.

        The response is considered outdated if the current text version is
        greater than `sync_version` and there are no pending requests for `method`.

        Parameters
        ----------
        method: str
            LSP method for which the response was received.
        sync_version: int
            Text version for which the request was sent.
        """
        if self._requests_in_flight.get(method, 0) > 0:
            return True

        if any(
            pending[0] == method for pending in self._pending_server_requests
        ):
            return True

        return self.text_version > sync_version

    def _get_edit_range(self, delta: TextDelta) -> lsp.Range:
        """Get the range of text removed in a text change."""
        start = lsp.Position(line=delta.line, character=delta.col)

        if not delta.removed_text:
            return lsp.Range(start=start, end=start)

        return lsp.Range(
            start=start, end=lsp.Position(*delta.get_end_line_col())
        )

    def _handle_document_change(self, edit: EditBlock):
        """Handle document change."""
        self._text_version += 1

        if self.sync_mode == lsp.TextDocumentSyncKind.Incremental:
            self.document_did_change(edit)
        else:
            self.document_did_change(_cancel_previous=True)

        self.do_automatic_completions()

    def _handle_new_text_set(self):
        """Handle full document replacement.

        Notifies the LSP server with the full document text so its view stays
        in sync after a programmatic text replacement that bypasses the normal
        incremental-edit path.
        """
        self._text_version += 1
        self.document_did_change(_cancel_previous=True)
        self.do_automatic_completions()

    # ---- Basic methods
    # -------------------------------------------------------------------------
    @Slot(str, object)
    def handle_response(self, method, params):
        in_flight = self._requests_in_flight.get(method, 0)
        if in_flight:
            self._requests_in_flight[method] = in_flight - 1

        if method in self.handler_registry:
            handler_name = self.handler_registry[method]
            handler = getattr(self, handler_name)
            handler(params)
            # This signal is only used on tests.
            # It could be used to track and profile LSP diagnostics.
            self.completions_response_signal.emit(method, params)

    @property
    def document_uri(self) -> str:
        """``file:`` URI of the edited file."""
        return path_as_uri(self.filename)

    def document_language(self) -> Language | None:
        """Language of the edited file, or ``None`` when Spyder has none."""
        return Language.find(name=self.language)

    def emit_request(self, method, params, requires_response):
        """Send a request or notification to the language services plugin.

        A new request cancels the previous in-flight request of the same
        method. Answers reach :meth:`handle_response` on the Qt thread.
        """
        plugin = self.language_services
        if plugin is None:
            return

        call = getattr(plugin, PLUGIN_METHODS[method])
        if method == lsp.TEXT_DOCUMENT_DID_OPEN:
            future = call(params, self.document_language())
        else:
            future = call(params)

        if not requires_response:
            @AsyncDispatcher.QtSlot
            def on_notification_done(future: DispatcherFuture):
                if future.cancelled():
                    return
                exc = future.exception()
                if exc is not None:
                    self._report_request_error(method, exc)

            future.connect(on_notification_done)
            return

        previous = self._futures.pop(method, None)
        if previous is not None:
            previous.cancel()
        self._futures[method] = future

        @AsyncDispatcher.QtSlot
        def on_response(future: DispatcherFuture):
            # Only handle_response releases the in-flight count, so the paths
            # that skip it (cancellation, errors) must release it themselves or
            # _is_outdated_response stays true forever and symbols/folding stop
            # updating.
            if future.cancelled():
                self._release_in_flight(method)
                return
            if self._futures.get(method) is future:
                del self._futures[method]
            exc = future.exception()
            if exc is not None:
                self._release_in_flight(method)
                self._report_request_error(method, exc)
                return
            try:
                self.handle_response(method, future.result())
            except RuntimeError:
                # The editor was deleted before the answer arrived.
                return

        future.connect(on_response)

    def _release_in_flight(self, method):
        """Drop one tracked in-flight request that did not reach
        handle_response (only WHOLE_DOCUMENT_REQUESTS are tracked)."""
        in_flight = self._requests_in_flight.get(method, 0)
        if in_flight:
            self._requests_in_flight[method] = in_flight - 1

    def _report_request_error(self, method, exc):
        if isinstance(exc, DocumentNotOpenError):
            # The document was closed while the request was in flight.
            logger.debug("%s for closed document: %s", method, exc)
            return
        raise LSPHandleError(
            f"Error while handling {method} for {self.filename}"
        ) from exc

    def manage_lsp_handle_errors(self, message):
        """
        Actions to take when we get errors while handling LSP responses.
        """
        # Raise exception so that handle response errors can be reported to
        # Github
        raise LSPHandleError(message)

    # ---- Configuration and start/stop
    # -------------------------------------------------------------------------
    def start_completion_services(self):
        """Start completion services for this instance."""
        self.completions_available = True

        # Requests sent to a previous server instance will never be answered.
        self._requests_in_flight.clear()

        if self.is_cloned:
            additional_msg = "cloned editor"
        else:
            additional_msg = ""
            self.document_did_open()

        logger.debug(
            "Completion services available for {0}: {1}".format(
                additional_msg, self.filename
            )
        )

    def register_completion_capabilities(
        self, capabilities: lsp.ServerCapabilities
    ):
        """
        Register completion server capabilities.

        Parameters
        ----------
        capabilities: lsp.ServerCapabilities
            Server capabilities reported during LSP initialization.
        """
        if capabilities is None:
            capabilities = lsp.ServerCapabilities()

        tds = capabilities.text_document_sync
        open_close = False
        sync_kind = lsp.TextDocumentSyncKind.None_
        will_save = False
        will_save_wait_until = False
        save_include_text = False

        if (
            capabilities.position_encoding is not None
            and capabilities.position_encoding != self.position_encoding
        ):
            raise LSPHandleError(
                f"Unsupported position encoding: "
                f"{capabilities.position_encoding}"
            )

        if isinstance(tds, lsp.TextDocumentSyncOptions):
            open_close = tds.open_close or False
            sync_kind = tds.change or lsp.TextDocumentSyncKind.None_
            will_save = tds.will_save or False
            will_save_wait_until = tds.will_save_wait_until or False
            save_opt = tds.save
            if isinstance(save_opt, lsp.SaveOptions):
                save_include_text = save_opt.include_text or False
        elif isinstance(tds, lsp.TextDocumentSyncKind):
            sync_kind = tds

        self.open_close_notifications = open_close
        if sync_kind != lsp.TextDocumentSyncKind.None_:
            self.sync_mode = sync_kind
        self.will_save_notify = will_save
        self.will_save_until_notify = will_save_wait_until
        self.save_include_text = save_include_text
        self.enable_hover = bool(capabilities.hover_provider)
        self.folding_supported = bool(capabilities.folding_range_provider)

        cp = capabilities.completion_provider
        self.auto_completion_characters = (
            list(cp.trigger_characters or []) if cp else []
        )
        self.resolve_completions_enabled = bool(cp and cp.resolve_provider)

        shp = capabilities.signature_help_provider
        self.signature_completion_characters = (
            list(shp.trigger_characters or []) if shp else []
        ) + ["="]  # FIXME:

        self.go_to_definition_enabled = bool(capabilities.definition_provider)
        self.find_references_enabled = bool(capabilities.references_provider)
        self.highlight_enabled = bool(
            capabilities.document_highlight_provider
        )
        self.formatting_enabled = bool(
            capabilities.document_formatting_provider
        )
        self.range_formatting_enabled = bool(
            capabilities.document_range_formatting_provider
        )
        self.document_symbols_enabled = bool(
            capabilities.document_symbol_provider
        )

        otf = capabilities.document_on_type_formatting_provider
        if otf:
            self.formatting_characters.append(otf.first_trigger_character)
            self.formatting_characters += list(
                otf.more_trigger_character or []
            )

        if self.formatting_enabled:
            self.sig_refresh_formatting.emit()

        self.completions_available = True

    def stop_completion_services(self):
        logger.debug("Stopping completion services for %s" % self.filename)
        self.completions_available = False

        # Requests that were not answered before stopping the server won't be
        # answered at all.
        self._requests_in_flight.clear()
        self._cancel_pending_futures()

    def _cancel_pending_futures(self):
        for future in self._futures.values():
            future.cancel()
        self._futures.clear()

    @request(method=lsp.TEXT_DOCUMENT_DID_OPEN, requires_response=False)
    def document_did_open(self):
        """Send textDocument/didOpen request to the server."""

        # We need to be sure that this signal is disconnected before trying to
        # connect it below.
        # Note: It can already be connected when the user requires a server
        # restart or when the server failed to start.
        # Fixes spyder-ide/spyder#20679
        try:
            self._timer_sync_symbols_and_folding.timeout.disconnect()
        except (TypeError, RuntimeError):
            pass

        # The connect is performed here instead of in __init__() because
        # notify_close() may have been called (which disconnects the signal).
        # Qt.UniqueConnection is used to avoid duplicate signal-slot
        # connections (just in case).
        #
        # Note: PyQt5 throws if the signal is not unique (= already connected).
        # It is an error if this happens because as per LSP specification
        # `didOpen` “must not be sent more than once without a corresponding
        # close notification send before”.
        self._timer_sync_symbols_and_folding.timeout.connect(
            self.sync_symbols_and_folding, Qt.UniqueConnection
        )

        text = self.get_text_with_eol()
        # TODO: LSP now supports IPython, update this workaround when
        #       using a language server that also supports it.
        if self.is_ipython():
            # Send valid python text to LSP as it doesn't support IPython
            text = self.ipython_to_python(text)
        language = self.document_language()
        if language is None:
            return None
        return lsp.DidOpenTextDocumentParams(
            text_document=lsp.TextDocumentItem(
                uri=self.document_uri,
                language_id=language.language_id,
                version=self.text_version,
                text=text,
            )
        )

    # ---- Symbols
    # -------------------------------------------------------------------------
    @schedule_request(
        method=lsp.TEXT_DOCUMENT_DOCUMENT_SYMBOL, cancel_previous=True
    )
    def request_symbols(self):
        """Request document symbols."""
        if not self.document_symbols_enabled:
            return

        # Ensure document is up to date before requesting symbols
        self._commit_pending_edit()

        if self.oe_proxy is not None:
            self.oe_proxy.emit_request_in_progress()
        self.symbols_sync_version = self.text_version
        return lsp.DocumentSymbolParams(
            text_document=lsp.TextDocumentIdentifier(uri=self.document_uri)
        )

    @handles(lsp.TEXT_DOCUMENT_DOCUMENT_SYMBOL)
    def process_symbols(self, params):
        """Handle symbols response."""
        if self._is_outdated_response(
            lsp.TEXT_DOCUMENT_DOCUMENT_SYMBOL, self.symbols_sync_version
        ):
            # Ignore outdated response
            return
        try:
            symbols = params or []
            self._update_classfuncdropdown(symbols)

            if self.oe_proxy is not None:
                self.oe_proxy.update_outline_info(symbols)
        except RuntimeError:
            # This is triggered when a codeeditor instance was removed
            # before the response can be processed.
            return
        except Exception:
            self.manage_lsp_handle_errors("Error when processing symbols")

    def _update_classfuncdropdown(self, symbols):
        """Update class/function dropdown."""
        symbols = [] if symbols is None else symbols

        if self.classfuncdropdown.isVisible():
            self.classfuncdropdown.update_data(symbols)
        else:
            self.classfuncdropdown.set_data(symbols)

    # ---- Linting and didChange
    # -------------------------------------------------------------------------
    @schedule_request(
        method=lsp.TEXT_DOCUMENT_DID_CHANGE,
        requires_response=False,
    )
    def document_did_change(
        self, edit: EditBlock | None = None
    ):
        """Send textDocument/didChange request to the server."""
        # Cancel formatting
        self.formatting_in_progress = False

        # Don't send request for cloned editors because it's not necessary.
        # The original file should send the request.
        if not self.completions_available or self.is_cloned:
            return

        is_ipython = self.is_ipython()
        linesep = self.get_line_separator()

        if edit:
            content_changes = [
                lsp.TextDocumentContentChangePartial(
                    range=self._get_edit_range(delta),
                    text=self._text_for_server(
                        str(delta.inserted_text).replace("\n", linesep),
                        is_ipython,
                    ),
                )
                for delta in edit.deltas
                if delta.inserted_text or delta.removed_text
            ]
        else:
            content_changes = [
                lsp.TextDocumentContentChangeWholeDocument(
                    text=self._text_for_server(
                        self.get_text_with_eol(), is_ipython
                    )
                )
            ]

        return lsp.DidChangeTextDocumentParams(
            text_document=lsp.VersionedTextDocumentIdentifier(
                uri=self.document_uri, version=self.text_version
            ),
            content_changes=content_changes,
        )

    def _text_for_server(self, text: str, is_ipython: bool) -> str:
        """Convert text to what the server expects to receive."""
        # TODO: LSP now supports IPython, update this workaround when
        #       using a language server that also supports it.
        return self.ipython_to_python(text) if is_ipython else text

    @handles(lsp.TEXT_DOCUMENT_PUBLISH_DIAGNOSTICS)
    def process_diagnostics(self, params):
        """Handle linting response."""
        # The LSP spec doesn't require that folding and symbols
        # are treated in the same way as linting, i.e. to be
        # recomputed on didChange, didOpen and didSave. However,
        # we think that's necessary to maintain accurate folding
        # and symbols all the time. Therefore, we decided to call
        # those requests here, but after a certain timeout to
        # avoid performance issues.
        self._timer_sync_symbols_and_folding.start()

        # Process results (runs in a thread)
        self.process_code_analysis(params or [])

    def set_sync_symbols_and_folding_timeout(self):
        """
        Set timeout to sync symbols and folding according to the file
        size.
        """
        current_lines = self.get_line_count()
        timeout = None

        for lines in self.SYNC_SYMBOLS_AND_FOLDING_TIMEOUTS.keys():
            if (current_lines // lines) == 0:
                timeout = self.SYNC_SYMBOLS_AND_FOLDING_TIMEOUTS[lines]
                break

        if not timeout:
            timeouts = self.SYNC_SYMBOLS_AND_FOLDING_TIMEOUTS.values()
            timeout = list(timeouts)[-1]

        # Add a random number so that several files are not synced at the same
        # time.
        self._timer_sync_symbols_and_folding.setInterval(
            timeout + random.randint(-100, 100)
        )

    def sync_symbols_and_folding(self):
        """
        Synchronize symbols and folding after linting results arrive.
        """
        # Send the pending edit before deciding what is out of sync. Otherwise
        # folding would be requested for the text the server currently has,
        # which we already know is outdated, and its response discarded.
        self._commit_pending_edit()

        if self.text_version > self.folding_sync_version:
            self.request_folding()

        if self.text_version > self.symbols_sync_version:
            self.request_symbols()

    def process_code_analysis(self, diagnostics):
        """Process code analysis results in a thread."""
        self.cleanup_code_analysis()
        self._diagnostics = diagnostics

        # Process diagnostics in a thread to improve performance.
        self.update_diagnostics_thread.start()

    def cleanup_code_analysis(self):
        """Remove all code analysis markers"""
        self.setUpdatesEnabled(False)
        self.clear_extra_selections("code_analysis_highlight")
        self.clear_extra_selections("code_analysis_underline")
        for data in self.blockuserdata_list():
            data.code_analysis = []

        self.setUpdatesEnabled(True)
        # When the new code analysis results are empty, it is necessary
        # to update manually the scrollflag and linenumber areas (otherwise,
        # the old flags will still be displayed):
        self.sig_flags_changed.emit()
        self.linenumberarea.update()

    def set_errors(self):
        """Set errors and warnings in the line number area."""
        try:
            self._process_code_analysis(underline=False)
        except RuntimeError:
            # This is triggered when a codeeditor instance was removed
            # before the response can be processed.
            return
        except Exception:
            self.manage_lsp_handle_errors("Error when processing linting")

    def underline_errors(self):
        """Underline errors and warnings."""
        try:
            # Clear current selections before painting the new ones.
            # This prevents accumulating them when moving around in or editing
            # the file, which generated a memory leakage and sluggishness
            # after some time.
            self.clear_extra_selections("code_analysis_underline")
            self._process_code_analysis(underline=True)
        except RuntimeError:
            # This is triggered when a codeeditor instance was removed
            # before the response can be processed.
            return
        except Exception:
            self.manage_lsp_handle_errors("Error when processing linting")

    def finish_code_analysis(self):
        """Finish processing code analysis results."""
        self.linenumberarea.update()
        if self.underline_errors_enabled:
            self.underline_errors()
        self.sig_process_code_analysis.emit()
        self.sig_flags_changed.emit()

    def errors_present(self):
        """
        Return True if there are errors or warnings present in the file.
        """
        return bool(len(self._diagnostics))

    def _process_code_analysis(self, underline):
        """
        Process all code analysis results.

        Parameters
        ----------
        underline: bool
            Determines if errors and warnings are going to be set in
            the line number area or underlined. It's better to separate
            these two processes for perfomance reasons. That's because
            setting errors can be done in a thread whereas underlining
            them can't.
        """
        document = self.document()
        if underline:
            first_block, last_block = self.get_buffer_block_numbers()

        for diagnostic in self._diagnostics:
            message = diagnostic.message
            if self.is_ipython() and (
                message == "undefined name 'get_ipython'"
            ):
                # get_ipython is defined in IPython files
                continue

            source = diagnostic.source or ""
            msg_range = diagnostic.range
            start_pos = msg_range.start
            end_pos = msg_range.end
            code = diagnostic.code or "E"
            severity = (
                diagnostic.severity
                if diagnostic.severity is not None
                else lsp.DiagnosticSeverity.Error
            )

            block = document.findBlockByNumber(start_pos.line)
            text = block.text()

            # Skip messages according to certain criteria.
            # This one works for any programming language
            if "analysis:ignore" in text:
                continue

            # This only works for Python and it's only needed with pyflakes.
            if self.language == "Python" and self.pyflakes_linting_enabled:
                if NOQA_INLINE_REGEXP.search(text) is not None:
                    continue

            data = block.userData()
            if not data:
                data = BlockUserData(self)

            if underline:
                block_nb = block.blockNumber()
                if first_block <= block_nb <= last_block:
                    error = severity == lsp.DiagnosticSeverity.Error
                    color = self.error_color if error else self.warning_color
                    color = QColor(color)
                    color.setAlpha(255)
                    block.color = color

                    data.selection_start = start_pos
                    data.selection_end = end_pos

                    self.highlight_selection(
                        "code_analysis_underline",
                        data._selection(),
                        underline_color=block.color,
                    )
            else:
                # Don't append messages to data for cloned editors to avoid
                # showing them twice or more times on hover.
                # Fixes spyder-ide/spyder#15618
                if not self.is_cloned:
                    data.code_analysis.append(
                        (source, code, severity, message)
                    )
                block.setUserData(data)

    # ---- Completion
    # -------------------------------------------------------------------------
    @schedule_request(
        method=lsp.TEXT_DOCUMENT_COMPLETION, cancel_previous=True
    )
    def do_completion(self, automatic=False):
        """Trigger completion."""
        cursor = self.textCursor()
        current_word = self.get_current_word(
            completion=True, valid_python_variable=False
        )

        params = lsp.CompletionParams(
            text_document=lsp.TextDocumentIdentifier(uri=self.document_uri),
            position=lsp.Position(
                line=cursor.blockNumber(), character=cursor.columnNumber()
            ),
            context=lsp.CompletionContext(
                trigger_kind=(
                    lsp.CompletionTriggerKind.TriggerCharacter
                    if automatic and current_word == ""
                    else lsp.CompletionTriggerKind.Invoked
                )
            ),
        )
        self.completion_args = (self.textCursor().position(), automatic)

        # Make sure that the document is up to date before requesting
        # completions.
        self._commit_pending_edit()

        return params

    @handles(lsp.TEXT_DOCUMENT_COMPLETION)
    def process_completion(self, params):
        """Handle completion response."""
        args = self.completion_args
        if args is None:
            # This should not happen
            return
        self.completion_args = None
        position, automatic = args

        start_cursor = self.textCursor()
        start_cursor.movePosition(QTextCursor.StartOfBlock)
        line_text = self.get_text(start_cursor.position(), "eol")
        leading_whitespace = self.compute_whitespace(line_text)
        indentation_whitespace = " " * leading_whitespace
        eol_char = self.get_line_separator()

        try:
            completions = params or []
            completions = [
                c
                for c in completions
                if c.insert_text
                or c.label
                or (c.text_edit and c.text_edit.new_text)
            ]

            prefix = self.get_current_word(
                completion=True, valid_python_variable=False
            )

            if (
                len(completions) == 1
                and (completions[0].insert_text or completions[0].label)
                == prefix
                and not (
                    completions[0].text_edit
                    and completions[0].text_edit.new_text
                )
            ):
                completions.pop()

            replace_end = self.textCursor().position()
            under_cursor = self.get_current_word_and_position(completion=True)
            if under_cursor:
                word, replace_start = under_cursor
            else:
                word = ""
                replace_start = replace_end
            first_letter = ""
            if len(word) > 0:
                first_letter = word[0]

            def sort_key(completion):
                te = completion.text_edit
                if te is not None:
                    text_insertion = te.new_text
                else:
                    text_insertion = completion.insert_text or completion.label

                first_insert_letter = (
                    text_insertion[0] if text_insertion else ""
                )
                case_mismatch = (
                    first_letter.isupper() and first_insert_letter.islower()
                ) or (first_letter.islower() and first_insert_letter.isupper())

                # False < True, so case matches go first
                return (case_mismatch, completion.sort_text or "")

            completion_list = sorted(completions, key=sort_key)

            # Allow for textEdit completions to be filtered by Spyder
            # if on-the-fly completions are disabled, only if the
            # textEdit range matches the word under the cursor.
            for completion in completion_list:
                te = completion.text_edit
                if te is not None:
                    c_range = te.range
                    c_replace_start = (
                        self.get_position_line_number(
                            c_range.start.line, c_range.start.character
                        )
                    )
                    c_replace_end = (
                        self.get_position_line_number(
                            c_range.end.line, c_range.end.character
                        )
                    )

                    if (
                        c_replace_start == replace_start
                        and c_replace_end == replace_end
                    ):
                        insert_text = te.new_text
                        completion.filter_text = insert_text
                        completion.insert_text = insert_text
                        completion.text_edit = None

                insert_text = completion.insert_text
                if insert_text:
                    insert_text_lines = insert_text.splitlines()
                    reindented_text = [insert_text_lines[0]]
                    for insert_line in insert_text_lines[1:]:
                        insert_line = indentation_whitespace + insert_line
                        reindented_text.append(insert_line)
                    reindented_text = eol_char.join(reindented_text)
                    completion.insert_text = reindented_text

            self.completion_widget.show_list(
                completion_list, position, automatic
            )
        except RuntimeError:
            # This is triggered when a codeeditor instance was removed
            # before the response can be processed.
            return
        except Exception:
            self.manage_lsp_handle_errors("Error when processing completions")

    @schedule_request(
        method=lsp.COMPLETION_ITEM_RESOLVE, cancel_previous=True
    )
    def resolve_completion_item(self, item):
        return item

    @handles(lsp.COMPLETION_ITEM_RESOLVE)
    def handle_completion_item_resolution(self, response):
        try:
            if not response:
                return

            self.completion_widget.augment_completion_info(response)
        except RuntimeError:
            # This is triggered when a codeeditor instance was removed
            # before the response can be processed.
            return
        except Exception:
            self.manage_lsp_handle_errors(
                "Error when handling completion item resolution"
            )

    # ---- Signature Hints
    # -------------------------------------------------------------------------
    @schedule_request(
        method=lsp.TEXT_DOCUMENT_SIGNATURE_HELP, cancel_previous=True
    )
    def request_signature(self):
        """Ask for signature."""
        # Ensure the pending edit is committed so that document_did_change is
        # queued before the signatureHelp request.
        self._commit_pending_edit()

        line, column = self.get_cursor_line_column()
        return lsp.SignatureHelpParams(
            text_document=lsp.TextDocumentIdentifier(uri=self.document_uri),
            position=lsp.Position(line=line, character=column),
        )

    @handles(lsp.TEXT_DOCUMENT_SIGNATURE_HELP)
    def process_signatures(self, response):
        """Handle signature response."""
        try:
            if response is None or not response.signatures:
                return

            active = response.active_signature or 0
            sig = response.signatures[active]

            doc = sig.documentation
            documentation = (
                doc.value
                if isinstance(doc, lsp.MarkupContent)
                else (doc or "")
            )

            # The language server returns encoded text with spaces defined as
            # `\xa0`
            documentation = documentation.replace("\xa0", " ")

            # Enable parsing signature's active parameter if available
            # while allowing to show calltip for signatures without parameters.
            # See spyder-ide/spyder#21660
            parameter = None
            if response.active_parameter is not None:
                parameter_idx = response.active_parameter
                parameters = sig.parameters or []
                if 0 <= parameter_idx < len(parameters):
                    label = parameters[parameter_idx].label
                    if isinstance(label, tuple):
                        parameter = sig.label[label[0]:label[1]]
                    else:
                        parameter = label

            self.sig_signature_invoked.emit(response)

            # This method is part of spyder/widgets/mixins
            self.show_calltip(
                signature=sig.label,
                parameter=parameter,
                language=self.language,
                documentation=documentation,
            )
        except RuntimeError:
            # This is triggered when a codeeditor instance was removed
            # before the response can be processed.
            return
        except Exception:
            self.manage_lsp_handle_errors("Error when processing signature")

    # ---- Hover/Cursor
    # -------------------------------------------------------------------------
    @schedule_request(method=lsp.TEXT_DOCUMENT_HOVER)
    def request_hover(self, line, col, offset, show_hint=True, clicked=True):
        """Request hover information."""
        self._show_hint = show_hint
        self._request_hover_clicked = clicked
        return lsp.HoverParams(
            text_document=lsp.TextDocumentIdentifier(uri=self.document_uri),
            position=lsp.Position(line=line, character=col),
        )

    @staticmethod
    def hover_text(hover: lsp.Hover | None) -> str:
        """Plain/markdown text of an LSP hover answer."""
        if hover is None:
            return ""
        raw = hover.contents
        entries = raw if isinstance(raw, (list, tuple)) else [raw]
        parts = []
        for entry in entries:
            if isinstance(entry, (lsp.MarkupContent, lsp.MarkedStringWithLanguage)):
                parts.append(entry.value)
            else:
                parts.append(str(entry))
        return "\n\n".join(part for part in parts if part)

    @handles(lsp.TEXT_DOCUMENT_HOVER)
    def handle_hover_response(self, hover):
        """Handle hover response."""
        if running_under_pytest():
            from unittest.mock import Mock

            # On some tests this is returning a Mock
            if isinstance(hover, Mock):
                return

        try:
            content = self.hover_text(hover)

            # Don't display hover if there's no content to display.
            if not content:
                return

            self.sig_display_object_info.emit(
                content, self._request_hover_clicked
            )

            if content is not None and self._show_hint and self._last_point:
                # This is located in spyder/widgets/mixins.py
                word = self._last_hover_word

                # Replace non-breaking spaces for real ones.
                content = content.replace("\xa0", " ")

                # Show hover
                self.show_hint(
                    content,
                    inspect_word=word,
                    at_point=self._last_point,
                    vertical_position='top',
                    as_hover=True,
                )

                self._last_point = None
        except RuntimeError:
            # This is triggered when a codeeditor instance was removed
            # before the response can be processed.
            return
        except Exception:
            self.manage_lsp_handle_errors("Error when processing hover")

    # ---- Go To Definition
    # -------------------------------------------------------------------------
    @Slot()
    @schedule_request(method=lsp.TEXT_DOCUMENT_DEFINITION)
    def go_to_definition_from_cursor(self, cursor=None):
        """Go to definition from cursor instance (QTextCursor)."""
        if not self.go_to_definition_enabled or self.in_comment_or_string():
            return

        if cursor is None:
            cursor = self.textCursor()

        text = str(cursor.selectedText())

        if len(text) == 0:
            cursor.select(QTextCursor.WordUnderCursor)
            text = str(cursor.selectedText())

        if text is not None:
            line, column = self.get_cursor_line_column()
            return lsp.DefinitionParams(
                text_document=lsp.TextDocumentIdentifier(
                    uri=self.document_uri
                ),
                position=lsp.Position(line=line, character=column),
            )

    @handles(lsp.TEXT_DOCUMENT_DEFINITION)
    def handle_go_to_definition(self, position):
        """Handle go to definition response (first location wins)."""
        try:
            if isinstance(position, list):
                position = position[0] if position else None
            if position is not None:
                if isinstance(position, lsp.Location):
                    uri = position.uri
                    start = position.range.start
                elif isinstance(position, lsp.LocationLink):
                    uri = position.target_uri
                    start = position.target_range.start
                else:
                    return
                file_path = uri_as_path(uri)
                if self.filename == file_path:
                    self.go_to_line(
                        start.line + 1, start.character, None, word=None
                    )
                else:
                    self.go_to_definition.emit(
                        file_path, start.line + 1, start.character
                    )
        except RuntimeError:
            # This is triggered when a codeeditor instance was removed
            # before the response can be processed.
            return
        except Exception:
            self.manage_lsp_handle_errors(
                "Error when processing go to definition"
            )

    # ---- Document/Selection formatting
    # -------------------------------------------------------------------------
    def format_document_or_range(self):
        """Format current document or selected text."""
        formatter = self.get_conf(
            ("providers", "pylsp", "values", "formatting"),
            default="",
            section="language_services",
        )
        is_ruff = formatter == "ruff"

        if (
            self.has_selected_text()
            and self.range_formatting_enabled
            and not is_ruff
        ):
            self.format_document_range()
        else:
            self.format_document()

    @schedule_request(method=lsp.TEXT_DOCUMENT_FORMATTING)
    def format_document(self):
        """Format current document."""
        self.__cursor_position_before_format = self.textCursor().position()

        if not self.formatting_enabled:
            return
        if self.formatting_in_progress:
            # Already waiting for a formatting
            return

        params = lsp.DocumentFormattingParams(
            text_document=lsp.TextDocumentIdentifier(uri=self.document_uri),
            options=self._formatting_options(),
        )

        # Sets the document into read-only and updates its corresponding
        # tab name to display the filename into parenthesis
        self.setReadOnly(True)
        self.document().setModified(True)
        self.sig_start_operation_in_progress.emit()
        self.operation_in_progress = True
        self.formatting_in_progress = True

        return params

    def _formatting_options(self) -> lsp.FormattingOptions:
        using_spaces = self.indent_chars != "\t"
        tab_size = (
            len(self.indent_chars)
            if using_spaces
            else self.tab_stop_width_spaces
        )
        return lsp.FormattingOptions(
            tab_size=tab_size,
            insert_spaces=using_spaces,
            trim_trailing_whitespace=self.remove_trailing_spaces,
            insert_final_newline=self.add_newline,
            trim_final_newlines=self.remove_trailing_newlines,
        )

    @schedule_request(method=lsp.TEXT_DOCUMENT_RANGE_FORMATTING)
    def format_document_range(self):
        """Format selected text."""
        self.__cursor_position_before_format = self.textCursor().position()

        if not self.range_formatting_enabled or not self.has_selected_text():
            return
        if self.formatting_in_progress:
            # Already waiting for a formatting
            return

        start, end = self.get_selection_start_end()
        start_line, start_col = start
        end_line, end_col = end

        # Remove empty trailing newline from multiline selection
        if end_line > start_line and end_col == 0:
            end_line -= 1

        params = lsp.DocumentRangeFormattingParams(
            text_document=lsp.TextDocumentIdentifier(uri=self.document_uri),
            range=lsp.Range(
                start=lsp.Position(line=start_line, character=start_col),
                end=lsp.Position(line=end_line, character=end_col),
            ),
            options=self._formatting_options(),
        )

        # Sets the document into read-only and updates its corresponding
        # tab name to display the filename into parenthesis
        self.setReadOnly(True)
        self.document().setModified(True)
        self.sig_start_operation_in_progress.emit()
        self.operation_in_progress = True
        self.formatting_in_progress = True

        return params

    @handles(lsp.TEXT_DOCUMENT_FORMATTING)
    def handle_document_formatting(self, edits):
        """Handle document formatting response."""
        try:
            if self.formatting_in_progress:
                self._apply_document_edits(edits)
        except RuntimeError:
            # This is triggered when a codeeditor instance was removed
            # before the response can be processed.
            return
        except Exception:
            self.manage_lsp_handle_errors(
                "Error when processing document formatting"
            )
        finally:
            # Remove read-only parenthesis and highlight document modification
            self.setReadOnly(False)
            self.document().setModified(False)
            self.document().setModified(True)
            self.sig_stop_operation_in_progress.emit()
            self.operation_in_progress = False
            self.formatting_in_progress = False

    @handles(lsp.TEXT_DOCUMENT_RANGE_FORMATTING)
    def handle_document_range_formatting(self, edits):
        """Handle document range formatting response."""
        try:
            if self.formatting_in_progress:
                self._apply_document_edits(edits)
        except RuntimeError:
            # This is triggered when a codeeditor instance was removed
            # before the response can be processed.
            return
        except Exception:
            self.manage_lsp_handle_errors(
                "Error when processing document selection formatting"
            )
        finally:
            # Remove read-only parenthesis and highlight document modification
            self.setReadOnly(False)
            self.document().setModified(False)
            self.document().setModified(True)
            self.sig_stop_operation_in_progress.emit()
            self.operation_in_progress = False
            self.formatting_in_progress = False

    def _apply_document_edits(self, edits):
        """Apply a set of atomic document edits to the current editor text."""
        if not edits:
            return

        # We need to use here toPlainText (which returns text with '\n'
        # for eols) and not get_text_with_eol, so that applying the
        # text edits that come from the LSP in the way implemented below
        # works as expected. That's because we assume eol chars of length
        # one in our algorithm.
        # Fixes spyder-ide/spyder#16180
        text = self.toPlainText()

        text_tokens = list(text)
        merged_text = None
        for edit in edits:
            repl_text = edit.new_text
            start_line = edit.range.start.line
            start_col = edit.range.start.character
            end_line = edit.range.end.line
            end_col = edit.range.end.character

            start_pos = self.get_position_line_number(start_line, start_col)
            end_pos = self.get_position_line_number(end_line, end_col)

            # Replace repl_text eols for '\n' to match the ones used in
            # `text`.
            repl_eol = sourcecode.get_eol_chars(repl_text)
            if repl_eol is not None and repl_eol != "\n":
                repl_text = repl_text.replace(repl_eol, "\n")

            text_tokens = list(text_tokens)
            this_edit = list(repl_text)

            if end_line == self.document().blockCount():
                end_pos = self.get_position("eof")
                end_pos += 1

            if (
                end_pos == len(text_tokens)
                and text_tokens[end_pos - 1] == "\n"
            ):
                end_pos += 1

            this_edition = (
                text_tokens[: max(start_pos - 1, 0)]
                + this_edit
                + text_tokens[end_pos - 1:]
            )

            text_edit = "".join(this_edition)
            if merged_text is None:
                merged_text = text_edit
            else:
                merged_text = merge(text_edit, merged_text, text)

        if merged_text is not None:
            # Restore eol chars after applying edits.
            merged_text = merged_text.replace("\n", self.get_line_separator())
            cursor = self.textCursor()

            # Save breakpoints here to restore them after inserting merged_text
            # Fixes spyder-ide/spyder#16549
            if getattr(self, "breakpoints_manager", False):
                breakpoints = self.breakpoints_manager.get_breakpoints()
            else:
                breakpoints = None

            # Begin text insertion
            cursor.beginEditBlock()

            # Select current text
            cursor.movePosition(QTextCursor.Start)
            cursor.movePosition(QTextCursor.End, QTextCursor.KeepAnchor)

            # Insert formatted text in place of the previous one
            cursor.insertText(merged_text)

            # End text insertion
            cursor.endEditBlock()
            
            # Restore breakpoints
            if breakpoints:
                self.breakpoints_manager.set_breakpoints(breakpoints)

            # Restore previous cursor position and center it.
            # Fixes spyder-ide/spyder#19958
            # Use QTextCursor.(position | setPosition) to restore the cursor
            # position to be able to do it with any wrap mode.
            # Fixes spyder-ide/spyder#20852
            if self.__cursor_position_before_format:
                self.moveCursor(QTextCursor.Start)
                cursor = self.textCursor()
                cursor.setPosition(self.__cursor_position_before_format)
                self.setTextCursor(cursor)
                self.centerCursor()

    # ---- Code folding
    # -------------------------------------------------------------------------
    def compute_whitespace(self, line):
        tab_size = self.tab_stop_width_spaces
        whitespace_regex = re.compile(r"(\s+).*")
        whitespace_match = whitespace_regex.match(line)
        total_whitespace = 0
        if whitespace_match is not None:
            whitespace_chars = whitespace_match.group(1)
            whitespace_chars = whitespace_chars.replace("\t", tab_size * " ")
            total_whitespace = len(whitespace_chars)
        return total_whitespace

    def update_whitespace_count(self, line, column):
        self.leading_whitespaces = {}
        lines = self.lines()
        for i, text in enumerate(lines):
            total_whitespace = self.compute_whitespace(text)
            self.leading_whitespaces[i] = total_whitespace

    def cleanup_folding(self):
        """Cleanup folding pane."""
        self.folding_panel.folding_regions = {}

    @schedule_request(
        method=lsp.TEXT_DOCUMENT_FOLDING_RANGE, cancel_previous=True
    )
    def request_folding(self):
        """Request folding."""
        if not self.folding_supported or not self.code_folding:
            return
        self.folding_sync_version = self.text_version
        return lsp.FoldingRangeParams(
            text_document=lsp.TextDocumentIdentifier(uri=self.document_uri)
        )

    @handles(lsp.TEXT_DOCUMENT_FOLDING_RANGE)
    def handle_folding_range(self, response):
        """Handle folding response."""
        if self._is_outdated_response(
            lsp.TEXT_DOCUMENT_FOLDING_RANGE, self.folding_sync_version
        ):
            return

        ranges = response or []
        if not ranges:
            return

        # Update folding info in a thread
        self.update_folding_thread.run = functools.partial(
            self._update_folding_info, ranges)
        self.update_folding_thread.start()

    def _update_folding_info(self, ranges):
        """Update folding information with new data from the LSP."""
        try:
            lines = self.lines()

            current_tree, root = merge_folding(
                ranges, lines, self.get_line_separator(),
                self.folding_panel.current_tree, self.folding_panel.root
            )

            self._folding_info = (current_tree, root, *collect_folding_regions(root))
        except RuntimeError:
            # This is triggered when a codeeditor instance was removed
            # before the response can be processed.
            return
        except Exception:
            self.manage_lsp_handle_errors("Error when processing folding")

    def highlight_folded_regions(self):
        self.folding_panel.highlight_folded_regions()

    def _finish_update_folding(self):
        """Finish updating code folding."""
        self.sig_update_code_folding.emit(self._folding_info)
        self.apply_code_folding(self._folding_info)

    def apply_code_folding(self, folding_info):
        """Apply code folding info."""
        # Check if we actually have folding info to update before trying to do
        # it.
        # Fixes spyder-ide/spyder#19514
        if folding_info is not None:
            self.folding_panel.update_folding(folding_info)

        self.highlight_folded_regions()

        # Update indent guides, which depend on folding
        if self.indent_guides._enabled:
            line, column = self.get_cursor_line_column()
            self.update_whitespace_count(line, column)

            # This is necessary to repaint guides in cloned editors and the
            # original one after making edits in any one of them.
            # See spyder-ide/spyder#23297
            self.update()

    # ---- Save/close file
    # -------------------------------------------------------------------------
    @request(
        method=lsp.TEXT_DOCUMENT_DID_SAVE, requires_response=False
    )
    def notify_save(self):
        """Send save request."""
        return lsp.DidSaveTextDocumentParams(
            text_document=lsp.TextDocumentIdentifier(uri=self.document_uri),
            text=self.get_text_with_eol() if self.save_include_text else None,
        )

    def notify_close(self):
        """Abort pending LSP work and send a close request when applicable."""
        self._pending_server_requests = []
        self._cancel_pending_futures()

        # This is necessary to prevent an error when closing the file.
        # Fixes spyder-ide/spyder#20071
        try:
            self._server_requests_timer.stop()
        except RuntimeError:
            pass

        # Cloned editors share the document opened by the original one.
        if not self.completions_available or self.is_cloned:
            return

        # This is necessary to prevent an error in our tests.
        try:
            # Servers can send an empty publishDiagnostics reply to clear
            # diagnostics after they receive a didClose request. Since
            # we also ask for symbols and folding when processing
            # diagnostics, we need to prevent it from happening
            # before sending that request here.
            self._timer_sync_symbols_and_folding.timeout.disconnect()
        except (TypeError, RuntimeError):
            pass

        params = lsp.DidCloseTextDocumentParams(
            text_document=lsp.TextDocumentIdentifier(uri=self.document_uri)
        )
        self.emit_request(
            lsp.TEXT_DOCUMENT_DID_CLOSE, params, requires_response=False
        )
