# -*- coding: utf-8 -*-

# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""Spyder Language Server Protocol Client workspace handler routines."""

import logging

from spyder.plugins.completion.providers.languageserver.providers.utils import (
    path_as_uri, process_uri, match_path_to_folder)
from spyder.plugins.completion.api import (
    CompletionRequestTypes, ClientConstants, WorkspaceUpdateKind)
from spyder.plugins.completion.providers.languageserver.decorators import (
    handles, send_request, send_response, send_notification)

logger = logging.getLogger(__name__)


class WorkspaceProvider:
    @send_notification(method=CompletionRequestTypes.WORKSPACE_CONFIGURATION_CHANGE)
    def send_configurations(self, configurations, *args):
        self.configurations = configurations
        params = {
            'settings': configurations
        }
        return params

    @send_response
    @handles(CompletionRequestTypes.WORKSPACE_FOLDERS)
    def send_workspace_folders(self, response):
        workspace_folders = []
        for folder_name in self.watched_folders:
            folder_uri = self.watched_folders[folder_name]
            workspace_folders.append({
                'uri': folder_uri,
                'name': folder_name
            })
        return workspace_folders

    @send_notification(method=CompletionRequestTypes.WORKSPACE_FOLDERS_CHANGE)
    def send_workspace_folders_change(self, params):
        folder = params['folder']
        workspace_watcher = params['instance']
        folder_uri = path_as_uri(folder)
        added_folders = []
        removed_folders = []
        if params['kind'] == WorkspaceUpdateKind.ADDITION:
            if folder not in self.watched_folders:
                self.watched_folders[folder] = {
                    'uri': folder_uri,
                    'instance': workspace_watcher
                }
                added_folders.append({
                    'uri': folder_uri,
                    'name': folder
                })
        elif params['kind'] == WorkspaceUpdateKind.DELETION:
            if folder in self.watched_folders:
                self.watched_folders.pop(folder)
                removed_folders.append({
                    'uri': folder_uri,
                    'name': folder
                })

        workspace_settings = self.server_capabilites['workspace']
        request_params = {
            'event': {
                'added': added_folders,
                'removed': removed_folders
            }
        }

        if workspace_settings['workspaceFolders']['supported']:
            logger.debug(
                u'Workspace folders change: {0} -> {1}'.format(
                    folder, params['kind'])
            )
        else:
            request_params[ClientConstants.CANCEL] = True

        return request_params

    @send_response
    @handles(CompletionRequestTypes.WORKSPACE_CONFIGURATION)
    def send_workspace_configuration(self, params):
        logger.debug(params)
        return self.configurations

    @send_notification(method=CompletionRequestTypes.WORKSPACE_WATCHED_FILES_UPDATE)
    def send_watched_files_change(self, params):
        changes = []
        entries = params.get('params', [])
        for entry in entries:
            changes.append({
                'uri': path_as_uri(entry['file']),
                'type': entry['kind']
            })
        params = {
            'changes': changes
        }
        return params

    @send_request(method=CompletionRequestTypes.WORKSPACE_SYMBOL)
    def send_symbol_request(self, params):
        params = {
            'query': params['query']
        }
        return params

    @handles(CompletionRequestTypes.WORKSPACE_SYMBOL)
    def handle_symbol_response(self, response):
        folders = list(self.watched_folders.keys())
        assigned_symbols = {folder: [] for folder in self.watched_folders}
        for symbol_info in response:
            location = symbol_info['location']
            path = process_uri(location['uri'])
            location['file'] = path
            workspace = match_path_to_folder(folders, path)
            assigned_symbols[workspace].append(symbol_info)

        for workspace in assigned_symbols:
            workspace_edits = assigned_symbols[workspace]
            workspace_instance = self.watched_folders[workspace]['instance']
            workspace_instance.handle_response(
                CompletionRequestTypes.WORKSPACE_SYMBOL,
                {'params': workspace_edits})

    @send_request(method=CompletionRequestTypes.WORKSPACE_EXECUTE_COMMAND)
    def send_execute_command(self, params):
        # It is not clear how this call is invoked
        params = {
            'command': params['command'],
            'arguments': params['args']
        }
        return params

    @send_response(method=CompletionRequestTypes.WORKSPACE_APPLY_EDIT)
    def send_edit_response(self, edits):
        params = {
            'applied': edits['applied']
        }
        if 'error' in edits:
            params['failureReason'] = edits['error']
        return params

    @handles(CompletionRequestTypes.WORKSPACE_APPLY_EDIT)
    def apply_edit(self, response):
        logger.debug("Editing: {0}".format(response['label']))
        response = response['edit']
        folders = list(self.watched_folders.keys())
        assigned_files = {folder: [] for folder in self.watched_folders}
        if 'documentChanges' in response:
            for change in response['documentChanges']:
                if 'textDocument' in change:
                    uri = change['textDocument']['uri']
                    path = process_uri(uri)
                    change['textDocument']['path'] = path
                    workspace = match_path_to_folder(folders, path)
                    assigned_files[workspace].append({path: change})
                elif 'uri' in change:
                    path = process_uri(change['uri'])
                    change['path'] = path
                    workspace = match_path_to_folder(folders, path)
                    assigned_files[workspace].append({path: change})
                elif 'oldUri' in change:
                    old_path = process_uri(change['oldUri'])
                    change['old_path'] = old_path
                    new_path = process_uri(change['newUri'])
                    change['new_path'] = new_path
                    workspace = match_path_to_folder(folders, new_path)
                    assigned_files[workspace].append({old_path: change})
        elif 'changes' in response:
            changes = response['changes']
            uris = list(changes.keys())
            for uri in uris:
                path = process_uri(uri)
                change = changes.pop(uri)
                workspace = match_path_to_folder(folders, path)
                assigned_files[workspace].append({path: change})

        for workspace in assigned_files:
            workspace_edits = assigned_files[workspace]
            workspace_instance = self.watched_folders[workspace]['instance']
            workspace_instance.handle_response(
                CompletionRequestTypes.WORKSPACE_APPLY_EDIT,
                {'params': {'edits': workspace_edits,
                            'language': self.language}})
