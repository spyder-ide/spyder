# -*- coding: utf-8 -*-

# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""
Spyder Language Server Protocol Client implementation.

Uses pygls JsonRPCClient (_SpyderPyglsClient) with a dedicated asyncio
thread for all LSP communication.  All parameters and responses are typed
lsprotocol objects; requests and notifications are dispatched directly via
protocol.send_request_async / protocol.notify.
"""

# Standard library imports
from __future__ import annotations

import asyncio
import logging
import os
import os.path as osp
import pathlib
import sys
import typing

# Third-party imports
from lsprotocol import types as lsp
from pygls.client import JsonRPCClient
from pygls.protocol import LanguageServerProtocol, default_converter
from qtpy.QtCore import QObject, QProcess, Signal, Slot
from spyder_kernels.utils.pythonenv import is_conda_env

# Local imports
from spyder.api.asyncdispatcher import AsyncDispatcher, DispatcherFuture
from spyder.api.config.mixins import SpyderConfigurationAccessor
from spyder.config.base import (
    DEV, get_conf_path, get_debug_level, running_under_pytest
)
from spyder.plugins.completion.api import SpyderSymbolKind
from spyder.plugins.completion.providers.languageserver.decorators import (
    class_register, handles
)
from spyder.plugins.completion.providers.languageserver.providers import (
    LSPMethodProviderMixIn
)
from spyder.utils.misc import getcwd_or_home, select_port

if typing.TYPE_CHECKING:
    from spyder.plugins.completion.providers.languageserver.providers.workspace import WatchedFolder


class RequestParams(typing.TypedDict, total=False):
    """TypedDict for parameters passed to LSPClient.perform_request builders."""
    requires_response: bool
    response_callback: typing.Callable


# Verbosity level sent to the server in the initialize request.
TRACE = lsp.TraceValue.Messages
if DEV:
    TRACE = lsp.TraceValue.Verbose

logger = logging.getLogger(__name__)

# Global loop name for AsyncDispatcher in LSP client.
_LSP_LOOP = 'lsp'


def _spyder_converter():
    """
    Build the cattrs converter used by _SpyderPyglsClient.

    Extends pygls's default_converter() with a structure hook for
    ``Optional[Union[str, NotebookDocumentFilter*]]``.  That type is used by
    ``NotebookDocumentFilterWithCells.notebook`` in lsprotocol 2025.0.0, but
    its hooks only cover the non-Optional variant, causing a
    ``StructureHandlerNotFoundError`` when pylsp returns
    ``notebookDocumentSync`` capabilities.
    """
    converter = default_converter()

    # Build the exact Optional Union type that lsprotocol 2025.0.0 exposes on
    # NotebookDocumentFilterWithCells.notebook so the hook key matches.
    _opt_notebook_filter = typing.Optional[
        typing.Union[
            str,
            lsp.NotebookDocumentFilterNotebookType,
            lsp.NotebookDocumentFilterScheme,
            lsp.NotebookDocumentFilterPattern,
        ]
    ]

    def _structure_opt_notebook_filter(obj, _):
        if obj is None:
            return None
        if isinstance(obj, str):
            return obj
        if "notebookType" in obj:
            return converter.structure(obj, lsp.NotebookDocumentFilterNotebookType)
        if "scheme" in obj:
            return converter.structure(obj, lsp.NotebookDocumentFilterScheme)
        return converter.structure(obj, lsp.NotebookDocumentFilterPattern)

    converter.register_structure_hook(_opt_notebook_filter, _structure_opt_notebook_filter)

    # Register hook for custom for Spyder extended LSP SymbolKind
    def _structure_symbol_kind(obj, _):
        try:
            return lsp.SymbolKind(obj)
        except ValueError:
            return SpyderSymbolKind(obj)

    converter.register_structure_hook(lsp.SymbolKind, _structure_symbol_kind)

    return converter


def _build_client_capabilities() -> lsp.ClientCapabilities:
    """Build the ClientCapabilities object advertised to the LSP server."""
    return lsp.ClientCapabilities(
        workspace=lsp.WorkspaceClientCapabilities(
            apply_edit=True,
            workspace_edit=lsp.WorkspaceEditClientCapabilities(
                document_changes=True,
                resource_operations=[
                    lsp.ResourceOperationKind.Create,
                    lsp.ResourceOperationKind.Rename,
                    lsp.ResourceOperationKind.Delete,
                ],
                failure_handling=lsp.FailureHandlingKind.Transactional,
            ),
            did_change_configuration=lsp.DidChangeConfigurationClientCapabilities(
                dynamic_registration=True,
            ),
            did_change_watched_files=lsp.DidChangeWatchedFilesClientCapabilities(
                dynamic_registration=True,
            ),
            symbol=lsp.WorkspaceSymbolClientCapabilities(
                dynamic_registration=True,
            ),
            execute_command=lsp.ExecuteCommandClientCapabilities(
                dynamic_registration=True,
            ),
            workspace_folders=True,
            configuration=True,
        ),
        text_document=lsp.TextDocumentClientCapabilities(
            synchronization=lsp.TextDocumentSyncClientCapabilities(
                dynamic_registration=True,
                will_save=True,
                will_save_wait_until=True,
                did_save=True,
            ),
            completion=lsp.CompletionClientCapabilities(
                dynamic_registration=True,
                completion_item=(
                    lsp.ClientCompletionItemOptions(
                        snippet_support=True,
                        documentation_format=[lsp.MarkupKind.PlainText],
                    )
                ),
            ),
            hover=lsp.HoverClientCapabilities(
                dynamic_registration=True,
                content_format=[lsp.MarkupKind.PlainText],
            ),
            signature_help=lsp.SignatureHelpClientCapabilities(
                dynamic_registration=True,
                signature_information=(
                    lsp.ClientSignatureInformationOptions(
                        documentation_format=[lsp.MarkupKind.PlainText],
                    )
                ),
            ),
            references=lsp.ReferenceClientCapabilities(
                dynamic_registration=True,
            ),
            document_highlight=lsp.DocumentHighlightClientCapabilities(
                dynamic_registration=True,
            ),
            document_symbol=lsp.DocumentSymbolClientCapabilities(
                dynamic_registration=True,
            ),
            formatting=lsp.DocumentFormattingClientCapabilities(
                dynamic_registration=True,
            ),
            range_formatting=lsp.DocumentRangeFormattingClientCapabilities(
                dynamic_registration=True,
            ),
            on_type_formatting=lsp.DocumentOnTypeFormattingClientCapabilities(
                dynamic_registration=True,
            ),
            definition=lsp.DefinitionClientCapabilities(
                dynamic_registration=True,
            ),
            code_action=lsp.CodeActionClientCapabilities(
                dynamic_registration=True,
            ),
            code_lens=lsp.CodeLensClientCapabilities(
                dynamic_registration=True,
            ),
            document_link=lsp.DocumentLinkClientCapabilities(
                dynamic_registration=True,
            ),
            rename=lsp.RenameClientCapabilities(
                dynamic_registration=True,
            ),
        ),
    )


class _SpyderPyglsClient(JsonRPCClient):
    """
    pygls JsonRPCClient subclass that routes server-initiated notifications
    and requests back to the Qt-thread LSPClient via AsyncDispatcher.
    """

    def __init__(self, qt_client: 'LSPClient', name: str, version: str) -> None:
        self.name = name
        self.version = version
        super().__init__(
            protocol_cls=LanguageServerProtocol,
            converter_factory=_spyder_converter,
        )
        self._qt_client = qt_client
        self._register_server_handlers()

    def _register_server_handlers(self) -> None:
        """Register handlers for server-to-client messages."""
        qt = self._qt_client

        # --- Notifications (server -> client, no response required) ---

        @self.feature(lsp.TEXT_DOCUMENT_PUBLISH_DIAGNOSTICS)
        def on_diagnostics(params: lsp.PublishDiagnosticsParams) -> None:
            qt._post_notification(
                lsp.TEXT_DOCUMENT_PUBLISH_DIAGNOSTICS, params
            )

        @self.feature(lsp.WINDOW_SHOW_MESSAGE)
        def on_show_message(params: lsp.ShowMessageParams) -> None:
            qt._post_notification(
                lsp.WINDOW_SHOW_MESSAGE, params
            )

        @self.feature(lsp.WINDOW_LOG_MESSAGE)
        def on_log_message(params: lsp.LogMessageParams) -> None:
            qt._post_notification(
                lsp.WINDOW_LOG_MESSAGE, params
            )

        # --- Requests from server (require a response) ---

        @self.feature(lsp.WORKSPACE_WORKSPACE_FOLDERS)
        def on_workspace_folders(params: None) -> list:
            """Return the currently open workspace folders."""
            folders = []
            for folder_name, folder_data in qt.watched_folders.items():
                folders.append(
                    lsp.WorkspaceFolder(
                        uri=folder_data['uri'],
                        name=folder_name,
                    )
                )
            return folders

        @self.feature(lsp.WORKSPACE_CONFIGURATION)
        def on_workspace_configuration(
            params: lsp.ConfigurationParams,
        ) -> list:
            """Return workspace configuration items requested by the server."""
            return [qt.configurations] * len(params.items)

        @self.feature(lsp.WORKSPACE_APPLY_EDIT)
        def on_apply_edit(
            params: lsp.ApplyWorkspaceEditParams,
        ) -> lsp.ApplyWorkspaceEditResult:
            """Route edit application to the Qt thread; acknowledge immediately."""
            qt._post_notification(
                lsp.WORKSPACE_APPLY_EDIT, params
            )
            return lsp.ApplyWorkspaceEditResult(applied=True)

        @self.feature(lsp.CLIENT_REGISTER_CAPABILITY)
        def on_register_capability(params: lsp.RegistrationParams) -> None:
            qt._post_notification(
                lsp.CLIENT_REGISTER_CAPABILITY, params
            )


@class_register
class LSPClient(QObject, LSPMethodProviderMixIn, SpyderConfigurationAccessor):
    """
    Language Server Protocol v3.0 client.

    Wraps a pygls BaseLanguageClient running in a dedicated asyncio thread.
    """

    sender_registry: dict[str, str]  # method_name -> builder method name
    handler_registry: dict[str, str]  # method_name -> handler method name

    # --- Public Qt signals ---

    #: Emitted when the server has initialised and is ready for requests.
    sig_initialize = Signal(object, str)

    #: Emitted when the server reports a recoverable error (debug/dev modes).
    sig_server_error = Signal(str)

    #: Emitted when the LSP server process has gone down.
    sig_went_down = Signal(str)

    def __init__(
        self,
        parent,
        server_settings: dict = {},
        folder: str = getcwd_or_home(),
        language: str = 'python',
    ) -> None:
        QObject.__init__(self)
        self.manager = parent
        self.language = language
        self.folder = folder

        self.initialized = False
        self.ready_to_close = False
        self.server_unresponsive = False
        self.req_reply: dict[int, typing.Callable] = {}       # req_id -> callback
        self.watched_files: dict = {}   # uri -> [editor, ...]
        self.watched_folders: dict[str, WatchedFolder] = {}

        # Request sequence counter (thread access: increment only from Qt thread)
        self._request_seq = 1
        self._requests = []  # kept only for testing

        # Server connection settings
        self.external_server = server_settings.get('external', False)
        self.stdio = server_settings.get('stdio', False)

        if self.stdio and self.external_server:
            raise AssertionError(
                'A server cannot use stdio and be external at the same time.'
            )

        self.server_host = server_settings['host']
        self.configurations = server_settings.get('configurations', {})

        if not server_settings['external']:
            self.server_port = select_port(
                default_port=server_settings['port']
            )
        else:
            self.server_port = server_settings['port']

        self._server_args = server_settings.get('args', '')
        self._server_cmd = server_settings['cmd']

        # LSP capabilities
        self.client_capabilites = _build_client_capabilities()
        self.server_capabilites: lsp.ServerCapabilities | None = None

        # QProcess for TCP-mode server management (not used in stdio mode)
        self.server: QProcess | None = None

        # pygls client
        self._pygls_client = _SpyderPyglsClient(self, f"spyder-{self.language}", "0.1.0")

    # ------------------------------------------------------------------
    # Properties / helpers
    # ------------------------------------------------------------------

    def _next_req_id(self) -> int:
        req_id = self._request_seq
        self._request_seq += 1
        return req_id

    @property
    def _log_dir(self) -> str:
        return get_conf_path(osp.join('lsp_logs'))

    def _get_log_filename(self, kind: str) -> str | None:
        if get_debug_level() == 0:
            return None
        fname = '{0}_{1}_{2}.log'.format(kind, self.language, os.getpid())
        location = osp.join(self._log_dir, fname)
        os.makedirs(osp.dirname(location), exist_ok=True)
        return location

    @property
    def server_log_file(self) -> str | None:
        return self._get_log_filename('server')

    @property
    def server_args(self) -> list:
        """Command and arguments to start the LSP server process."""
        args = []
        if self.language == 'python':
            args += [sys.executable, '-m']
        args += [self._server_cmd]

        host_and_port = self._server_args.format(
            host=self.server_host, port=self.server_port
        )
        if host_and_port:
            args += host_and_port.split()

        if self.language == 'python' and get_debug_level() > 0:
            args += ['--log-file', self.server_log_file]
            if get_debug_level() == 2:
                args.append('-v')
            elif get_debug_level() == 3:
                args.append('-vv')

        return args

    @property
    def stdio_pid(self) -> int | None:
        """Return the PID of the stdio server process, or None if not in stdio mode."""
        if not self.stdio:
            return None
        server = getattr(self._pygls_client, '_server', None)
        return getattr(server, 'pid', None) if server is not None else None

    def is_stdio_alive(self) -> bool:
        """Return True if the stdio server process is still running."""
        server = getattr(self._pygls_client, '_server', None)
        if server is None:
            return False
        # asyncio.subprocess.Process.returncode is None while the process runs
        return getattr(server, 'returncode', 1) is None

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def start_server(self) -> None:
        """Start the LSP server as a QProcess (TCP non-external mode only)."""
        if self.external_server or self.stdio:
            return

        logger.info('Starting server: %s', ' '.join(self.server_args))

        self.server = QProcess(self)
        env = self.server.processEnvironment()

        if self.language == 'python':
            # Set the PyLS current working to an empty dir inside
            # our config one. This avoids the server to pick up user
            # files such as random.py or string.py instead of the
            # standard library modules named the same.
            cwd = osp.join(get_conf_path(), 'lsp_paths', 'cwd')
            os.makedirs(cwd, exist_ok=True)

            if os.name == "nt":
                # On Windows, some modules (notably Matplotlib)
                # cause exceptions if they cannot get the user home.
                # So, we need to pass the USERPROFILE env variable to
                # the PyLSP.
                if "USERPROFILE" in os.environ:
                    env.insert("USERPROFILE", os.environ["USERPROFILE"])

                # The PyLSP can't start on pip installations if APPDATA
                # is missing and the user has installed their packages on
                # that directory.
                # Fixes spyder-ide/spyder#17661
                if not is_conda_env(sys.prefix) and "APPDATA" in os.environ:
                    env.insert("APPDATA", os.environ["APPDATA"])
        else:
            # There's no need to define a cwd for other servers.
            cwd = None

            # Most LSP servers spawn other processes, which may require
            # some environment variables.
            for var in os.environ:
                env.insert(var, os.environ[var])
            logger.info('Server process env variables: {0}'.format(env.keys()))

        self.server.setProcessEnvironment(env)
        self.server.errorOccurred.connect(self._handle_process_error)
        if cwd:
            self.server.setWorkingDirectory(cwd)
        self.server.setProcessChannelMode(QProcess.MergedChannels)
        if self.server_log_file:
            self.server.setStandardOutputFile(self.server_log_file)

        # Start server
        self.server.start(self.server_args[0], self.server_args[1:])

    def start(self) -> None:
        """Start the server process (if needed) and connect via asyncio."""
        self.start_server()
        self._connect()
        logger.debug('LSP %s client started.', self.language)

    def stop(self) -> None:
        """Send LSP shutdown/exit and kill the server process."""
        logger.info('Stopping %s client…', self.language)

        if self.initialized and not self._pygls_client.stopped:
            try:
                self._graceful_stop().result(timeout=3)
            except Exception:
                pass

        if self.server is not None:
            self.server.close()
            self.server.waitForFinished(1000)

    @Slot(QProcess.ProcessError)
    def _handle_process_error(self, _error) -> None:
        self.sig_went_down.emit(self.language)

    # ------------------------------------------------------------------
    # Asyncio connection and request dispatch
    # ------------------------------------------------------------------

    @AsyncDispatcher(loop=_LSP_LOOP)
    async def _graceful_stop(self) -> None:
        """Send shutdown and exit to the server (LSP graceful teardown)."""
        try:
            await self._pygls_client.protocol.send_request_async(
                lsp.SHUTDOWN, None
            )
            self._pygls_client.protocol.notify(lsp.EXIT, None)
        except Exception:
            pass

    @AsyncDispatcher(loop=_LSP_LOOP)
    async def _connect(self) -> None:
        """Establish the connection to the LSP server and send initialize."""
        try:
            if self.stdio:
                # pygls spawns and manages the server subprocess directly.
                await self._pygls_client.start_io(*self.server_args)
            else:
                # For TCP mode, wait briefly for the server to start, then
                # connect.  Retry on connection refused to handle slow starts.
                await self._connect_tcp()

            await self._initialize_server()
        except Exception:
            logger.exception('LSP %s: connection failed.', self.language)
            self.sig_went_down.emit(self.language)

    async def _connect_tcp(self, retries: int = 10, delay: float = 0.5) -> None:
        """Connect pygls client to the TCP LSP server with retries."""
        for attempt in range(retries):
            try:
                await self._pygls_client.start_tcp(
                    self.server_host, self.server_port
                )
                return
            except ConnectionRefusedError:
                if attempt == retries - 1:
                    raise
                await asyncio.sleep(delay)

    async def _initialize_server(self) -> None:
        """Send initialize, then initialized, then emit sig_initialize."""
        pid = os.getpid() if self.stdio else None
        result: lsp.InitializeResult = (
            await self._pygls_client.protocol.send_request_async(
                lsp.INITIALIZE,
                lsp.InitializeParams(
                    process_id=pid,
                    root_uri=pathlib.Path(
                        osp.abspath(self.folder)
                    ).as_uri(),
                    capabilities=self.client_capabilites,
                    trace=TRACE,
                ),
            )
        )
        if running_under_pytest():
            self._requests.append((0, lsp.INITIALIZE))
        self._process_server_capabilities(result)

    def _process_server_capabilities(
        self, result: lsp.InitializeResult
    ) -> None:
        """
        Store the server capabilities, send 'initialized', and emit
        sig_initialize on the Qt thread.
        """
        self.server_capabilites = result.capabilities

        # The initialized notification must be the first message after the
        # initialize response, per LSP spec.
        self._pygls_client.protocol.notify(
            lsp.INITIALIZED, lsp.InitializedParams()
        )
        if running_under_pytest():
            self._requests.append((None, lsp.INITIALIZED))

        self.initialized = True

        # Forward the configurations set in Spyder Preferences.
        self.configurations = self.configurations  # ensure attr exists
        self._pygls_client.protocol.notify(
            lsp.WORKSPACE_DID_CHANGE_CONFIGURATION,
            lsp.DidChangeConfigurationParams(settings=self.configurations),
        )
        if running_under_pytest():
            self._requests.append(
                (None, lsp.WORKSPACE_DID_CHANGE_CONFIGURATION)
            )

        # Inform the rest of Spyder that the server is ready.
        self.sig_initialize.emit(self.server_capabilites, self.language)

    # ------------------------------------------------------------------
    # Public request dispatch
    # ------------------------------------------------------------------

    def perform_request(self, method: str, params: RequestParams) -> int | None:
        """
        Dispatch *params* as an LSP request or notification for *method*.

        Returns the integer request-id for requests, None for notifications.
        """
        if not self.initialized and method != lsp.INITIALIZE:
            return None

        if method not in self.sender_registry:
            return None

        builder_name = self.sender_registry[method]
        builder = getattr(self, builder_name)
        lsp_params = builder(params)

        # None return from a builder means the operation was cancelled.
        if lsp_params is None:
            return None

        kind = getattr(builder, '_kind', 'request')

        if kind == 'notification':
            self._async_notification(method, lsp_params)
            return None

        # Request: allocate an id, register an optional callback, dispatch.
        req_id = self._next_req_id()
        if running_under_pytest():
            self._requests.append((req_id, method))

        if params.get('requires_response') and 'response_callback' in params:
            self.req_reply[req_id] = params['response_callback']

        # Capture method/req_id in a closure so the QtSlot can report errors.
        @AsyncDispatcher.QtSlot
        def _on_done(future):
            try:
                result = future.result()
                self._dispatch_response(method, req_id, result)
            except Exception:
                logger.exception(
                    'LSP request %s (id=%d) failed', method, req_id
                )
                if req_id in self.req_reply:
                    self.req_reply.pop(req_id)(None, None)

        self._async_request(method, lsp_params).connect(_on_done)
        return req_id

    @AsyncDispatcher(loop=_LSP_LOOP)
    async def _async_request(self, method: str, lsp_params):
        """Await a pygls request and return the result."""
        return await self._pygls_client.protocol.send_request_async(
            method, lsp_params
        )

    @AsyncDispatcher(loop=_LSP_LOOP)
    async def _async_notification(self, method: str, lsp_params) -> None:
        """Send an LSP notification (no response expected)."""
        try:
            self._pygls_client.protocol.notify(method, lsp_params)
        except Exception:
            logger.exception('LSP notification %s failed', method)

    def _post_notification(self, method: str, params) -> None:
        """Deliver a server notification to the Qt main thread.

        Called from the asyncio thread (inside pygls feature handlers).
        A pre-resolved DispatcherFuture carries the payload; connect() with
        the @AsyncDispatcher.QtSlot handler posts the callback to the Qt
        event loop via QCoreApplication.postEvent.
        """
        future = DispatcherFuture()
        future.set_result((method, params))
        future.connect(self._on_notification)

    @AsyncDispatcher.QtSlot
    def _on_notification(self, future) -> None:
        """Receive a server notification on the Qt main thread."""
        try:
            method, params = future.result()
            self._dispatch_notification(method, params)
        except Exception:
            logger.exception('LSP: error delivering server notification')

    def _dispatch_notification(self, method: str, params) -> None:
        """Route a server notification to the appropriate handler method."""
        try:
            if method in self.handler_registry:
                handler = getattr(self, self.handler_registry[method])
                handler(params)
        except RuntimeError:
            # CodeEditor may have been destroyed before the notification arrives.
            pass
        except Exception:
            logger.exception('Error handling notification %s', method)

    def _dispatch_response(self, method: str, req_id: int, result) -> None:
        """Route an LSP response to the appropriate handler method."""
        try:
            if method in self.handler_registry:
                handler = getattr(self, self.handler_registry[method])
                handler(result, req_id)
        except RuntimeError:
            pass
        except Exception:
            logger.exception('Error handling response %s (id=%d)', method, req_id)

    # ------------------------------------------------------------------
    # Shutdown helpers
    # ------------------------------------------------------------------

    def is_down(self) -> bool:
        """Return True when the LSP client or managed server has stopped."""
        if self._pygls_client.stopped:
            if not self.server_unresponsive:
                self.server_unresponsive = True
                self.sig_went_down.emit(self.language)
            return True

        if self.server is not None:
            if self.server.state() == QProcess.NotRunning:
                if not self.server_unresponsive:
                    self.server_unresponsive = True
                    self.sig_went_down.emit(self.language)
                return True

        return False

    # ------------------------------------------------------------------
    # Built-in initialization handlers
    # ------------------------------------------------------------------

    @handles(lsp.SHUTDOWN)
    def handle_shutdown(self, response, *args) -> None:
        self.ready_to_close = True

    # ------------------------------------------------------------------
    # Settings queries (unchanged interface)
    # ------------------------------------------------------------------

    @property
    def support_multiple_workspaces(self) -> bool:
        if self.server_capabilites is None:
            return False
        ws = self.server_capabilites.workspace
        wf = ws.workspace_folders if ws else None
        return bool(wf and wf.supported)

    @property
    def support_workspace_update(self) -> bool:
        if self.server_capabilites is None:
            return False
        ws = self.server_capabilites.workspace
        wf = ws.workspace_folders if ws else None
        return bool(wf and wf.change_notifications)

    def send_configurations(self, configurations) -> None:
        """
        Send a workspace/didChangeConfiguration notification to the server.

        Called directly by LanguageServerProvider when Preferences change.
        If the server is not yet initialised the new value is stored and will
        be forwarded automatically inside _process_server_capabilities.
        """
        self.configurations = configurations
        if not self.initialized:
            return
        self._async_notification(
            lsp.WORKSPACE_DID_CHANGE_CONFIGURATION,
            lsp.DidChangeConfigurationParams(settings=configurations),
        )
