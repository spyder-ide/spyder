# -*- coding: utf-8 -*-

# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""Kite document requests handlers and senders."""

import logging
import hashlib

import os
import os.path as osp

from qtpy.QtCore import QMutexLocker
from spyder.plugins.completion.kite.decorators import send_request, handles
from spyder.plugins.completion.languageserver import (
    LSPRequestTypes, CompletionItemKind)


KITE_DOCUMENT_TYPES = {
    'function': CompletionItemKind.FUNCTION,
    'call': CompletionItemKind.FUNCTION,
    'module': CompletionItemKind.MODULE,
    'type': CompletionItemKind.CLASS,
    'instance': CompletionItemKind.VARIABLE,
    'descriptor': CompletionItemKind.FILE,
    'union': CompletionItemKind.VALUE,
    'global': CompletionItemKind.PROPERTY,
    'unknown': CompletionItemKind.TEXT
}

logger = logging.getLogger(__name__)


def convert_text_snippet(snippet_info):
    text = snippet_info['text']
    text_builder = []
    prev_pos = 0
    next_pos = None
    total_placeholders = len(snippet_info['placeholders'])
    for i, placeholder in enumerate(snippet_info['placeholders']):
        placeholder_begin = placeholder['begin']
        placeholder_end = placeholder['end']
        next_pos = placeholder_begin
        standard_text = text[prev_pos:next_pos]
        snippet_text = text[next_pos:placeholder_end][1:-1]
        prev_pos = placeholder['end']
        text_builder.append(standard_text)
        placeholder_number = (i + 1) % total_placeholders
        snippet = '${%d:%s}' % (placeholder_number, snippet_text)
        text_builder.append(snippet)
    text_builder.append(text[prev_pos:])
    return ''.join(text_builder)


class DocumentProvider:
    @send_request(method=LSPRequestTypes.DOCUMENT_DID_OPEN)
    def document_did_open(self, params):
        request = {
            'source': 'spyder',
            'filename': osp.realpath(params['file']),
            'text': params['text'],
            'action': 'focus',
            'selections': []
        }

        default_info = {'text': '', 'count': 0}
        with QMutexLocker(self.mutex):
            file_info = self.opened_files.get(params['file'], default_info)
            file_info['count'] += 1
            file_info['text'] = params['text']
            self.opened_files[params['file']] = file_info
        return request

    @send_request(method=LSPRequestTypes.DOCUMENT_DID_CHANGE)
    def document_did_change(self, params):
        request = {
            'source': 'spyder',
            'filename': osp.realpath(params['file']),
            'text': params['text'],
            'action': 'edit',
            'selections': []
        }
        with QMutexLocker(self.mutex):
            file_info = self.opened_files[params['file']]
            file_info['text'] = params['text']
        return request

    @send_request(method=LSPRequestTypes.DOCUMENT_COMPLETION)
    def request_document_completions(self, params):
        text = self.opened_files[params['file']]['text']
        request = {
            'filename': osp.realpath(params['file']),
            'editor': 'spyder',
            'no_snippets': not self.enable_code_snippets,
            'text': text,
            'position': {
                'begin': params['offset']
            },
            'placeholders': []
        }
        return request

    @handles(LSPRequestTypes.DOCUMENT_COMPLETION)
    def convert_completion_request(self, response):
        logger.debug(response)
        if response is None:
           return {'params': []}
        spyder_completions = []
        completions = response['completions']
        if completions is not None:
            for completion in completions:
                entry = {
                    'kind': KITE_DOCUMENT_TYPES.get(
                        completion['hint'], CompletionItemKind.TEXT),
                    'label': completion['display'],
                    'insertText': completion['snippet']['text'],
                    'filterText': completion['display'],
                    'sortText': completion['display'],
                    'documentation': completion['documentation']['text']
                }
                spyder_completions.append(entry)
                if 'children' in completion:
                    children_snippets = completion['children']
                    for children in children_snippets:
                        text = children['snippet']['text']
                        snippet = convert_text_snippet(children['snippet'])
                        child_entry = {
                            'kind': KITE_DOCUMENT_TYPES.get(
                                children['hint'], CompletionItemKind.TEXT),
                            'label': text,
                            'insertText': snippet,
                            'filterText': text,
                            'sortText': text,
                            'documentation': children['documentation']['text']
                        }
                        spyder_completions.append(child_entry)
        return {'params': spyder_completions}

    @send_request(method=LSPRequestTypes.DOCUMENT_HOVER)
    def request_hover(self, params):
        text = self.opened_files[params['file']]['text']
        md5 = hashlib.md5(text.encode('utf-8')).hexdigest()
        path = str(params['file'])
        path = path.replace(osp.sep, ':')
        logger.debug(path)
        if os.name == 'nt':
            path = path.replace('::', ':')
            path = 'windows:' + path
        request = {
            'filename': path,
            'hash': md5,
            'cursor_runes': params['offset']
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
        text = self.opened_files[request['file']]['text']
        response = {
            'editor': 'spyder',
            'filename': request['file'],
            'text': text,
            'cursor_runes': request['offset'],
            'offset_encoding': 'utf-32'
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

                signature = signatures[0]
                parameters = []
                names = []
                logger.debug(signature)
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
                    'activeParameter': arg_idx
                }
        return {'params': params}
