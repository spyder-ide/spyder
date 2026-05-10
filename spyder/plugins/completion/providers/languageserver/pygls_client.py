# -*- coding: utf-8 -*-

# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)
"""
Spyder Language Server Protocol Client implementation.
"""

from __future__ import annotations
from pygls.client import JsonRPCClient
from pygls.protocol import LanguageServerProtocol, default_converter
from lsprotocol import types as lsp
from typing import Optional, Union, TYPE_CHECKING
from spyder.plugins.completion.api import SpyderSymbolKind

if TYPE_CHECKING:
    from spyder.plugins.completion.providers.languageserver.client import LSPClient


def spyder_converter():
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
    _opt_notebook_filter = Optional[
        Union[
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

    converter.register_structure_hook(
        _opt_notebook_filter, _structure_opt_notebook_filter
    )

    # Register hook for custom for Spyder extended LSP SymbolKind
    def _structure_symbol_kind(obj, _):
        try:
            return lsp.SymbolKind(obj)
        except ValueError:
            return SpyderSymbolKind(obj)

    converter.register_structure_hook(lsp.SymbolKind, _structure_symbol_kind)

    return converter


class SpyderPyglsClient(JsonRPCClient):
    """
    pygls JsonRPCClient subclass that routes server-initiated notifications
    and requests back to the Qt-thread LSPClient via AsyncDispatcher.
    """

    def __init__(self, qt_client: LSPClient, name: str, version: str) -> None:
        self.name = name
        self.version = version
        super().__init__(
            protocol_cls=LanguageServerProtocol,
            converter_factory=spyder_converter,
        )
        self._qt_client = qt_client
        self._register_server_handlers()

    def _register_server_handlers(self) -> None:
        """Register handlers for server-to-client messages."""
        qt = self._qt_client

        # ---- Notifications (server -> client, no response required)
        @self.feature(lsp.TEXT_DOCUMENT_PUBLISH_DIAGNOSTICS)
        def on_diagnostics(params: lsp.PublishDiagnosticsParams) -> None:
            qt._post_notification(lsp.TEXT_DOCUMENT_PUBLISH_DIAGNOSTICS, params)

        @self.feature(lsp.WINDOW_SHOW_MESSAGE)
        def on_show_message(params: lsp.ShowMessageParams) -> None:
            qt._post_notification(lsp.WINDOW_SHOW_MESSAGE, params)

        @self.feature(lsp.WINDOW_LOG_MESSAGE)
        def on_log_message(params: lsp.LogMessageParams) -> None:
            qt._post_notification(lsp.WINDOW_LOG_MESSAGE, params)

        # ---- Requests from server (require a response)
        @self.feature(lsp.WORKSPACE_WORKSPACE_FOLDERS)
        def on_workspace_folders(params: None) -> list:
            """Return the currently open workspace folders."""
            folders = []
            for folder_name, folder_data in qt.watched_folders.items():
                folders.append(
                    lsp.WorkspaceFolder(
                        uri=folder_data["uri"],
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
            """
            Route edit application to the Qt thread; acknowledge immediately.
            """
            qt._post_notification(lsp.WORKSPACE_APPLY_EDIT, params)
            return lsp.ApplyWorkspaceEditResult(applied=True)

        @self.feature(lsp.CLIENT_REGISTER_CAPABILITY)
        def on_register_capability(params: lsp.RegistrationParams) -> None:
            qt._post_notification(lsp.CLIENT_REGISTER_CAPABILITY, params)
