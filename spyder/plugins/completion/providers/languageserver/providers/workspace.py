# -*- coding: utf-8 -*-

# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""Spyder Language Server Protocol Client workspace handler routines."""

import logging

from lsprotocol import types as lsp

from spyder.plugins.completion.providers.languageserver.providers.utils import (
    path_as_uri, process_uri, match_path_to_folder)
from spyder.plugins.completion.api import (
    CompletionRequestTypes, WorkspaceUpdateKind)
from spyder.plugins.completion.providers.languageserver.providers.document import (
    _location_to_dict, _text_edits_to_list, _range_to_dict,
)
from spyder.plugins.completion.providers.languageserver.decorators import (
    handles, send_request, send_notification)

logger = logging.getLogger(__name__)


class WorkspaceProvider:

    # ------------------------------------------------------------------
    # workspace/didChangeConfiguration
    # ------------------------------------------------------------------

    @send_notification(method=CompletionRequestTypes.WORKSPACE_CONFIGURATION_CHANGE)
    def send_configurations(self, configurations, *args):
        self.configurations = configurations
        return lsp.DidChangeConfigurationParams(
            settings=configurations,
        )

    # ------------------------------------------------------------------
    # workspace/didChangeWorkspaceFolders
    # ------------------------------------------------------------------

    @send_notification(method=CompletionRequestTypes.WORKSPACE_FOLDERS_CHANGE)
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

        ws_settings = self.server_capabilites.get('workspace', {})
        if not ws_settings.get('workspaceFolders', {}).get('supported', False):
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

    @send_notification(method=CompletionRequestTypes.WORKSPACE_WATCHED_FILES_UPDATE)
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

    @send_request(method=CompletionRequestTypes.WORKSPACE_SYMBOL)
    def send_symbol_request(self, params):
        return lsp.WorkspaceSymbolParams(query=params['query'])

    @handles(CompletionRequestTypes.WORKSPACE_SYMBOL)
    def handle_symbol_response(self, response, *args):
        """Distribute symbol results to the corresponding workspace instances."""
        if not response:
            return

        folders = list(self.watched_folders.keys())
        assigned_symbols = {folder: [] for folder in self.watched_folders}

        for sym in response:
            # response is list[SymbolInformation] | list[WorkspaceSymbol]
            if isinstance(sym, lsp.SymbolInformation):
                loc = sym.location
                path = process_uri(loc.uri)
                sym_dict = {
                    'name': sym.name,
                    'kind': sym.kind.value if sym.kind else 0,
                    'location': _location_to_dict(loc),
                    'containerName': sym.container_name,
                }
            else:  # WorkspaceSymbol
                loc = sym.location
                if isinstance(loc, lsp.Location):
                    path = process_uri(loc.uri)
                    loc_dict = _location_to_dict(loc)
                else:
                    path = process_uri(loc.uri)
                    loc_dict = {'uri': loc.uri, 'file': path}
                sym_dict = {
                    'name': sym.name,
                    'kind': sym.kind.value if sym.kind else 0,
                    'location': loc_dict,
                }

            workspace = match_path_to_folder(folders, path)
            if workspace is not None:
                assigned_symbols[workspace].append(sym_dict)

        for workspace, syms in assigned_symbols.items():
            instance = self.watched_folders[workspace]['instance']
            instance.handle_response(
                CompletionRequestTypes.WORKSPACE_SYMBOL,
                {'params': syms},
            )

    # ------------------------------------------------------------------
    # workspace/executeCommand
    # ------------------------------------------------------------------

    @send_request(method=CompletionRequestTypes.WORKSPACE_EXECUTE_COMMAND)
    def send_execute_command(self, params):
        return lsp.ExecuteCommandParams(
            command=params['command'],
            arguments=params.get('args'),
        )

    @handles(CompletionRequestTypes.WORKSPACE_EXECUTE_COMMAND)
    def handle_execute_command_response(self, response, req_id):
        if req_id in self.req_reply:
            self.req_reply[req_id](
                CompletionRequestTypes.WORKSPACE_EXECUTE_COMMAND,
                {'params': response},
            )

    # ------------------------------------------------------------------
    # workspace/applyEdit  (server -> client, routed via _sig_notification)
    # The actual response (applied=True) is sent by _SpyderPyglsClient
    # directly from the asyncio thread. Here we process the edit payload
    # and distribute it to the affected workspace instances.
    # ------------------------------------------------------------------

    @handles(CompletionRequestTypes.WORKSPACE_APPLY_EDIT)
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
                    edits = _text_edits_to_list(change.edits)
                    workspace = match_path_to_folder(folders, path)
                    if workspace is not None:
                        assigned_files[workspace].append(
                            {path: {'textDocument': {'uri': uri, 'path': path},
                                    'edits': edits}}
                        )
                elif isinstance(change, lsp.CreateFile):
                    path = process_uri(change.uri)
                    workspace = match_path_to_folder(folders, path)
                    if workspace is not None:
                        assigned_files[workspace].append(
                            {path: {'uri': change.uri, 'path': path,
                                    'kind': 'create'}}
                        )
                elif isinstance(change, lsp.RenameFile):
                    old_path = process_uri(change.old_uri)
                    new_path = process_uri(change.new_uri)
                    workspace = match_path_to_folder(folders, new_path)
                    if workspace is not None:
                        assigned_files[workspace].append(
                            {old_path: {'old_path': old_path,
                                        'new_path': new_path,
                                        'kind': 'rename'}}
                        )
                elif isinstance(change, lsp.DeleteFile):
                    path = process_uri(change.uri)
                    workspace = match_path_to_folder(folders, path)
                    if workspace is not None:
                        assigned_files[workspace].append(
                            {path: {'uri': change.uri, 'path': path,
                                    'kind': 'delete'}}
                        )
        elif edit.changes:
            for uri, text_edits in edit.changes.items():
                path = process_uri(uri)
                workspace = match_path_to_folder(folders, path)
                if workspace is not None:
                    assigned_files[workspace].append(
                        {path: _text_edits_to_list(text_edits)}
                    )

        for workspace, file_edits in assigned_files.items():
            instance = self.watched_folders[workspace]['instance']
            instance.handle_response(
                CompletionRequestTypes.WORKSPACE_APPLY_EDIT,
                {'params': {'edits': file_edits, 'language': self.language}},
            )
