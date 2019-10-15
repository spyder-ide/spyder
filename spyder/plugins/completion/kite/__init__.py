# -*- coding: utf-8 -*-

# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""Kite client requests and constants."""

from spyder.plugins.completion.languageserver import LSPRequestTypes


class _KiteEndpoints(type):
    """HTTP endpoints supported by Kite"""
    KITE_PORT = 46624
    KITE_URL = 'http://localhost:{0}'.format(KITE_PORT)

    LANGUAGES_ENDPOINT = ('GET', '/clientapi/languages')
    EVENT_ENDPOINT = ('POST', '/clientapi/editor/event')
    HOVER_ENDPOINT = (
        'GET', '/api/buffer/spyder/{filename}/{hash}/hover?'
               'cursor_runes={cursor_runes}')
    COMPLETION_ENDPOINT = ('POST', '/clientapi/editor/complete')
    SIGNATURE_ENDPOINT = ('POST', '/clientapi/editor/signatures')
    FILENAME_STATUS_ENDPOINT = ('GET', '/clientapi/status?filename={filename}')
    BUFFER_STATUS_ENDPOINT = ('GET', '/clientapi/status?filetype=python')

    def __getattribute__(self, attr):
        value = object.__getattribute__(self, attr)
        if attr.endswith('ENDPOINT'):
            verb, path = value
            url = '{0}{1}'.format(self.KITE_URL, path)
            return verb.lower(), url
        return value


KITE_ENDPOINTS = _KiteEndpoints(
    'KiteEndpoints', (), {'__doc__': 'HTTP endpoints supported by Kite'})


KITE_REQUEST_MAPPING = {
    LSPRequestTypes.DOCUMENT_DID_OPEN: KITE_ENDPOINTS.EVENT_ENDPOINT,
    LSPRequestTypes.DOCUMENT_DID_CLOSE: KITE_ENDPOINTS.EVENT_ENDPOINT,
    LSPRequestTypes.DOCUMENT_DID_CHANGE: KITE_ENDPOINTS.EVENT_ENDPOINT,
    LSPRequestTypes.DOCUMENT_HOVER: KITE_ENDPOINTS.HOVER_ENDPOINT,
    LSPRequestTypes.DOCUMENT_COMPLETION: KITE_ENDPOINTS.COMPLETION_ENDPOINT,
    LSPRequestTypes.DOCUMENT_SIGNATURE: KITE_ENDPOINTS.SIGNATURE_ENDPOINT
}
