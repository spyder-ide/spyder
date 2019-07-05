# -*- coding: utf-8 -*-

# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""Kite client requests and constants."""

from spyder.plugins.languageserver import LSPRequestTypes


class _KiteEndpoints:
    """HTTP endpoints supported by Kite"""
    KITE_PORT = 46624
    KITE_URL = 'http://localhost:{0}'.format(KITE_PORT)

    ALIVE_ENDPOINT = ('GET', '/clientapi/ping')
    LANGUAGES_ENDPOINT = ('GET', '/clientapi/languages')
    EVENT_ENDPOINT = ('POST', '/clientapi/editor/event')
    HOVER_ENDPOINT = (
        'GET', '/api/buffer/spyder/{filename}/{hash}/hover?'
               'cursor_runes={cursor_bytes}&offset_encoding={encoding}')
    COMPLETION_ENDPOINT = ('POST', '/clientapi/editor/completions')
    SIGNATURE_ENDPOINT = ('POST', '/clientapi/editor/signatures')

    def __getattr__(self, attr):
        value = super().__getattr__(self, attr)
        if attr.endswith('ENDPOINT'):
            verb, path = value
            url = '{0}{1}'.format(self.KITE_URL, path)
            return verb.lower(), url
        return value


KITE_ENDPOINTS = _KiteEndpoints()


KITE_REQUEST_MAPPING = {
    LSPRequestTypes.DOCUMENT_DID_OPEN: KITE_ENDPOINTS.EVENT_ENDPOINT,
    LSPRequestTypes.DOCUMENT_DID_CLOSE: KITE_ENDPOINTS.EVENT_ENDPOINT,
    LSPRequestTypes.DOCUMENT_DID_CHANGE: KITE_ENDPOINTS.EVENT_ENDPOINT,
    LSPRequestTypes.DOCUMENT_HOVER: KITE_ENDPOINTS.HOVER_ENDPOINT,
    # FIXME: Ask Kite team about completions endpoint
    LSPRequestTypes.DOCUMENT_COMPLETION: KITE_ENDPOINTS.COMPLETION_ENDPOINT,
    LSPRequestTypes.DOCUMENT_SIGNATURE: KITE_ENDPOINTS.SIGNATURE_ENDPOINT
}
