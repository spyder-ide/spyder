# -*- coding: utf-8 -*-

# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""
Fallback completion provider.

Wraps FallbackActor to provide compatibility with SpyderCompletionProvider
API.
"""

# Standard library imports
import logging

# Local imports
from spyder.plugins.completion.api import SpyderCompletionProvider
from spyder.plugins.fallback.actor import FallbackActor

# Logging
logger = logging.getLogger(__name__)


class FallbackProvider(SpyderCompletionProvider):
    NAME = 'fallback'

    def __init__(self, parent):
        super().__init__(parent)

        self.enabled = True
        self.started = False
        self.requests = {}
        self.fallback_actor = FallbackActor(self)

        # Signals
        self.fallback_actor.sig_fallback_ready.connect(
            lambda: self.sig_provider_ready.emit(self.NAME))
        self.fallback_actor.sig_set_tokens.connect(
            lambda _id, resp: self.sig_response_ready.emit(
                self.NAME, _id, resp))

    # --- SpyderCompletionProvider API
    # ------------------------------------------------------------------------
    def start(self):
        if not self.started and self.enabled:
            self.fallback_actor.start()
            self.started = True

    def shutdown(self):
        if self.started:
            self.fallback_actor.stop()

    def start_client(self, language):
        return self.started

    def stop_client(self, language):
        pass

    def send_request(self, language, req_type, req, req_id=None):
        if not self.enabled:
            return

        request = {
            'type': req_type,
            'file': req['file'],
            'id': req_id,
            'msg': req
        }
        req['language'] = language
        self.fallback_actor.sig_mailbox.emit(request)

    def register_file(self, language, filename, codeeditor):
        pass

    def update_configuration(self, options=None):
        if options:
            self.enabled = options.get('enabled', True)
