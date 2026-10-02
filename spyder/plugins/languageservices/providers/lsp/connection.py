# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""
Connection to one language server.

Every method runs on the language services event loop. The server process
(when Spyder starts it) is an asyncio subprocess. Communication goes
through pygls over stdio or TCP.
"""

from __future__ import annotations

# Standard library imports
import asyncio
import collections
import logging
import os
import os.path as osp
import sys
import uuid
from collections.abc import Callable
from typing import Any

# Third party imports
from lsprotocol import types as lsp

# Local imports
from spyder.config.base import DEV, get_conf_path, get_debug_level
from spyder.plugins.languageservices.api.languages import Language
from spyder.plugins.languageservices.api.uri import path_as_uri
from spyder.plugins.languageservices.providers.lsp.config import ServerConfig
from spyder.plugins.languageservices.providers.lsp.pygls_client import (
    SpyderPyglsClient,
)
from spyder.utils.misc import select_port

logger = logging.getLogger(__name__)

TRACE = lsp.TraceValue.Verbose if DEV else lsp.TraceValue.Messages
TCP_CONNECT_RETRIES = 20
TCP_CONNECT_DELAY = 0.5


class ServerDownError(RuntimeError):
    """The server process or connection is not available."""


class LanguageServerConnection:
    """pygls connection to the server described by a :class:`ServerConfig`.

    Parameters
    ----------
    config: ServerConfig
    root_path: str
        Workspace root sent in ``initialize``.
    on_notification: Callable[[str, Any], None]
        Receives server notifications (``method, params``) and
        ``workspace/applyEdit`` requests.
    interpreter: str
        Python used for ``python_module`` servers.
    """

    def __init__(
        self,
        config: ServerConfig,
        root_path: str,
        on_notification: Callable[[str, Any], None],
        interpreter: str = sys.executable,
    ):
        self.config = config
        self.root_path = root_path
        self.interpreter = interpreter
        self._on_notification = on_notification
        self.configurations: dict[str, Any] = dict(config.configurations)
        self.workspace_folders: dict[str, lsp.WorkspaceFolder] = {}

        self.initialized = False
        self.capabilities: lsp.ServerCapabilities | None = None
        self.registered_languages: set[str] = set()
        """``languageId``\\s of the document selectors the server registered
        with ``client/registerCapability``."""

        self.port = (
            config.port if config.external else select_port(config.port)
        )
        self.sent_methods: collections.deque[str] = collections.deque(maxlen=200)
        """Methods of the last messages sent, in order (for diagnosis)."""
        self._process: asyncio.subprocess.Process | None = None
        self._client = SpyderPyglsClient(self, f"spyder-{config.name}")

    # ---- Process ---------------------------------------------------------
    @property
    def name(self) -> str:
        return self.config.name

    @property
    def log_file(self) -> str | None:
        if get_debug_level() == 0:
            return None
        directory = get_conf_path("lsp_logs")
        os.makedirs(directory, exist_ok=True)
        return osp.join(directory, f"server_{self.name}_{os.getpid()}.log")

    def command(self) -> list[str]:
        """Command line starting the server."""
        config = self.config
        args = [self.interpreter, "-m", config.cmd] if config.python_module else [config.cmd]
        extra = config.args.format(host=config.host, port=self.port)
        if extra:
            args += extra.split()
        return args

    def _environment(self) -> dict[str, str]:
        env = dict(os.environ)
        if self.config.python_module:
            # pylsp picks up random user files named like stdlib modules
            # when started from the user's cwd. Use an empty directory.
            env.setdefault("PYTHONIOENCODING", "utf-8")
        return env

    def _working_directory(self) -> str | None:
        if self.config.python_module:
            cwd = osp.join(get_conf_path(), "lsp_paths", "cwd")
            os.makedirs(cwd, exist_ok=True)
            return cwd
        return None

    async def _start_process(self) -> None:
        command = self.command()
        logger.info("Starting server %r: %s", self.name, " ".join(command))
        stdout = (
            open(self.log_file, "ab") if self.log_file else asyncio.subprocess.DEVNULL
        )
        self._process = await asyncio.create_subprocess_exec(
            *command,
            cwd=self._working_directory(),
            env=self._environment(),
            stdout=stdout,
            stderr=asyncio.subprocess.STDOUT,
        )

    @property
    def process_alive(self) -> bool:
        if self.config.stdio:
            server = getattr(self._client, "_server", None)
            return server is not None and server.returncode is None
        if self.config.external:
            return True
        return self._process is not None and self._process.returncode is None

    def is_down(self) -> bool:
        """Whether the server or its connection stopped."""
        if self._client.stopped:
            return True
        return self.initialized and not self.process_alive

    # ---- Lifecycle -------------------------------------------------------
    async def start(self) -> lsp.ServerCapabilities:
        """Start (or connect to) the server and run the initialize
        handshake. Returns the server capabilities."""
        if self.config.stdio:
            await self._client.start_io(*self.command())
        else:
            if not self.config.external:
                await self._start_process()
            await self._connect_tcp()
        return await self._initialize()

    async def _connect_tcp(self) -> None:
        for attempt in range(TCP_CONNECT_RETRIES):
            if not self.process_alive:
                raise ServerDownError(
                    f"Server {self.name!r} exited before accepting connections"
                )
            try:
                await self._client.start_tcp(self.config.host, self.port)
                return
            except (ConnectionRefusedError, OSError):
                if attempt == TCP_CONNECT_RETRIES - 1:
                    raise
                await asyncio.sleep(TCP_CONNECT_DELAY)

    async def _initialize(self) -> lsp.ServerCapabilities:
        self.sent_methods.append(lsp.INITIALIZE)
        result: lsp.InitializeResult = await self._client.protocol.send_request_async(
            lsp.INITIALIZE,
            lsp.InitializeParams(
                process_id=os.getpid(),
                root_uri=path_as_uri(self.root_path),
                capabilities=self.client_capabilities(),
                trace=TRACE,
                initialization_options=self.config.initialization_options,
                workspace_folders=(
                    list(self.workspace_folders.values()) or None
                ),
            ),
        )
        self.capabilities = result.capabilities
        encoding = self.capabilities.position_encoding
        if encoding is not None and encoding != lsp.PositionEncodingKind.Utf16:
            raise ValueError(
                f"Server {self.name!r} selected position encoding "
                f"{encoding.value!r}; only UTF-16 is supported"
            )
        self.sent_methods.append(lsp.INITIALIZED)
        self._client.protocol.notify(lsp.INITIALIZED, lsp.InitializedParams())
        self.initialized = True
        self.notify(
            lsp.WORKSPACE_DID_CHANGE_CONFIGURATION,
            lsp.DidChangeConfigurationParams(settings=self.configurations),
        )
        return self.capabilities

    async def stop(self) -> None:
        """Shut the server down and release the process."""
        if self.initialized and not self._client.stopped:
            try:
                await asyncio.wait_for(
                    self._client.protocol.send_request_async(lsp.SHUTDOWN, None),
                    3,
                )
                self._client.protocol.notify(lsp.EXIT, None)
            except Exception:  # noqa: BLE001
                logger.debug("Server %r did not shut down cleanly", self.name)
        self.initialized = False
        try:
            await asyncio.wait_for(self._client.stop(), 3)
        except Exception:  # noqa: BLE001
            logger.debug("pygls client of %r did not stop cleanly", self.name)
        if self._process is not None and self._process.returncode is None:
            self._process.terminate()
            try:
                await asyncio.wait_for(self._process.wait(), 3)
            except asyncio.TimeoutError:
                self._process.kill()
        self._process = None

    # ---- Messages --------------------------------------------------------
    async def request(self, method: str, params: Any) -> Any:
        """Send a request and return its typed result.

        On cancellation, drop the pending request and send ``$/cancelRequest``.
        """
        if not self.initialized:
            raise ServerDownError(f"Server {self.name!r} is not initialized")
        protocol = self._client.protocol
        msg_id = str(uuid.uuid4())
        self.sent_methods.append(method)
        future = protocol.send_request(method, params, msg_id=msg_id)
        try:
            return await asyncio.wrap_future(future)
        except asyncio.CancelledError:
            # pygls resolves this future without checking for cancellation, so
            # a response arriving after the cancel would raise InvalidStateError
            # on the cancelled future. Drop the pending entry to ignore it.
            protocol._request_futures.pop(msg_id, None)
            protocol._result_types.pop(msg_id, None)
            if not self._client.stopped:
                protocol.notify(lsp.CANCEL_REQUEST, lsp.CancelParams(id=msg_id))
            raise

    def notify(self, method: str, params: Any) -> None:
        if not self.initialized:
            raise ServerDownError(f"Server {self.name!r} is not initialized")
        self.sent_methods.append(method)
        self._client.protocol.notify(method, params)

    def send_configurations(self, configurations: dict[str, Any]) -> None:
        self.configurations = configurations
        if self.initialized:
            self.notify(
                lsp.WORKSPACE_DID_CHANGE_CONFIGURATION,
                lsp.DidChangeConfigurationParams(settings=configurations),
            )

    # ---- Capabilities ----------------------------------------------------
    @property
    def supports_workspace_folders(self) -> bool:
        workspace = self.capabilities.workspace if self.capabilities else None
        folders = workspace.workspace_folders if workspace else None
        return bool(folders and folders.supported)

    @property
    def supports_workspace_folder_changes(self) -> bool:
        workspace = self.capabilities.workspace if self.capabilities else None
        folders = workspace.workspace_folders if workspace else None
        return bool(folders and folders.change_notifications)

    def languages(self) -> frozenset[Language]:
        """Languages served by language server.
         
        if ``auto`` is set, all languages are supported by default,
        unless the servers registers document selectors. Otherwise,
        the configured languages are used.

        The result is a frozenset of :class:`Language` objects.
        """
        if self.config.auto_languages:
            if not self.registered_languages:
                return frozenset(Language)
            ids = self.registered_languages
        else:
            ids = set(self.config.languages)
        languages: set[Language] = set()
        for language_id in ids:
            try:
                languages |= Language.from_language_id(language_id)
            except LookupError:
                logger.warning(
                    "Server %r serves unknown language_id %r",
                    self.name,
                    language_id,
                )
        return frozenset(languages)

    # ---- Server -> client ------------------------------------------------
    def on_server_notification(self, method: str, params: Any) -> None:
        self._on_notification(method, params)

    def on_register_capability(self, params: lsp.RegistrationParams) -> None:
        for registration in params.registrations:
            options = registration.register_options or {}
            selector = (
                options.get("documentSelector")
                if isinstance(options, dict)
                else getattr(options, "document_selector", None)
            )
            for entry in selector or ():
                language = (
                    entry.get("language")
                    if isinstance(entry, dict)
                    else getattr(entry, "language", None)
                )
                if language:
                    self.registered_languages.add(language)
        self._on_notification(lsp.CLIENT_REGISTER_CAPABILITY, params)

    def on_unregister_capability(self, params: lsp.UnregistrationParams) -> None:
        self._on_notification(lsp.CLIENT_UNREGISTER_CAPABILITY, params)

    # ---- Client capabilities ---------------------------------------------
    @staticmethod
    def client_capabilities() -> lsp.ClientCapabilities:
        """Capabilities advertised to every server."""
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
                    dynamic_registration=True
                ),
                did_change_watched_files=lsp.DidChangeWatchedFilesClientCapabilities(
                    dynamic_registration=True
                ),
                symbol=lsp.WorkspaceSymbolClientCapabilities(
                    dynamic_registration=True
                ),
                execute_command=lsp.ExecuteCommandClientCapabilities(
                    dynamic_registration=True
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
                    completion_item=lsp.ClientCompletionItemOptions(
                        snippet_support=True,
                        documentation_format=[lsp.MarkupKind.PlainText],
                    ),
                    context_support=True,
                ),
                hover=lsp.HoverClientCapabilities(
                    dynamic_registration=True,
                    content_format=[lsp.MarkupKind.PlainText],
                ),
                signature_help=lsp.SignatureHelpClientCapabilities(
                    dynamic_registration=True,
                    signature_information=lsp.ClientSignatureInformationOptions(
                        documentation_format=[lsp.MarkupKind.PlainText],
                        parameter_information=(
                            lsp.ClientSignatureParameterInformationOptions(
                                label_offset_support=True
                            )
                        ),
                    ),
                ),
                references=lsp.ReferenceClientCapabilities(
                    dynamic_registration=True
                ),
                document_highlight=lsp.DocumentHighlightClientCapabilities(
                    dynamic_registration=True
                ),
                document_symbol=lsp.DocumentSymbolClientCapabilities(
                    dynamic_registration=True,
                    symbol_kind=lsp.ClientSymbolKindOptions(
                        value_set=list(lsp.SymbolKind)
                    ),
                ),
                formatting=lsp.DocumentFormattingClientCapabilities(
                    dynamic_registration=True
                ),
                range_formatting=lsp.DocumentRangeFormattingClientCapabilities(
                    dynamic_registration=True
                ),
                on_type_formatting=lsp.DocumentOnTypeFormattingClientCapabilities(
                    dynamic_registration=True
                ),
                definition=lsp.DefinitionClientCapabilities(
                    dynamic_registration=True, link_support=True
                ),
                code_action=lsp.CodeActionClientCapabilities(
                    dynamic_registration=True
                ),
                code_lens=lsp.CodeLensClientCapabilities(
                    dynamic_registration=True
                ),
                document_link=lsp.DocumentLinkClientCapabilities(
                    dynamic_registration=True
                ),
                rename=lsp.RenameClientCapabilities(dynamic_registration=True),
                publish_diagnostics=lsp.PublishDiagnosticsClientCapabilities(),
                folding_range=lsp.FoldingRangeClientCapabilities(
                    dynamic_registration=True,
                    # The folding panel works on whole lines.
                    line_folding_only=True,
                ),
            ),
            general=lsp.GeneralClientCapabilities(
                position_encodings=[lsp.PositionEncodingKind.Utf16]
            ),
        )

