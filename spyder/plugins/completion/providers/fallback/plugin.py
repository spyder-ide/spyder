# -*- coding: utf-8 -*-

# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""
Fallback completion plugin.

Wraps FallbackActor to provide compatibility with SpyderCompletionPlugin API.
"""

# Standard library imports
import logging

# Local imports
from spyder.plugins.completion.manager.api import SpyderCompletionPlugin
from spyder.plugins.completion.fallback.actor import FallbackActor


logger = logging.getLogger(__name__)


class FallbackPlugin(SpyderCompletionPlugin):
    CONF_SECTION = 'fallback-completions'
    CONF_FILE = False
    COMPLETION_CLIENT_NAME = 'fallback'

    def __init__(self, parent):
        SpyderCompletionPlugin.__init__(self, parent)
        self.fallback_actor = FallbackActor(self)
        self.fallback_actor.sig_fallback_ready.connect(
            lambda: self.sig_plugin_ready.emit(self.COMPLETION_CLIENT_NAME))
        self.fallback_actor.sig_set_tokens.connect(
            lambda _id, resp: self.sig_response_ready.emit(
                self.COMPLETION_CLIENT_NAME, _id, resp))
        self.started = False
        self.requests = {}
        self.update_configuration()

    def start_client(self, language):
        return self.started

    def start(self):
        if not self.started and self.enabled:
            self.fallback_actor.start()
            self.started = True

    def shutdown(self):
        if self.started:
            self.fallback_actor.stop()

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

    def update_configuration(self):
        self.enabled = self.get_option('enable')
        self.start()
