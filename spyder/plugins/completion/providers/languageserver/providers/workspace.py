# -*- coding: utf-8 -*-

# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""Spyder Language Server Protocol Client workspace handler routines."""
from __future__ import annotations
import logging
import typing

from lsprotocol import types as lsp

from spyder.plugins.completion.providers.languageserver.providers.utils import (
    path_as_uri, process_uri, match_path_to_folder)
from spyder.plugins.completion.api import WorkspaceUpdateKind
from spyder.plugins.completion.providers.languageserver.decorators import (
    handles, send_request, send_notification)

if typing.TYPE_CHECKING:
    from spyder.plugins.editor.widgets.codeeditor.lsp_mixin import LSPMixin

class WatchedFolder(typing.TypedDict):
    uri: str
    instance: LSPMixin


logger = logging.getLogger(__name__)


class WorkspaceProvider:

    watched_folders: dict[str, WatchedFolder]
    server_capabilites: lsp.ServerCapabilities | None
    language: str
    req_reply: dict[int, typing.Callable]

    # ------------------------------------------------------------------
    # workspace/didChangeConfiguration
    # ------------------------------------------------------------------

    @send_notification(method=lsp.WORKSPACE_DID_CHANGE_CONFIGURATION)
    def send_configurations(self, configurations, *args):
        self.configurations = configurations
        return lsp.DidChangeConfigurationParams(
            settings=configurations,
        )

    # ------------------------------------------------------------------
    # workspace/didChangeWorkspaceFolders
    # ------------------------------------------------------------------

    @send_notification(method=lsp.WORKSPACE_DID_CHANGE_WORKSPACE_FOLDERS)
    def send_workspace_folders_change(self, params):
        folder = params['folder']
        workspace_watcher = params['instance']
        folder_uri = path_as_uri(folder)
        added: list[lsp.WorkspaceFolder] = []
        removed: list[lsp.WorkspaceFolder] = []

        if params['kind'] == WorkspaceUpdateKind.ADDITION:
            if folder not in self.watched_folders:
                self.watched_folders[folder] = {
                    'uri': folder_uri,
                    'instance': workspace_watcher,
                }
                added.append(lsp.WorkspaceFolder(uri=folder_uri, name=folder))
        elif params['kind'] == WorkspaceUpdateKind.DELETION:
            if folder in self.watched_folders:
                self.watched_folders.pop(folder)
                removed.append(lsp.WorkspaceFolder(uri=folder_uri, name=folder))

        ws = self.server_capabilites.workspace if self.server_capabilites else None
        wf = ws.workspace_folders if ws else None
        if not (wf and wf.supported):
            return None  # Server doesn't support workspace folders, cancel.

        logger.debug('Workspace folders change: %s -> %s', folder, params['kind'])
        return lsp.DidChangeWorkspaceFoldersParams(
            event=lsp.WorkspaceFoldersChangeEvent(
                added=added,
                removed=removed,
            ),
        )

    # ------------------------------------------------------------------
    # workspace/didChangeWatchedFiles
    # ------------------------------------------------------------------

    @send_notification(method=lsp.WORKSPACE_DID_CHANGE_WATCHED_FILES)
    def send_watched_files_change(self, params):
        changes = [
            lsp.FileEvent(
                uri=path_as_uri(entry['file']),
                type=lsp.FileChangeType(entry['kind']),
            )
            for entry in params.get('params', [])
        ]
        return lsp.DidChangeWatchedFilesParams(changes=changes)

    # ------------------------------------------------------------------
    # workspace/symbol
    # ------------------------------------------------------------------

    @send_request(method=lsp.WORKSPACE_SYMBOL)
    def send_symbol_request(self, params):
        return lsp.WorkspaceSymbolParams(query=params['query'])

    @handles(lsp.WORKSPACE_SYMBOL)
    def handle_symbol_response(self, response, *args):
        """Distribute symbol results to the corresponding workspace instances."""
        if not response:
            return

        folders = list(self.watched_folders.keys())
        assigned_symbols = {folder: [] for folder in self.watched_folders}

        for sym in response:
            # response is list[SymbolInformation] | list[WorkspaceSymbol]
            if isinstance(sym, lsp.SymbolInformation):
                path = process_uri(sym.location.uri)
            else:  # WorkspaceSymbol
                path = process_uri(sym.location.uri)

            workspace = match_path_to_folder(folders, path)
            if workspace is not None:
                assigned_symbols[workspace].append(sym)

        for workspace, syms in assigned_symbols.items():
            instance = self.watched_folders[workspace]['instance']
            instance.handle_response(
                lsp.WORKSPACE_SYMBOL,
                syms,
            )

    # ------------------------------------------------------------------
    # workspace/executeCommand
    # ------------------------------------------------------------------

    @send_request(method=lsp.WORKSPACE_EXECUTE_COMMAND)
    def send_execute_command(self, params):
        return lsp.ExecuteCommandParams(
            command=params['command'],
            arguments=params.get('args'),
        )

    @handles(lsp.WORKSPACE_EXECUTE_COMMAND)
    def handle_execute_command_response(self, response, req_id):
        if req_id in self.req_reply:
            self.req_reply[req_id](
                lsp.WORKSPACE_EXECUTE_COMMAND,
                response,
            )

    @handles(lsp.WORKSPACE_APPLY_EDIT)
    def apply_edit(self, params: lsp.ApplyWorkspaceEditParams) -> None:
        logger.debug('Applying edit: %s', params.label)
        edit = params.edit
        folders = list(self.watched_folders.keys())
        assigned_files = {folder: [] for folder in self.watched_folders}

        if edit.document_changes:
            for change in edit.document_changes:
                if isinstance(change, lsp.TextDocumentEdit):
                    uri = change.text_document.uri
                    path = process_uri(uri)
                    workspace = match_path_to_folder(folders, path)
                    if workspace is not None:
                        assigned_files[workspace].append(change)
                elif isinstance(change, (lsp.CreateFile, lsp.RenameFile, lsp.DeleteFile)):
                    ref_uri = change.new_uri if isinstance(change, lsp.RenameFile) else change.uri
                    path = process_uri(ref_uri)
                    workspace = match_path_to_folder(folders, path)
                    if workspace is not None:
                        assigned_files[workspace].append(change)
        elif edit.changes:
            for uri, text_edits in edit.changes.items():
                path = process_uri(uri)
                workspace = match_path_to_folder(folders, path)
                if workspace is not None:
                    assigned_files[workspace].append(
                        lsp.TextDocumentEdit(
                            text_document=lsp.OptionalVersionedTextDocumentIdentifier(uri=uri),
                            edits=text_edits,
                        )
                    )

        for workspace, file_edits in assigned_files.items():
            instance = self.watched_folders[workspace]['instance']
            instance.handle_response(
                lsp.WORKSPACE_APPLY_EDIT,
                {'edits': file_edits, 'language': self.language},
            )
