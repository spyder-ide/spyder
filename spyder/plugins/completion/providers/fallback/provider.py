# -*- coding: utf-8 -*-

# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""
Fallback completion provider.

Wraps FallbackActor to provide compatibility with SpyderCompletionProvider API.
"""

# Standard library imports
import logging

# Local imports
from spyder.config.base import _
from spyder.plugins.completion.api import SpyderCompletionProvider
from spyder.plugins.completion.providers.fallback.actor import FallbackActor


logger = logging.getLogger(__name__)


class FallbackProvider(SpyderCompletionProvider):
    COMPLETION_PROVIDER_NAME = 'fallback'
    DEFAULT_ORDER = 2

    def __init__(self, parent, config):
        SpyderCompletionProvider.__init__(self, parent, config)
        self.fallback_actor = FallbackActor(self)
        self.fallback_actor.sig_fallback_ready.connect(
            lambda: self.sig_provider_ready.emit(
                self.COMPLETION_PROVIDER_NAME))
        self.fallback_actor.sig_set_tokens.connect(
            lambda _id, resp: self.sig_response_ready.emit(
                self.COMPLETION_PROVIDER_NAME, _id, resp))
        self.started = False
        self.requests = {}

    def get_name(self):
        return _('Fallback')

    def start_completion_services_for_language(self, language):
        return self.started

    def start(self):
        if not self.started:
            self.fallback_actor.start()
            self.started = True

    def shutdown(self):
        if self.started:
            self.fallback_actor.stop()
            self.started = False

    def send_request(self, language, req_type, req, req_id=None):
        request = {
            'type': req_type,
            'file': req['file'],
            'id': req_id,
            'msg': req
        }
        req['language'] = language
        self.fallback_actor.sig_mailbox.emit(request)

    def can_close(self):
        return True
