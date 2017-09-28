# -*- coding: utf-8 -*-

# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""Spyder Language Server Protocol Client document handler routines."""

import os.path as osp

from spyder.py3compat import PY2
from spyder.utils.code_analysis.decorators import handles, send_request
from spyder.utils.code_analysis import (
    LSPRequestTypes, InsertTextFormat, CompletionItemKind)

if PY2:
    import pathlib2 as pathlib
else:
    import pathlib


def path_as_uri(path):
    return pathlib.Path(osp.abspath(path)).as_uri()


class DocumentProvider:
    def register_file(self, filename, signal):
        filename = path_as_uri(filename)
        if filename not in self.watched_files:
            self.watched_files[filename] = []
        self.watched_files[filename].append(signal)

    @handles(LSPRequestTypes.DOCUMENT_PUBLISH_DIAGNOSTICS)
    def process_document_diagnostics(self, response, *args):
        uri = response['uri']
        diagnostics = response['diagnostics']
        callbacks = self.watched_files[uri]
        for callback in callbacks:
            callback.emit(
                LSPRequestTypes.DOCUMENT_PUBLISH_DIAGNOSTICS,
                {'params': diagnostics})

    @send_request(
        method=LSPRequestTypes.DOCUMENT_DID_CHANGE, requires_response=False)
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

    @send_request(
        method=LSPRequestTypes.DOCUMENT_DID_OPEN, requires_response=False)
    def document_open(self, editor_params):
        params = {
            'textDocument': {
                'uri': path_as_uri(editor_params['file']),
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
        for item in response:
            item['kind'] = item.get('kind', CompletionItemKind.TEXT)
            item['detail'] = item.get('detail', '')
            item['documentation'] = item.get('documentation', '')
            item['sortText'] = item.get('sortText', item['label'])
            item['filterText'] = item.get('filterText', item['label'])
            item['insertTextFormat'] = item.get(
                'insertTextFormat', InsertTextFormat.PLAIN_TEXT)
            item['insertText'] = item.get('insertText', item['label'])

        if req_id in self.req_reply:
            self.req_reply[req_id].emit(
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
        else:
            response['signatures'] = None
        if req_id in self.req_reply:
            self.req_reply[req_id].emit(
                LSPRequestTypes.DOCUMENT_SIGNATURE,
                {'params': response['signatures']})
