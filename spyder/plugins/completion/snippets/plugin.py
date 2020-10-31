# -*- coding: utf-8 -*-

# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""Custom text snippets completion plugin."""

# Standard library imports
import bisect
import logging

# Local imports
from spyder.api.completion import SpyderCompletionPlugin
from spyder.plugins.completion.languageserver import LSP_LANGUAGES
from spyder.plugins.completion.snippets.actor import SnippetsActor

PYTHON_POS = bisect.bisect_left(LSP_LANGUAGES, 'Python')
LSP_LANGUAGES_PY = list(LSP_LANGUAGES)
LSP_LANGUAGES_PY.insert(PYTHON_POS, 'Python')
LSP_LANGUAGES_PY = {x.lower() for x in LSP_LANGUAGES_PY}

logger = logging.getLogger(__name__)


class SnippetsPlugin(SpyderCompletionPlugin):
    CONF_SECTION = 'snippet-completions'
    CONF_FILE = False
    COMPLETION_CLIENT_NAME = 'snippets'

    def __init__(self, parent):
        SpyderCompletionPlugin.__init__(self, parent)
        self.snippets_actor = SnippetsActor(self)
        self.snippets_actor.sig_snippets_ready.connect(
            lambda: self.sig_plugin_ready.emit(self.COMPLETION_CLIENT_NAME))
        self.snippets_actor.sig_snippets_response.connect(
            lambda _id, resp: self.sig_response_ready.emit(
                self.COMPLETION_CLIENT_NAME, _id, resp))
        self.started = False
        self.requests = {}
        self.update_configuration()

    def start_client(self, language):
        return self.started

    def start(self):
        if not self.started and self.enabled:
            self.snippets_actor.start()
            self.started = True

    def shutdown(self):
        if self.started:
            self.snippets_actor.stop()

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
        self.snippets_actor.sig_mailbox.emit(request)

    def update_configuration(self):
        self.enabled = self.get_option('enable')
        snippet_info = {}
        for language in LSP_LANGUAGES_PY:
            snippet_info[language] = self.get_option(language, {})
        self.snippets_actor.sig_update_snippets.emit(snippet_info)
