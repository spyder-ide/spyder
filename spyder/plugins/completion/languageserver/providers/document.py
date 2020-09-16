# -*- coding: utf-8 -*-

# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""Spyder Language Server Protocol Client document handler routines."""

# Standard library imports
import logging

# Local imports
from spyder.plugins.completion.manager.api import (
    LSPRequestTypes, InsertTextFormat, CompletionItemKind,
    ClientConstants)
from spyder.plugins.completion.languageserver.providers.utils import (
    path_as_uri, process_uri)
from spyder.plugins.completion.languageserver.decorators import (
    handles, send_request, send_notification)


LSP_COMPLETION = "LSP"

logger = logging.getLogger(__name__)


class DocumentProvider:
    def register_file(self, filename, codeeditor):
        filename = path_as_uri(filename)
        if filename not in self.watched_files:
            self.watched_files[filename] = []
        self.watched_files[filename].append(codeeditor)

    @handles(LSPRequestTypes.DOCUMENT_PUBLISH_DIAGNOSTICS)
    def process_document_diagnostics(self, response, *args):
        uri = response['uri']
        diagnostics = response['diagnostics']
        if uri in self.watched_files:
            callbacks = self.watched_files[uri]
            for callback in callbacks:
                callback.handle_response(
                    LSPRequestTypes.DOCUMENT_PUBLISH_DIAGNOSTICS,
                    {'params': diagnostics})
        else:
            logger.debug("Received diagnotics for file not open: " + uri)

    @send_notification(method=LSPRequestTypes.DOCUMENT_DID_CHANGE)
    def document_changed(self, params):
        params = {
            'textDocument': {
                'uri': path_as_uri(params['file']),
                'version': params['version']
            },
            'contentChanges': [{
                'text': params['text']
            }]
        }
        return params

    @send_notification(method=LSPRequestTypes.DOCUMENT_DID_OPEN)
    def document_open(self, editor_params):
        uri = path_as_uri(editor_params['file'])
        if uri not in self.watched_files:
            self.register_file(
                editor_params['file'], editor_params['codeeditor'])
        params = {
            'textDocument': {
                'uri': uri,
                'languageId': editor_params['language'],
                'version': editor_params['version'],
                'text': editor_params['text']
            }
        }

        return params

    @send_request(method=LSPRequestTypes.DOCUMENT_COMPLETION)
    def document_completion_request(self, params):
        params = {
            'textDocument': {
                'uri': path_as_uri(params['file'])
            },
            'position': {
                'line': params['line'],
                'character': params['column']
            }
        }

        return params

    @handles(LSPRequestTypes.DOCUMENT_COMPLETION)
    def process_document_completion(self, response, req_id):
        if isinstance(response, dict):
            response = response['items']
        if response is not None:
            for item in response:
                item['kind'] = item.get('kind', CompletionItemKind.TEXT)
                item['detail'] = item.get('detail', '')
                item['documentation'] = item.get('documentation', '')
                item['sortText'] = item.get('sortText', item['label'])
                item['filterText'] = item.get('filterText', item['label'])
                item['insertTextFormat'] = item.get(
                    'insertTextFormat', InsertTextFormat.PLAIN_TEXT)
                item['insertText'] = item.get('insertText', item['label'])
                item['provider'] = LSP_COMPLETION

        if req_id in self.req_reply:
            self.req_reply[req_id](
                LSPRequestTypes.DOCUMENT_COMPLETION, {'params': response})

    @send_request(method=LSPRequestTypes.DOCUMENT_SIGNATURE)
    def signature_help_request(self, params):
        params = {
            'textDocument': {
                'uri': path_as_uri(params['file'])
            },
            'position': {
                'line': params['line'],
                'character': params['column']
            }
        }

        return params

    @handles(LSPRequestTypes.DOCUMENT_SIGNATURE)
    def process_signature_completion(self, response, req_id):
        if len(response['signatures']) > 0:
            response['signatures'] = response['signatures'][
                response['activeSignature']]
            response['provider'] = LSP_COMPLETION
        else:
            response = None
        if req_id in self.req_reply:
            self.req_reply[req_id](
                LSPRequestTypes.DOCUMENT_SIGNATURE,
                {'params': response})

    @send_request(method=LSPRequestTypes.DOCUMENT_HOVER)
    def hover_request(self, params):
        params = {
            'textDocument': {
                'uri': path_as_uri(params['file'])
            },
            'position': {
                'line': params['line'],
                'character': params['column']
            }
        }

        return params

    @handles(LSPRequestTypes.DOCUMENT_HOVER)
    def process_hover_result(self, result, req_id):
        contents = result['contents']
        if isinstance(contents, dict):
            if 'value' in contents:
                contents = contents['value']
        elif isinstance(contents, list):
            text = []
            for entry in contents:
                if isinstance(entry, dict):
                    text.append(entry['value'])
                else:
                    text.append(entry)
            contents = '\n\n'.join(text)
        if req_id in self.req_reply:
            self.req_reply[req_id](
                LSPRequestTypes.DOCUMENT_HOVER,
                {'params': contents})

    @send_request(method=LSPRequestTypes.DOCUMENT_SYMBOL)
    def document_symbol_request(self, params):
        params = {
            'textDocument': {
                'uri': path_as_uri(params['file'])
            },
        }
        return params

    @handles(LSPRequestTypes.DOCUMENT_SYMBOL)
    def process_document_symbol_request(self, result, req_id):
        if req_id in self.req_reply:
            self.req_reply[req_id](LSPRequestTypes.DOCUMENT_SYMBOL,
                                   {'params': result})

    @send_request(method=LSPRequestTypes.DOCUMENT_DEFINITION)
    def go_to_definition_request(self, params):
        params = {
            'textDocument': {
                'uri': path_as_uri(params['file'])
            },
            'position': {
                'line': params['line'],
                'character': params['column']
            }
        }

        return params

    @handles(LSPRequestTypes.DOCUMENT_DEFINITION)
    def process_go_to_definition(self, result, req_id):
        if isinstance(result, list):
            if len(result) > 0:
                result = result[0]
                result['file'] = process_uri(result['uri'])
            else:
                result = None
        elif isinstance(result, dict):
            result['file'] = process_uri(result['uri'])
        if req_id in self.req_reply:
            self.req_reply[req_id](
                LSPRequestTypes.DOCUMENT_DEFINITION,
                {'params': result})

    @send_request(method=LSPRequestTypes.DOCUMENT_FOLDING_RANGE)
    def folding_range_request(self, params):
        params = {
            'textDocument': {
                'uri': path_as_uri(params['file'])
            }
        }
        return params

    @handles(LSPRequestTypes.DOCUMENT_FOLDING_RANGE)
    def process_folding_range(self, result, req_id):
        results = []
        for folding_range in result:
            start_line = folding_range['startLine']
            end_line = folding_range['endLine']
            results.append((start_line, end_line))
        if req_id in self.req_reply:
            self.req_reply[req_id](
                LSPRequestTypes.DOCUMENT_FOLDING_RANGE,
                {'params': results})

    @send_notification(method=LSPRequestTypes.DOCUMENT_WILL_SAVE)
    def document_will_save_notification(self, params):
        params = {
            'textDocument': {
                'uri': path_as_uri(params['file'])
            },
            'reason': params['reason']
        }
        return params

    @send_notification(method=LSPRequestTypes.DOCUMENT_DID_SAVE)
    def document_did_save_notification(self, params):
        """
        Handle the textDocument/didSave message received from an LSP server.
        """
        text = None
        if 'text' in params:
            text = params['text']
        params = {
            'textDocument': {
                'uri': path_as_uri(params['file'])
            }
        }
        if text is not None:
            params['text'] = text
        return params

    @send_notification(method=LSPRequestTypes.DOCUMENT_DID_CLOSE)
    def document_did_close(self, params):
        codeeditor = params['codeeditor']
        filename = path_as_uri(params['file'])
        params = {
            'textDocument': {
                'uri': filename
            }
        }

        if filename not in self.watched_files:
            params[ClientConstants.CANCEL] = True
        else:
            editors = self.watched_files[filename]
            if len(editors) > 1:
                params[ClientConstants.CANCEL] = True
            idx = -1
            for i, editor in enumerate(editors):
                if id(codeeditor) == id(editor):
                    idx = i
                    break
            if idx > 0:
                editors.pop(idx)

            if len(editors) == 0:
                self.watched_files.pop(filename)

        return params
