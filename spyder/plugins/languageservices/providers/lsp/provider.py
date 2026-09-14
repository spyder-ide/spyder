# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""
Generic language server client provider.

Manages any number of language servers described by
:class:`~spyder.plugins.languageservices.providers.lsp.config.ServerConfig`
objects and knows nothing about particular languages or servers. The
servers come from the provider configuration (``("servers", <name>)``) or,
for subclasses, from :meth:`LanguageServerClientProvider.get_server_configs`.
"""

from __future__ import annotations

# Standard library imports
import asyncio
import logging
import os
import os.path as osp
import sys
import traceback
from collections.abc import Iterable
from dataclasses import dataclass, field
from typing import Any

# Third party imports
from lsprotocol import types as lsp
from qtpy.QtCore import Signal

# Local imports
from spyder.api.config.decorators import on_conf_change
from spyder.api.translations import _
from spyder.config.base import get_conf_path, running_under_pytest
from spyder.plugins.languageservices.api.languages import Language
from spyder.plugins.languageservices.api.policies import merge_strategy
from spyder.plugins.languageservices.api.provider import (
    FEATURE_METHODS,
    LanguageServicesProvider,
    ProviderStatus,
    supports_method,
)
from spyder.plugins.languageservices.providers.lsp.config import ServerConfig
from spyder.plugins.languageservices.providers.lsp.connection import (
    LanguageServerConnection,
    ServerDownError,
)
from spyder.plugins.languageservices.providers.lsp.widgets.status import (
    LSPStatusWidget,
)
from spyder.utils.misc import check_connection_port

logger = logging.getLogger(__name__)


@dataclass
class _ServerState:
    config: ServerConfig
    connection: LanguageServerConnection | None = None
    status: ProviderStatus = ProviderStatus.STOPPED
    restart_attempts: int = 0
    documents: dict[str, str] = field(default_factory=dict)
    """Documents opened in this server (uri -> language_id)."""
    task: asyncio.Task | None = None
    """Start or restart task in progress."""

    @property
    def ready(self) -> bool:
        return (
            self.status is ProviderStatus.READY
            and self.connection is not None
            and self.connection.initialized
        )


class LanguageServerClientProvider(LanguageServicesProvider):
    """Language services from any number of LSP servers.

    Each server serves the languages given in its configuration, or those
    it registers through ``client/registerCapability`` document selectors
    when configured with ``languages="auto"``. Requests fan out to every
    ready server of the document's language and the answers are merged
    with the same strategies the plugin uses across providers.

    A server that goes down is restarted up to :attr:`MAX_RESTART_ATTEMPTS`
    times, :attr:`RESTART_DELAY` seconds apart.
    """

    NAME = "lsp"
    PRIORITY = 10
    CONF_DEFAULTS = [("servers", {}), ("show_lsp_down_warning", True)]
    CONF_VERSION = "0.1.0"
    STATUS_BAR_CLASSES = [LSPStatusWidget]

    MAX_RESTART_ATTEMPTS = 5
    RESTART_DELAY = 10.0
    HEARTBEAT_INTERVAL = 3.0

    sig_server_status_changed = Signal(str, str)
    """A server changed status.

    Parameters
    ----------
    server: str
    status: ProviderStatus
    """

    def __init__(self, plugin, config=None):
        super().__init__(plugin, config)
        self._servers: dict[str, _ServerState] = {}
        self._heartbeat: asyncio.Task | None = None
        self._interpreter = sys.executable
        self._workspace_folders: dict[str, lsp.WorkspaceFolder] = {}
        self._started = False

    # ---- Configuration ---------------------------------------------------
    def get_server_configs(self) -> list[ServerConfig]:
        """Servers to run. The base reads the ``servers`` option."""
        servers = self.get_conf("servers", {}) or {}
        return [
            ServerConfig.from_conf(name, dict(data))
            for name, data in servers.items()
        ]

    def get_root_path(self) -> str:
        """Workspace root given to servers when no project is open.

        This is an empty directory inside the configuration folder. A home
        folder with many files makes servers index for a long time.
        """
        path = osp.join(get_conf_path(), "lsp_paths", "root_path")
        os.makedirs(path, exist_ok=True)
        return path

    @on_conf_change(option="servers")
    def _on_servers_changed(self, servers):
        """Restart, reconfigure or stop servers to match configuration edits."""
        if not self._started:
            return
        from spyder.plugins.languageservices.plugin import dispatch

        dispatch(self.apply_server_configs)(self.get_server_configs())

    async def apply_server_configs(self, configs: Iterable[ServerConfig]) -> None:
        """Reconcile the running servers with ``configs``."""
        wanted = {config.name: config for config in configs}
        for name in list(self._servers):
            if name not in wanted:
                await self._stop_server(name)
                del self._servers[name]
        for name, config in wanted.items():
            state = self._servers.get(name)
            if state is None:
                self._servers[name] = _ServerState(config)
                if config.auto_languages:
                    await self._start_server(name)
                continue
            if state.config.needs_restart(config):
                logger.debug("Restart required for server %r", name)
                running = state.status is not ProviderStatus.STOPPED
                await self._stop_server(name)
                state.config = config
                if running:
                    await self._start_server(name)
            else:
                state.config = config
                if state.connection is not None:
                    state.connection.send_configurations(config.configurations)

    # ---- Lifecycle -------------------------------------------------------
    async def start(self) -> None:
        self._started = True
        for config in self.get_server_configs():
            self._servers[config.name] = _ServerState(config)
        # Servers with explicit languages start when a document of one of
        # them is opened. Auto-detected ones must run to report theirs.
        for name, state in self._servers.items():
            if state.config.auto_languages:
                await self._start_server(name)
        self._heartbeat = asyncio.ensure_future(self._heartbeat_loop())

    async def stop(self) -> None:
        self._started = False
        if self._heartbeat is not None:
            self._heartbeat.cancel()
            self._heartbeat = None
        for name in list(self._servers):
            await self._stop_server(name)

    async def start_language(self, language: Language) -> None:
        for name, state in self._servers.items():
            if state.status is ProviderStatus.STOPPED and (
                language in self._configured_languages(state.config)
            ):
                await self._start_server(name)

    async def stop_language(self, language: Language) -> None:
        for name, state in self._servers.items():
            if state.status is not ProviderStatus.STOPPED and (
                language in self._server_languages(state)
            ):
                await self._stop_server(name)

    async def restart_server(self, name: str) -> None:
        """Stop and start a server (user request)."""
        state = self._servers[name]
        state.restart_attempts = 0
        await self._stop_server(name)
        await self._start_server(name)

    async def restart_language(self, language: Language) -> None:
        for name, state in list(self._servers.items()):
            if language in self._server_languages(state) or (
                language in self._configured_languages(state.config)
            ):
                await self.restart_server(name)

    def server_names(self) -> list[str]:
        return list(self._servers)

    def server_status(self, name: str) -> ProviderStatus:
        return self._servers[name].status

    def servers_for(self, language: Language) -> list[str]:
        """Names of the servers configured or detected for ``language``."""
        return [
            name
            for name, state in self._servers.items()
            if language in self._server_languages(state)
            or language in self._configured_languages(state.config)
        ]

    # ---- Server management -----------------------------------------------
    @staticmethod
    def _configured_languages(config: ServerConfig) -> frozenset[Language]:
        if config.auto_languages:
            return frozenset()
        languages: set[Language] = set()
        for language_id in config.languages:
            try:
                languages |= Language.from_language_id(language_id)
            except LookupError:
                logger.warning(
                    "Server %r configured for unknown language_id %r",
                    config.name,
                    language_id,
                )
        return frozenset(languages)

    def _server_languages(self, state: _ServerState) -> frozenset[Language]:
        if state.connection is None or not state.connection.initialized:
            return frozenset()
        return state.connection.languages()

    def _set_status(self, state: _ServerState, status: ProviderStatus) -> None:
        state.status = status
        self.sig_server_status_changed.emit(state.config.name, status)
        languages = self._server_languages(state) | self._configured_languages(
            state.config
        )
        for language in languages:
            self.sig_status_changed.emit(language, status)

    async def _start_server(self, name: str) -> None:
        state = self._servers[name]
        if state.status in (ProviderStatus.STARTING, ProviderStatus.READY):
            return
        config = state.config
        if config.external and not check_connection_port(config.host, config.port):
            self._report_no_external_server(config)
            self._set_status(state, ProviderStatus.DOWN)
            return

        self._set_status(state, ProviderStatus.STARTING)
        connection = LanguageServerConnection(
            config,
            self.get_root_path(),
            self._make_notification_handler(name),
            interpreter=self._interpreter,
        )
        connection.workspace_folders = dict(self._workspace_folders)
        state.connection = connection
        try:
            await connection.start()
        except Exception as exc:  # noqa: BLE001
            logger.exception("Server %r failed to start", name)
            await connection.stop()
            state.connection = None
            self._set_status(state, ProviderStatus.DOWN)
            self.sig_exception_occurred.emit(
                {
                    "text": "".join(traceback.format_exception(exc)),
                    "is_traceback": True,
                    "repo": "spyder-ide/spyder",
                    "title": _("Language server {0} failed to start").format(
                        name
                    ),
                    "label": "",
                    "steps": "",
                }
            )
            return

        state.restart_attempts = 0
        self._set_status(state, ProviderStatus.READY)
        for language in self._server_languages(state):
            self.sig_capabilities_changed.emit(
                language, self.capabilities(language)
            )
        if self._workspace_folders and connection.supports_workspace_folder_changes:
            connection.notify(
                lsp.WORKSPACE_DID_CHANGE_WORKSPACE_FOLDERS,
                lsp.DidChangeWorkspaceFoldersParams(
                    event=lsp.WorkspaceFoldersChangeEvent(
                        added=list(self._workspace_folders.values()),
                        removed=[],
                    )
                ),
            )

    async def _stop_server(self, name: str) -> None:
        state = self._servers[name]
        if state.task is not None:
            state.task.cancel()
            state.task = None
        languages = self._server_languages(state)
        connection, state.connection = state.connection, None
        if connection is not None:
            await connection.stop()
        for uri in list(state.documents):
            self.sig_diagnostics.emit(
                lsp.PublishDiagnosticsParams(uri=uri, diagnostics=[])
            )
        state.documents.clear()
        self._set_status(state, ProviderStatus.STOPPED)
        for language in languages:
            self.sig_capabilities_changed.emit(
                language, self.capabilities(language)
            )

    async def _heartbeat_loop(self) -> None:
        while True:
            await asyncio.sleep(self.HEARTBEAT_INTERVAL)
            for name, state in list(self._servers.items()):
                if state.status is ProviderStatus.READY and (
                    state.connection is None or state.connection.is_down()
                ):
                    self._handle_server_down(name)

    def _handle_server_down(self, name: str) -> None:
        state = self._servers[name]
        logger.warning("Server %r went down", name)
        if state.task is not None and not state.task.done():
            return
        state.task = asyncio.ensure_future(self._restart_after_failure(name))

    async def _restart_after_failure(self, name: str) -> None:
        state = self._servers[name]
        await self._stop_server(name)
        if running_under_pytest():
            self._set_status(state, ProviderStatus.DOWN)
            return
        while state.restart_attempts < self.MAX_RESTART_ATTEMPTS:
            state.restart_attempts += 1
            logger.info(
                "Restart attempt %d for server %r", state.restart_attempts, name
            )
            await self._start_server(name)
            if state.status is ProviderStatus.READY:
                return
            await asyncio.sleep(self.RESTART_DELAY)
        self._set_status(state, ProviderStatus.DOWN)
        self._report_server_down(name)

    # ---- Reports ---------------------------------------------------------
    def _report_no_external_server(self, config: ServerConfig) -> None:
        self.sig_show_message.emit(
            lsp.ShowMessageParams(
                type=lsp.MessageType.Warning,
                message=_(
                    "It appears there is no language server listening at "
                    "{host}:{port} (server {name}). Completion and linting "
                    "for its languages will not work during this session."
                ).format(host=config.host, port=config.port, name=config.name),
            )
        )

    def _report_server_down(self, name: str) -> None:
        if not self.get_conf("show_lsp_down_warning", True):
            return
        self.sig_show_message.emit(
            lsp.ShowMessageParams(
                type=lsp.MessageType.Warning,
                message=_(
                    "The language server {name} stopped working and could "
                    "not be restarted. Completion and linting for its "
                    "languages will not work until Spyder is restarted."
                ).format(name=name),
            )
        )

    # ---- Provider API ----------------------------------------------------
    def supported_languages(self) -> frozenset[Language]:
        languages: set[Language] = set()
        for state in self._servers.values():
            if state.ready:
                languages |= self._server_languages(state)
        return frozenset(languages)

    def capabilities(self, language: Language) -> lsp.ServerCapabilities | None:
        from spyder.plugins.languageservices.services import merge_capabilities

        connections = self._ready_connections(language)
        if not connections:
            return None
        return merge_capabilities([c.capabilities for c in connections])

    def _ready_connections(
        self, language: Language, method: str | None = None
    ) -> list[LanguageServerConnection]:
        connections = []
        for state in self._servers.values():
            if not state.ready or language not in self._server_languages(state):
                continue
            if method is not None and not supports_method(
                state.connection.capabilities, method
            ):
                continue
            connections.append(state.connection)
        return connections

    def _language_of(self, uri: str) -> Language | None:
        for state in self._servers.values():
            language_id = state.documents.get(uri)
            if language_id is not None:
                candidates = Language.from_language_id(language_id)
                return next(iter(candidates))
        return None

    def _states_with_document(self, uri: str) -> list[_ServerState]:
        return [
            state
            for state in self._servers.values()
            if uri in state.documents and state.ready
        ]

    # ---- Document sync ---------------------------------------------------
    async def did_open(self, params: lsp.DidOpenTextDocumentParams) -> None:
        item = params.text_document
        for language in Language.from_language_id(item.language_id):
            for state in self._servers.values():
                if not state.ready or item.uri in state.documents:
                    continue
                if language not in self._server_languages(state):
                    continue
                state.documents[item.uri] = item.language_id
                state.connection.notify(lsp.TEXT_DOCUMENT_DID_OPEN, params)

    async def did_change(self, params: lsp.DidChangeTextDocumentParams) -> None:
        uri = params.text_document.uri
        for state in self._states_with_document(uri):
            state.connection.notify(lsp.TEXT_DOCUMENT_DID_CHANGE, params)

    async def did_save(self, params: lsp.DidSaveTextDocumentParams) -> None:
        for state in self._states_with_document(params.text_document.uri):
            state.connection.notify(lsp.TEXT_DOCUMENT_DID_SAVE, params)

    async def did_close(self, params: lsp.DidCloseTextDocumentParams) -> None:
        uri = params.text_document.uri
        for state in self._states_with_document(uri):
            state.documents.pop(uri, None)
            state.connection.notify(lsp.TEXT_DOCUMENT_DID_CLOSE, params)

    # ---- Features --------------------------------------------------------
    async def _fan_out(self, method: str, params: Any, uri: str | None) -> Any:
        if uri is not None:
            connections = [
                state.connection
                for state in self._states_with_document(uri)
                if supports_method(state.connection.capabilities, method)
            ]
        else:
            connections = [
                state.connection for state in self._servers.values() if state.ready
            ]
        if not connections:
            return None
        results = await asyncio.gather(
            *(
                self._call(connection, method, params)
                for connection in connections
            ),
            return_exceptions=True,
        )
        good = []
        for connection, result in zip(connections, results):
            if isinstance(result, asyncio.CancelledError):
                raise result
            if isinstance(result, BaseException):
                logger.error(
                    "Server %r failed answering %s",
                    connection.name,
                    method,
                    exc_info=result,
                )
            elif result is not None:
                good.append((connection.name, result))
        return merge_strategy(method)(good) if good else None

    async def _call(self, connection, method, params):
        return await connection.request(method, params)

    async def completion(self, params):
        return await self._fan_out(
            lsp.TEXT_DOCUMENT_COMPLETION, params, params.text_document.uri
        )

    async def resolve_completion_item(self, item: lsp.CompletionItem):
        data = item.data if isinstance(item.data, dict) else {}
        uri = data.get("uri")
        if uri is None:
            return None
        return await self._fan_out(lsp.COMPLETION_ITEM_RESOLVE, item, uri)

    async def hover(self, params):
        return await self._fan_out(
            lsp.TEXT_DOCUMENT_HOVER, params, params.text_document.uri
        )

    async def signature_help(self, params):
        return await self._fan_out(
            lsp.TEXT_DOCUMENT_SIGNATURE_HELP, params, params.text_document.uri
        )

    async def definition(self, params):
        return await self._fan_out(
            lsp.TEXT_DOCUMENT_DEFINITION, params, params.text_document.uri
        )

    async def references(self, params):
        return await self._fan_out(
            lsp.TEXT_DOCUMENT_REFERENCES, params, params.text_document.uri
        )

    async def document_symbol(self, params):
        return await self._fan_out(
            lsp.TEXT_DOCUMENT_DOCUMENT_SYMBOL, params, params.text_document.uri
        )

    async def folding_range(self, params):
        return await self._fan_out(
            lsp.TEXT_DOCUMENT_FOLDING_RANGE, params, params.text_document.uri
        )

    async def formatting(self, params):
        return await self._fan_out(
            lsp.TEXT_DOCUMENT_FORMATTING, params, params.text_document.uri
        )

    async def range_formatting(self, params):
        return await self._fan_out(
            lsp.TEXT_DOCUMENT_RANGE_FORMATTING, params, params.text_document.uri
        )

    async def code_action(self, params):
        return await self._fan_out(
            lsp.TEXT_DOCUMENT_CODE_ACTION, params, params.text_document.uri
        )

    async def rename(self, params):
        return await self._fan_out(
            lsp.TEXT_DOCUMENT_RENAME, params, params.text_document.uri
        )

    async def workspace_symbol(self, params):
        return await self._fan_out(lsp.WORKSPACE_SYMBOL, params, None)

    async def execute_command(self, params):
        return await self._fan_out(lsp.WORKSPACE_EXECUTE_COMMAND, params, None)

    # ---- Workspace -------------------------------------------------------
    async def did_change_workspace_folders(
        self, params: lsp.DidChangeWorkspaceFoldersParams
    ) -> None:
        for folder in params.event.added:
            self._workspace_folders[folder.uri] = folder
        for folder in params.event.removed:
            self._workspace_folders.pop(folder.uri, None)
        for state in self._servers.values():
            if not state.ready:
                continue
            connection = state.connection
            connection.workspace_folders = dict(self._workspace_folders)
            if connection.supports_workspace_folder_changes:
                connection.notify(lsp.WORKSPACE_DID_CHANGE_WORKSPACE_FOLDERS, params)
            else:
                logger.debug(
                    "Server %r does not support workspace folders. Restarting",
                    connection.name,
                )
                await self.restart_server(state.config.name)

    async def did_change_watched_files(
        self, params: lsp.DidChangeWatchedFilesParams
    ) -> None:
        for state in self._servers.values():
            if state.ready:
                state.connection.notify(lsp.WORKSPACE_DID_CHANGE_WATCHED_FILES, params)

    async def did_change_configuration(
        self, params: lsp.DidChangeConfigurationParams
    ) -> None:
        for state in self._servers.values():
            if state.ready:
                state.connection.notify(lsp.WORKSPACE_DID_CHANGE_CONFIGURATION, params)

    async def on_interpreter_changed(self, interpreter: str) -> None:
        self._interpreter = interpreter

    # ---- Server notifications --------------------------------------------
    def _make_notification_handler(self, name: str):
        def handler(method: str, params: Any) -> None:
            self._on_server_notification(name, method, params)

        return handler

    def _on_server_notification(self, name: str, method: str, params: Any) -> None:
        state = self._servers.get(name)
        if state is None or state.connection is None:
            return
        if method == lsp.TEXT_DOCUMENT_PUBLISH_DIAGNOSTICS:
            if params.uri not in state.documents:
                logger.debug("Diagnostics for a document not open: %s", params.uri)
                return
            for diagnostic in params.diagnostics:
                if not diagnostic.source:
                    diagnostic.source = name
            self.sig_diagnostics.emit(params)
        elif method == lsp.WINDOW_SHOW_MESSAGE:
            self.sig_show_message.emit(params)
        elif method == lsp.WINDOW_LOG_MESSAGE:
            self.sig_log_message.emit(params)
        elif method == lsp.WORKSPACE_APPLY_EDIT:
            self.sig_apply_edit.emit(params)
        elif method == lsp.CLIENT_REGISTER_CAPABILITY:
            if state.config.auto_languages and state.ready:
                for language in self._server_languages(state):
                    self.sig_capabilities_changed.emit(
                        language, self.capabilities(language)
                    )
