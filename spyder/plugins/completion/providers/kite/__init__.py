# -*- coding: utf-8 -*-

# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""Kite client requests and constants."""

from spyder.plugins.completion.api import CompletionRequestTypes


LOCALHOST = '127.0.0.1'


class _KiteEndpoints(type):
    """HTTP endpoints supported by Kite"""
    KITE_PORT = 46624
    KITE_URL = 'http://{0}:{1}'.format(LOCALHOST, KITE_PORT)

    LANGUAGES_ENDPOINT = ('GET', '/clientapi/languages')
    EVENT_ENDPOINT = ('POST', '/clientapi/editor/event')
    HOVER_ENDPOINT = (
        'GET', u'/api/buffer/spyder/{filename}/{hash}/hover?'
               'cursor_runes={cursor_runes}')
    COMPLETION_ENDPOINT = ('POST', '/clientapi/editor/complete')
    SIGNATURE_ENDPOINT = ('POST', '/clientapi/editor/signatures')
    ONBOARDING_ENDPOINT = ('GET',
                           '/clientapi/plugins/onboarding_file?editor=spyder')
    STATUS_ENDPOINT = (
        'GET', u'/clientapi/status')  # Params: filename or filetype

    def __getattribute__(self, attr):
        value = object.__getattribute__(self, attr)
        if attr.endswith('ENDPOINT'):
            verb, path = value
            url = u'{0}{1}'.format(self.KITE_URL, path)
            return verb.lower(), url
        return value


KITE_ENDPOINTS = _KiteEndpoints(
    'KiteEndpoints', (), {'__doc__': 'HTTP endpoints supported by Kite'})


KITE_REQUEST_MAPPING = {
    CompletionRequestTypes.DOCUMENT_DID_OPEN: KITE_ENDPOINTS.EVENT_ENDPOINT,
    CompletionRequestTypes.DOCUMENT_DID_CLOSE: KITE_ENDPOINTS.EVENT_ENDPOINT,
    CompletionRequestTypes.DOCUMENT_DID_CHANGE: KITE_ENDPOINTS.EVENT_ENDPOINT,
    CompletionRequestTypes.DOCUMENT_CURSOR_EVENT: KITE_ENDPOINTS.EVENT_ENDPOINT,
    CompletionRequestTypes.DOCUMENT_HOVER: KITE_ENDPOINTS.HOVER_ENDPOINT,
    CompletionRequestTypes.DOCUMENT_COMPLETION: KITE_ENDPOINTS.COMPLETION_ENDPOINT,
    CompletionRequestTypes.DOCUMENT_SIGNATURE: KITE_ENDPOINTS.SIGNATURE_ENDPOINT
}
