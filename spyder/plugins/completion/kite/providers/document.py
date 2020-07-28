# -*- coding: utf-8 -*-

# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""Kite document requests handlers and senders."""

from collections import defaultdict
import logging
import hashlib

import os
import os.path as osp

from qtpy.QtCore import QMutexLocker
from spyder.plugins.completion.kite.decorators import send_request, handles
from spyder.plugins.completion.manager.api import (
    LSPRequestTypes, CompletionItemKind)


# Kite can return e.g. "int | str", so we make the default hint VALUE.
KITE_DOCUMENT_TYPES = defaultdict(lambda: CompletionItemKind.VALUE, {
    'function': CompletionItemKind.FUNCTION,
    'type': CompletionItemKind.CLASS,
    'module': CompletionItemKind.MODULE,
    'descriptor': CompletionItemKind.PROPERTY,
    'union': CompletionItemKind.VALUE,
    'unknown': CompletionItemKind.TEXT,
    'keyword': CompletionItemKind.KEYWORD,
    'call': CompletionItemKind.FUNCTION,
})

KITE_COMPLETION = 'Kite'

logger = logging.getLogger(__name__)


def convert_text_snippet(snippet_info):
    text = snippet_info['text']
    text_builder = []
    prev_pos = 0
    next_pos = None
    num_placeholders = len(snippet_info['placeholders'])
    total_placeholders = num_placeholders + 1
    for i, placeholder in enumerate(snippet_info['placeholders']):
        placeholder_begin = placeholder['begin']
        placeholder_end = placeholder['end']
        next_pos = placeholder_begin
        standard_text = text[prev_pos:next_pos]
        snippet_text = text[next_pos:placeholder_end]
        prev_pos = placeholder['end']
        text_builder.append(standard_text)
        placeholder_number = (i + 1) % total_placeholders
        if snippet_text:
            snippet = '${%d:%s}' % (placeholder_number, snippet_text)
        else:
            snippet = '$%d' % (placeholder_number)
        text_builder.append(snippet)
    text_builder.append(text[prev_pos:])
    if num_placeholders > 0:
        text_builder.append('$0')
    return ''.join(text_builder)


