# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""
Editor mixin and utils to manage connection with the LSP
"""

# Standard library imports
import functools
import logging
import random
import re

# Third party imports
from diff_match_patch import diff_match_patch
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
from spyder.config.base import running_under_pytest
from spyder.plugins.completion.api import (
    CompletionRequestTypes,
    TextDocumentSyncKind,
    DiagnosticSeverity,
)
from spyder.plugins.completion.decorators import (
    request,
    handles,
    class_register,
)
from spyder.plugins.editor.panels import FoldingPanel
from spyder.plugins.editor.panels.utils import (
    merge_folding,
    collect_folding_regions,
)
from spyder.plugins.editor.utils.editor import BlockUserData
from spyder.utils import sourcecode


logger = logging.getLogger(__name__)

# Regexp to detect noqa inline comments.
NOQA_INLINE_REGEXP = re.compile(r"#?noqa", re.IGNORECASE)


def schedule_request(req=None, method=None, requires_response=True):
    """Call function req and then emit its results to the completion server."""
    if req is None:
        return functools.partial(
            schedule_request,
            method=method,
            requires_response=requires_response,
        )

    @functools.wraps(req)
    def wrapper(self, *args, **kwargs):
        params = req(self, *args, **kwargs)
        if params is not None and self.completions_available:
            self._pending_server_requests.append(
                (method, params, requires_response)
            )
            self._server_requests_timer.setInterval(
                self.LSP_REQUESTS_SHORT_DELAY
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
    LSP_REQUESTS_SHORT_DELAY = 50
    LSP_REQUESTS_LONG_DELAY = 300

    # -- LSP signals
    #: Signal emitted when an LSP request is sent to the LSP manager
    sig_perform_completion_request = Signal(str, str, dict)

    #: Signal emitted when a response is received from the completion plugin
    # For now it's only used on tests, but it could be used to track
    # and profile completion diagnostics.
    completions_response_signal = Signal(str, object)

    #: Signal to display object information on the Help plugin
    sig_display_object_info = Signal(str, bool)

    #: Signal only used for tests
    # TODO: Remove it!
    sig_signature_invoked = Signal(dict)

    #: Signal emitted when processing code analysis warnings is finished
    sig_process_code_analysis = Signal()

    # Used to start the status spinner in the editor
    sig_start_operation_in_progress = Signal()

    # Used to start the status spinner in the editor
    sig_stop_operation_in_progress = Signal()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

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
        self._server_requests_timer.setInterval(self.LSP_REQUESTS_SHORT_DELAY)
        self._server_requests_timer.timeout.connect(
            self._process_server_requests)

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

        # Text diffs across versions
        self.differ = diff_match_patch()
        self.previous_text = ''
        self.patch = []
        self.leading_whitespaces = {}

        # Other attributes
        self.filename = None
        self.completions_available = False
        self.text_version = 0
        self.save_include_text = True
        self.open_close_notifications = True
        self.sync_mode = TextDocumentSyncKind.FULL
        self.will_save_notify = False
        self.will_save_until_notify = False
        self.enable_hover = True
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
        self.symbols_in_sync = False
        self.folding_in_sync = False

    # ---- Helper private methods
    # -------------------------------------------------------------------------
    def _process_server_requests(self):
        """Process server requests."""
        # Check if the document needs to be updated
        if self._document_server_needs_update:
            self.document_did_change()
            self.do_automatic_completions()
            self._document_server_needs_update = False

        # Send pending requests
        for method, params, requires_response in self._pending_server_requests:
            self.emit_request(method, params, requires_response)

        # Clear pending requests
        self._pending_server_requests = []

    # ---- Basic methods
    # -------------------------------------------------------------------------
    @Slot(str, dict)
    def handle_response(self, method, params):
        if method in self.handler_registry:
            handler_name = self.handler_registry[method]
            handler = getattr(self, handler_name)
            handler(params)
            # This signal is only used on tests.
            # It could be used to track and profile LSP diagnostics.
            self.completions_response_signal.emit(method, params)

    def emit_request(self, method, params, requires_response):
        """Send request to LSP manager."""
        params["requires_response"] = requires_response
        params["response_instance"] = self
        self.sig_perform_completion_request.emit(
            self.language.lower(), method, params
        )

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

    def register_completion_capabilities(self, capabilities):
        """
        Register completion server capabilities.

        Parameters
        ----------
        capabilities: dict
            Capabilities supported by a language server.
        """
        sync_options = capabilities["textDocumentSync"]
        completion_options = capabilities["completionProvider"]
        signature_options = capabilities["signatureHelpProvider"]
        range_formatting_options = capabilities[
            "documentOnTypeFormattingProvider"
        ]
        self.open_close_notifications = sync_options.get("openClose", False)
        self.sync_mode = sync_options.get("change", TextDocumentSyncKind.NONE)
        self.will_save_notify = sync_options.get("willSave", False)
        self.will_save_until_notify = sync_options.get(
            "willSaveWaitUntil", False
        )
        self.save_include_text = sync_options["save"]["includeText"]
        self.enable_hover = capabilities["hoverProvider"]
        self.folding_supported = capabilities.get(
            "foldingRangeProvider", False
        )
        self.auto_completion_characters = completion_options[
            "triggerCharacters"
        ]
        self.resolve_completions_enabled = completion_options.get(
            "resolveProvider", False
        )
        self.signature_completion_characters = signature_options[
            "triggerCharacters"
        ] + [
            "="
        ]  # FIXME:
        self.go_to_definition_enabled = capabilities["definitionProvider"]
        self.find_references_enabled = capabilities["referencesProvider"]
        self.highlight_enabled = capabilities["documentHighlightProvider"]
        self.formatting_enabled = capabilities["documentFormattingProvider"]
        self.range_formatting_enabled = capabilities[
            "documentRangeFormattingProvider"
        ]
        self.document_symbols_enabled = capabilities["documentSymbolProvider"]
        self.formatting_characters.append(
            range_formatting_options["firstTriggerCharacter"]
        )
        self.formatting_characters += range_formatting_options.get(
            "moreTriggerCharacter", []
        )

        if self.formatting_enabled:
            self.format_action.setEnabled(True)
            self.sig_refresh_formatting.emit(True)

        self.completions_available = True

    def stop_completion_services(self):
        logger.debug("Stopping completion services for %s" % self.filename)
        self.completions_available = False

    @request(
        method=CompletionRequestTypes.DOCUMENT_DID_OPEN,
        requires_response=False,
    )
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

        cursor = self.textCursor()
        text = self.get_text_with_eol()
        if self.is_ipython():
            # Send valid python text to LSP as it doesn't support IPython
            text = self.ipython_to_python(text)
        params = {
            "file": self.filename,
            "language": self.language,
            "version": self.text_version,
            "text": text,
            "codeeditor": self,
            "offset": cursor.position(),
            "selection_start": cursor.selectionStart(),
            "selection_end": cursor.selectionEnd(),
        }
        return params

    # ---- Symbols
    # -------------------------------------------------------------------------
    @schedule_request(method=CompletionRequestTypes.DOCUMENT_SYMBOL)
    def request_symbols(self):
        """Request document symbols."""
        if not self.document_symbols_enabled:
            return
        if self.oe_proxy is not None:
            self.oe_proxy.emit_request_in_progress()
        params = {"file": self.filename}
        return params

    @handles(CompletionRequestTypes.DOCUMENT_SYMBOL)
    def process_symbols(self, params):
        """Handle symbols response."""
        try:
            symbols = params["params"]
            self._update_classfuncdropdown(symbols)

            if self.oe_proxy is not None:
                self.oe_proxy.update_outline_info(symbols)
        except RuntimeError:
            # This is triggered when a codeeditor instance was removed
            # before the response can be processed.
            return
        except Exception:
            self.manage_lsp_handle_errors("Error when processing symbols")
        finally:
            self.symbols_in_sync = True

    def _update_classfuncdropdown(self, symbols):
        """Update class/function dropdown."""
        symbols = [] if symbols is None else symbols

        if self.classfuncdropdown.isVisible():
            self.classfuncdropdown.update_data(symbols)
        else:
            self.classfuncdropdown.set_data(symbols)

    # ---- Linting and didChange
    # -------------------------------------------------------------------------
    def _schedule_document_did_change(self):
        """Schedule a document update."""
        self._document_server_needs_update = True
        self._server_requests_timer.setInterval(self.LSP_REQUESTS_LONG_DELAY)
        self._server_requests_timer.start()

    @request(
        method=CompletionRequestTypes.DOCUMENT_DID_CHANGE,
        requires_response=False,
    )
    def document_did_change(self):
        """Send textDocument/didChange request to the server."""
        # Cancel formatting
        self.formatting_in_progress = False
        self.symbols_in_sync = False
        self.folding_in_sync = False

        # Don't send request for cloned editors because it's not necessary.
        # The original file should send the request.
        if self.is_cloned:
            return

        # Get text
        text = self.get_text_with_eol()
        if self.is_ipython():
            # Send valid python text to LSP
            text = self.ipython_to_python(text)

        self.text_version += 1

        self.patch = self.differ.patch_make(self.previous_text, text)
        self.previous_text = text
        cursor = self.textCursor()
        params = {
            "file": self.filename,
            "version": self.text_version,
            "text": text,
            "diff": self.patch,
            "offset": cursor.position(),
            "selection_start": cursor.selectionStart(),
            "selection_end": cursor.selectionEnd(),
        }
        return params

    @handles(CompletionRequestTypes.DOCUMENT_PUBLISH_DIAGNOSTICS)
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
        self.process_code_analysis(params["params"])

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
        if not self.folding_in_sync:
            self.request_folding()
        if not self.symbols_in_sync:
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
            if self.is_ipython() and (
                diagnostic["message"] == "undefined name 'get_ipython'"
            ):
                # get_ipython is defined in IPython files
                continue
            source = diagnostic.get("source", "")
            msg_range = diagnostic["range"]
            start = msg_range["start"]
            end = msg_range["end"]
            code = diagnostic.get("code", "E")
            message = diagnostic["message"]
            severity = diagnostic.get("severity", DiagnosticSeverity.ERROR)

            block = document.findBlockByNumber(start["line"])
            text = block.text()

            # Skip messages according to certain criteria.
            # This one works for any programming language
            if "analysis:ignore" in text:
                continue

            # This only works for Python.
            if self.language == "Python":
                if NOQA_INLINE_REGEXP.search(text) is not None:
                    continue

            data = block.userData()
            if not data:
                data = BlockUserData(self)

            if underline:
                block_nb = block.blockNumber()
                if first_block <= block_nb <= last_block:
                    error = severity == DiagnosticSeverity.ERROR
                    color = self.error_color if error else self.warning_color
                    color = QColor(color)
                    color.setAlpha(255)
                    block.color = color

                    data.selection_start = start
                    data.selection_end = end

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
    @schedule_request(method=CompletionRequestTypes.DOCUMENT_COMPLETION)
    def do_completion(self, automatic=False):
        """Trigger completion."""
        cursor = self.textCursor()
        current_word = self.get_current_word(
            completion=True, valid_python_variable=False
        )

        params = {
            "file": self.filename,
            "line": cursor.blockNumber(),
            "column": cursor.columnNumber(),
            "offset": cursor.position(),
            "selection_start": cursor.selectionStart(),
            "selection_end": cursor.selectionEnd(),
            "current_word": current_word,
        }
        self.completion_args = (self.textCursor().position(), automatic)
        return params

    @handles(CompletionRequestTypes.DOCUMENT_COMPLETION)
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
            completions = params["params"]
            completions = (
                []
                if completions is None
                else [
                    completion
                    for completion in completions
                    if completion.get("insertText")
                    or completion.get("textEdit", {}).get("newText")
                ]
            )
            prefix = self.get_current_word(
                completion=True, valid_python_variable=False
            )

            if (
                len(completions) == 1
                and completions[0].get("insertText") == prefix
                and not completions[0].get("textEdit", {}).get("newText")
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
                if "textEdit" in completion:
                    text_insertion = completion["textEdit"]["newText"]
                else:
                    text_insertion = completion["insertText"]

                first_insert_letter = text_insertion[0]
                case_mismatch = (
                    first_letter.isupper() and first_insert_letter.islower()
                ) or (first_letter.islower() and first_insert_letter.isupper())

                # False < True, so case matches go first
                return (case_mismatch, completion["sortText"])

            completion_list = sorted(completions, key=sort_key)

            # Allow for textEdit completions to be filtered by Spyder
            # if on-the-fly completions are disabled, only if the
            # textEdit range matches the word under the cursor.
            for completion in completion_list:
                if "textEdit" in completion:
                    c_replace_start = completion["textEdit"]["range"]["start"]
                    c_replace_end = completion["textEdit"]["range"]["end"]

                    if (
                        c_replace_start == replace_start
                        and c_replace_end == replace_end
                    ):
                        insert_text = completion["textEdit"]["newText"]
                        completion["filterText"] = insert_text
                        completion["insertText"] = insert_text
                        del completion["textEdit"]

                if "insertText" in completion:
                    insert_text = completion["insertText"]
                    insert_text_lines = insert_text.splitlines()
                    reindented_text = [insert_text_lines[0]]
                    for insert_line in insert_text_lines[1:]:
                        insert_line = indentation_whitespace + insert_line
                        reindented_text.append(insert_line)
                    reindented_text = eol_char.join(reindented_text)
                    completion["insertText"] = reindented_text

            self.completion_widget.show_list(
                completion_list, position, automatic
            )
        except RuntimeError:
            # This is triggered when a codeeditor instance was removed
            # before the response can be processed.
            return
        except Exception:
            self.manage_lsp_handle_errors("Error when processing completions")

    @schedule_request(method=CompletionRequestTypes.COMPLETION_RESOLVE)
    def resolve_completion_item(self, item):
        return {"file": self.filename, "completion_item": item}

    @handles(CompletionRequestTypes.COMPLETION_RESOLVE)
    def handle_completion_item_resolution(self, response):
        try:
            response = response["params"]

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
    @schedule_request(method=CompletionRequestTypes.DOCUMENT_SIGNATURE)
    def request_signature(self):
        """Ask for signature."""
        line, column = self.get_cursor_line_column()
        offset = self.get_position("cursor")
        params = {
            "file": self.filename,
            "line": line,
            "column": column,
            "offset": offset,
        }
        return params

    @handles(CompletionRequestTypes.DOCUMENT_SIGNATURE)
    def process_signatures(self, params):
        """Handle signature response."""
        try:
            signature_params = params["params"]

            if signature_params is not None:
                self.sig_signature_invoked.emit(signature_params)
                signature_data = signature_params["signatures"]
                documentation = signature_data["documentation"]

                if isinstance(documentation, dict):
                    documentation = documentation["value"]

                # The language server returns encoded text with
                # spaces defined as `\xa0`
                documentation = documentation.replace("\xa0", " ")

                # Enable parsing signature's active parameter if available
                # while allowing to show calltip for signatures without
                # parameters.
                # See spyder-ide/spyder#21660
                parameter = None
                if "activeParameter" in signature_params:
                    parameter_idx = signature_params["activeParameter"]
                    parameters = signature_data["parameters"]
                    if len(parameters) > 0 and parameter_idx < len(parameters):
                        parameter_data = parameters[parameter_idx]
                        parameter = parameter_data["label"]

                signature = signature_data["label"]

                # This method is part of spyder/widgets/mixins
                self.show_calltip(
                    signature=signature,
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
    @schedule_request(method=CompletionRequestTypes.DOCUMENT_CURSOR_EVENT)
    def request_cursor_event(self):
        text = self.get_text_with_eol()
        cursor = self.textCursor()
        params = {
            "file": self.filename,
            "version": self.text_version,
            "text": text,
            "offset": cursor.position(),
            "selection_start": cursor.selectionStart(),
            "selection_end": cursor.selectionEnd(),
        }
        return params

    @schedule_request(method=CompletionRequestTypes.DOCUMENT_HOVER)
    def request_hover(self, line, col, offset, show_hint=True, clicked=True):
        """Request hover information."""
        params = {
            "file": self.filename,
            "line": line,
            "column": col,
            "offset": offset,
        }
        self._show_hint = show_hint
        self._request_hover_clicked = clicked
        return params

    @handles(CompletionRequestTypes.DOCUMENT_HOVER)
    def handle_hover_response(self, contents):
        """Handle hover response."""
        if running_under_pytest():
            from unittest.mock import Mock

            # On some tests this is returning a Mock
            if isinstance(contents, Mock):
                return

        try:
            content = contents["params"]

            # - Don't display hover if there's no content to display.
            # - Prevent spurious errors when a client returns a list.
            if not content or isinstance(content, list):
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
    @schedule_request(method=CompletionRequestTypes.DOCUMENT_DEFINITION)
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
            params = {"file": self.filename, "line": line, "column": column}
            return params

    @handles(CompletionRequestTypes.DOCUMENT_DEFINITION)
    def handle_go_to_definition(self, position):
        """Handle go to definition response."""
        try:
            position = position["params"]
            if position is not None:
                def_range = position["range"]
                start = def_range["start"]
                if self.filename == position["file"]:
                    self.go_to_line(
                        start["line"] + 1, start["character"], None, word=None
                    )
                else:
                    self.go_to_definition.emit(
                        position["file"], start["line"] + 1, start["character"]
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
        if self.has_selected_text() and self.range_formatting_enabled:
            self.format_document_range()
        else:
            self.format_document()

    @schedule_request(method=CompletionRequestTypes.DOCUMENT_FORMATTING)
    def format_document(self):
        """Format current document."""
        self.__cursor_position_before_format = self.textCursor().position()

        if not self.formatting_enabled:
            return
        if self.formatting_in_progress:
            # Already waiting for a formatting
            return

        using_spaces = self.indent_chars != "\t"
        tab_size = (
            len(self.indent_chars)
            if using_spaces
            else self.tab_stop_width_spaces
        )
        params = {
            "file": self.filename,
            "options": {
                "tab_size": tab_size,
                "insert_spaces": using_spaces,
                "trim_trailing_whitespace": self.remove_trailing_spaces,
                "insert_final_new_line": self.add_newline,
                "trim_final_new_lines": self.remove_trailing_newlines,
            },
        }

        # Sets the document into read-only and updates its corresponding
        # tab name to display the filename into parenthesis
        self.setReadOnly(True)
        self.document().setModified(True)
        self.sig_start_operation_in_progress.emit()
        self.operation_in_progress = True
        self.formatting_in_progress = True

        return params

    @schedule_request(method=CompletionRequestTypes.DOCUMENT_RANGE_FORMATTING)
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

        fmt_range = {
            "start": {"line": start_line, "character": start_col},
            "end": {"line": end_line, "character": end_col},
        }

        using_spaces = self.indent_chars != "\t"
        tab_size = (
            len(self.indent_chars)
            if using_spaces
            else self.tab_stop_width_spaces
        )

        params = {
            "file": self.filename,
            "range": fmt_range,
            "options": {
                "tab_size": tab_size,
                "insert_spaces": using_spaces,
                "trim_trailing_whitespace": self.remove_trailing_spaces,
                "insert_final_new_line": self.add_newline,
                "trim_final_new_lines": self.remove_trailing_newlines,
            },
        }

        # Sets the document into read-only and updates its corresponding
        # tab name to display the filename into parenthesis
        self.setReadOnly(True)
        self.document().setModified(True)
        self.sig_start_operation_in_progress.emit()
        self.operation_in_progress = True
        self.formatting_in_progress = True

        return params

    @handles(CompletionRequestTypes.DOCUMENT_FORMATTING)
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

    @handles(CompletionRequestTypes.DOCUMENT_RANGE_FORMATTING)
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
        edits = edits["params"]
        if edits is None:
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
            edit_range = edit["range"]
            repl_text = edit["newText"]
            start, end = edit_range["start"], edit_range["end"]
            start_line, start_col = start["line"], start["character"]
            end_line, end_col = end["line"], end["character"]

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

            # Begin text insertion
            cursor.beginEditBlock()

            # Select current text
            cursor.movePosition(QTextCursor.Start)
            cursor.movePosition(QTextCursor.End, QTextCursor.KeepAnchor)

            # Insert formatted text in place of the previous one
            cursor.insertText(merged_text)

            # End text insertion
            cursor.endEditBlock()

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
        lines = str(self.toPlainText()).splitlines()
        for i, text in enumerate(lines):
            total_whitespace = self.compute_whitespace(text)
            self.leading_whitespaces[i] = total_whitespace

    def cleanup_folding(self):
        """Cleanup folding pane."""
        self.folding_panel.folding_regions = {}

    @schedule_request(method=CompletionRequestTypes.DOCUMENT_FOLDING_RANGE)
    def request_folding(self):
        """Request folding."""
        if not self.folding_supported or not self.code_folding:
            return
        params = {"file": self.filename}
        return params

    @handles(CompletionRequestTypes.DOCUMENT_FOLDING_RANGE)
    def handle_folding_range(self, response):
        """Handle folding response."""
        ranges = response["params"]
        if ranges is None:
            return

        # Update folding info in a thread
        self.update_folding_thread.run = functools.partial(
            self._update_folding_info, ranges)
        self.update_folding_thread.start()

    def _update_folding_info(self, ranges):
        """Update folding information with new data from the LSP."""
        try:
            lines = self.toPlainText().splitlines()

            current_tree, root = merge_folding(
                ranges, lines, self.get_line_separator(),
                self.folding_panel.current_tree, self.folding_panel.root
            )

            folding_info = collect_folding_regions(root)
            self._folding_info = (current_tree, root, *folding_info)
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
        # Check if we actually have folding info to update before trying to do
        # it.
        # Fixes spyder-ide/spyder#19514
        if self._folding_info is not None:
            self.folding_panel.update_folding(self._folding_info)

        self.highlight_folded_regions()

        # Update indent guides, which depend on folding
        if self.indent_guides._enabled and len(self.patch) > 0:
            line, column = self.get_cursor_line_column()
            self.update_whitespace_count(line, column)

        self.folding_in_sync = True

    # ---- Save/close file
    # -------------------------------------------------------------------------
    @schedule_request(method=CompletionRequestTypes.DOCUMENT_DID_SAVE,
                      requires_response=False)
    def notify_save(self):
        """Send save request."""
        params = {'file': self.filename}
        if self.save_include_text:
            params['text'] = self.get_text_with_eol()
        return params

    @request(method=CompletionRequestTypes.DOCUMENT_DID_CLOSE,
             requires_response=False)
    def notify_close(self):
        """Send close request."""
        self._pending_server_requests = []

        # This is necessary to prevent an error when closing the file.
        # Fixes spyder-ide/spyder#20071
        try:
            self._server_requests_timer.stop()
        except RuntimeError:
            pass

        if self.completions_available:
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

            params = {
                'file': self.filename,
                'codeeditor': self
            }
            return params
