# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""pygls client routing server-initiated messages to the connection."""

from __future__ import annotations

# Standard library imports
from collections.abc import Callable
from typing import Any, Optional, TYPE_CHECKING, Union

# Third party imports
from lsprotocol import types as lsp
from pygls.client import JsonRPCClient
from pygls.protocol import LanguageServerProtocol, default_converter

# Local imports
from spyder.plugins.languageservices.api.symbols import SpyderSymbolKind

if TYPE_CHECKING:
    from spyder.plugins.languageservices.providers.lsp.connection import (
        LanguageServerConnection,
    )


def spyder_converter():
    """cattrs converter of pygls extended for Spyder's needs.

    Adds a structure hook for ``Optional[Union[str, NotebookDocumentFilter*]]``
    (``NotebookDocumentFilterWithCells.notebook`` in lsprotocol 2025.0.0 has
    no hook for the Optional variant, which breaks structuring pylsp's
    ``notebookDocumentSync`` capabilities) and accepts Spyder's extended
    symbol kinds (cells, block comments) in ``SymbolKind`` fields.
    """
    converter = default_converter()

    notebook_filter = Optional[
        Union[
            str,
            lsp.NotebookDocumentFilterNotebookType,
            lsp.NotebookDocumentFilterScheme,
            lsp.NotebookDocumentFilterPattern,
        ]
    ]

    def structure_notebook_filter(obj, _):
        if obj is None or isinstance(obj, str):
            return obj
        if "notebookType" in obj:
            return converter.structure(
                obj, lsp.NotebookDocumentFilterNotebookType
            )
        if "scheme" in obj:
            return converter.structure(obj, lsp.NotebookDocumentFilterScheme)
        return converter.structure(obj, lsp.NotebookDocumentFilterPattern)

    converter.register_structure_hook(
        notebook_filter, structure_notebook_filter
    )

    def structure_symbol_kind(obj, _):
        try:
            return lsp.SymbolKind(obj)
        except ValueError:
            return SpyderSymbolKind(obj)

    converter.register_structure_hook(lsp.SymbolKind, structure_symbol_kind)
    return converter


class SpyderPyglsClient(JsonRPCClient):
    """pygls client forwarding server messages to
    :class:`LanguageServerConnection`."""

    def __init__(
        self,
        connection: LanguageServerConnection,
        name: str,
        version: str = "0.1.0",
    ):
        self.name = name
        self.version = version
        super().__init__(
            protocol_cls=LanguageServerProtocol,
            converter_factory=spyder_converter,
        )
        self._connection = connection
        self._register_server_handlers()

    def _register_server_handlers(self) -> None:
        connection = self._connection

        def notification(method: str) -> Callable[[Any], None]:
            def handler(params: Any) -> None:
                connection.on_server_notification(method, params)

            return handler

        for method in (
            lsp.TEXT_DOCUMENT_PUBLISH_DIAGNOSTICS,
            lsp.WINDOW_SHOW_MESSAGE,
            lsp.WINDOW_LOG_MESSAGE,
        ):
            self.feature(method)(notification(method))

        @self.feature(lsp.WORKSPACE_WORKSPACE_FOLDERS)
        def on_workspace_folders(params: None) -> list[lsp.WorkspaceFolder]:
            return list(connection.workspace_folders.values())

        @self.feature(lsp.WORKSPACE_CONFIGURATION)
        def on_workspace_configuration(params: lsp.ConfigurationParams) -> list:
            return [connection.configurations] * len(params.items)

        @self.feature(lsp.WORKSPACE_APPLY_EDIT)
        def on_apply_edit(
            params: lsp.ApplyWorkspaceEditParams,
        ) -> lsp.ApplyWorkspaceEditResult:
            connection.on_server_notification(lsp.WORKSPACE_APPLY_EDIT, params)
            return lsp.ApplyWorkspaceEditResult(applied=True)

        @self.feature(lsp.CLIENT_REGISTER_CAPABILITY)
        def on_register_capability(params: lsp.RegistrationParams) -> None:
            connection.on_register_capability(params)

        @self.feature(lsp.CLIENT_UNREGISTER_CAPABILITY)
        def on_unregister_capability(params: lsp.UnregistrationParams) -> None:
            connection.on_unregister_capability(params)