class DocumentProvider:

    @send_request(method=LSPRequestTypes.DOCUMENT_DID_OPEN)
    def document_did_open(self, params):
        request = {
            'source': 'spyder',
            'filename': osp.realpath(params['file']),
            'text': params['text'],
            'action': 'focus',
            'selections': [{
                'start': params['selection_start'],
                'end': params['selection_end'],
                'encoding': 'utf-16',
            }],
        }

        with QMutexLocker(self.mutex):
            self.get_status(params['file'])
            self.opened_files[params['file']] = params['text']
        return request

    @send_request(method=LSPRequestTypes.DOCUMENT_DID_CHANGE)
    def document_did_change(self, params):
        request = {
            'source': 'spyder',
            'filename': osp.realpath(params['file']),
            'text': params['text'],
            'action': 'edit',
            'selections': [{
                'start': params['selection_start'],
                'end': params['selection_end'],
                'encoding': 'utf-16',
            }],
        }
        with QMutexLocker(self.mutex):
            self.opened_files[params['file']] = params['text']
        return request

    @send_request(method=LSPRequestTypes.DOCUMENT_CURSOR_EVENT)
    def document_cursor_event(self, params):
        request = {
            'source': 'spyder',
            'filename': osp.realpath(params['file']),
            'text': params['text'],
            'action': 'edit',
            'selections': [{
                'start': params['selection_start'],
                'end': params['selection_end'],
                'encoding': 'utf-16',
            }],
        }
        return request

    @send_request(method=LSPRequestTypes.DOCUMENT_COMPLETION)
    def request_document_completions(self, params):
        text = self.opened_files[params['file']]
        request = {
            'filename': osp.realpath(params['file']),
            'editor': 'spyder',
            'no_snippets': not self.enable_code_snippets,
            'text': text,
            'position': {
                'begin': params['selection_start'],
                'end': params['selection_end'],
            },
            'offset_encoding': 'utf-16',
        }
        return request

    @handles(LSPRequestTypes.DOCUMENT_COMPLETION)
    def convert_completion_request(self, response):
        # The response schema is tested via mocking in
        # spyder/plugins/editor/widgets/tests/test_introspection.py

        logger.debug(response)
        if response is None:
            return {'params': []}
        spyder_completions = []
        completions = response['completions']
        if completions is not None:
            for i, completion in enumerate(completions):
                entry = {
                    'kind': KITE_DOCUMENT_TYPES.get(
                        completion['hint'], CompletionItemKind.TEXT),
                    'label': completion['display'],
                    'textEdit': {
                        'newText': convert_text_snippet(completion['snippet']),
                        'range': {
                            'start': completion['replace']['begin'],
                            'end': completion['replace']['end'],
                        },
                    },
                    'filterText': '',
                    # Use the returned ordering
                    'sortText': (i, 0),
                    'documentation': completion['documentation']['text'],
                    'provider': KITE_COMPLETION,
                }
                spyder_completions.append(entry)

                if 'children' in completion:
                    for j, child in enumerate(completion['children']):
                        child_entry = {
                            'kind': KITE_DOCUMENT_TYPES.get(
                                child['hint'], CompletionItemKind.TEXT),
                            'label': ' '*2 + child['display'],
                            'textEdit': {
                                'newText': convert_text_snippet(
                                    child['snippet']),
                                'range': {
                                    'start': child['replace']['begin'],
                                    'end': child['replace']['end'],
                                },
                            },
                            'insertText': convert_text_snippet(
                                child['snippet']),
                            'filterText': '',
                            # Use the returned ordering
                            'sortText': (i, j+1),
                            'documentation': child['documentation']['text'],
                            'provider': KITE_COMPLETION,
                        }
                        spyder_completions.append(child_entry)

        return {'params': spyder_completions}

    @send_request(method=LSPRequestTypes.DOCUMENT_HOVER)
    def request_hover(self, params):
        text = self.opened_files.get(params['file'], "")
        md5 = hashlib.md5(text.encode('utf-8')).hexdigest()
        path = params['file']
        path = path.replace(osp.sep, ':')
        logger.debug(path)
        if os.name == 'nt':
            path = path.replace('::', ':')
            path = ':windows:' + path
        request = {
            'filename': path,
            'hash': md5,
            'cursor_runes': params['offset'],
            'offset_encoding': 'utf-16',
        }
        return None, request

    @handles(LSPRequestTypes.DOCUMENT_HOVER)
    def process_hover(self, response):
        # logger.debug(response)
        text = None
        logger.debug(response)
        if response is not None:
            report = response['report']
            text = report['description_text']
            if len(text) == 0:
                text = None
        else:
            text = None

        return {'params': text}

    @send_request(method=LSPRequestTypes.DOCUMENT_SIGNATURE)
    def request_signature(self, request):
        text = self.opened_files.get(request['file'], "")
        response = {
            'editor': 'spyder',
            'filename': request['file'],
            'text': text,
            'cursor_runes': request['offset'],
            'offset_encoding': 'utf-16',
        }
        return response

    @handles(LSPRequestTypes.DOCUMENT_SIGNATURE)
    def process_signature(self, response):
        params = None
        if response is not None:
            calls = response['calls']
            if len(calls) > 0:
                call = calls[0]
                callee = call['callee']
                documentation = callee['synopsis']
                call_label = callee['repr']
                signatures = call['signatures']
                arg_idx = call['arg_index']

                parameters = []
                names = []

                logger.debug(signatures)
                if len(signatures) > 0:
                    signature = signatures[0]
                    logger.debug(signature)
                    if signature['args'] is not None:
                        for arg in signature['args']:
                            parameters.append({
                                'label': arg['name'],
                                'documentation': ''
                            })
                            names.append(arg['name'])

                    func_args = ', '.join(names)
                    call_label = '{0}({1})'.format(call_label, func_args)

                base_signature = {
                    'label': call_label,
                    'documentation': documentation,
                    'parameters': parameters
                }
                # doc_signatures.append(base_signature)
                params = {
                    'signatures': base_signature,
                    'activeSignature': 0,
                    'activeParameter': arg_idx,
                    'provider': KITE_COMPLETION
                }
        return {'params': params}
