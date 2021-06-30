# -*- coding: utf-8 -*-

# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""Custom text snippets completion plugin."""

# Standard library imports
import os
import bisect
import logging

# Local imports
from spyder.api.config.decorators import on_conf_change
from spyder.config.base import _, running_under_pytest
from spyder.config.snippets import SNIPPETS
from spyder.plugins.completion.api import (SpyderCompletionProvider,
                                           SUPPORTED_LANGUAGES)
from spyder.plugins.completion.providers.snippets.actor import SnippetsActor
from spyder.plugins.completion.providers.snippets.conftabs import (
    SnippetsConfigTab
)

PYTHON_POS = bisect.bisect_left(SUPPORTED_LANGUAGES, 'Python')
SUPPORTED_LANGUAGES_PY = list(SUPPORTED_LANGUAGES)
SUPPORTED_LANGUAGES_PY.insert(PYTHON_POS, 'Python')
SUPPORTED_LANGUAGES_PY = {x.lower() for x in SUPPORTED_LANGUAGES_PY}

logger = logging.getLogger(__name__)


class SnippetsProvider(SpyderCompletionProvider):
    COMPLETION_PROVIDER_NAME = 'snippets'
    DEFAULT_ORDER = 3
    CONF_DEFAULTS = [(lang, SNIPPETS[lang]) for lang in SNIPPETS]
    CONF_VERSION = "0.1.0"
    CONF_TABS = [SnippetsConfigTab]

    def __init__(self, parent, config):
        SpyderCompletionProvider.__init__(self, parent, config)
        self.snippets_actor = SnippetsActor(self)
        self.snippets_actor.sig_snippets_ready.connect(
            self.signal_provider_ready)
        self.snippets_actor.sig_snippets_response.connect(
            lambda _id, resp: self.sig_response_ready.emit(
                self.COMPLETION_PROVIDER_NAME, _id, resp))
        self.started = False
        self.requests = {}
        self.config = config

    def get_name(self):
        return _('Text snippets')

    def start_completion_services_for_language(self, language):
        return self.started

    def start(self):
        if not self.started:
            self.snippets_actor.start()
            self.started = True

    def signal_provider_ready(self):
        self.update_snippets(self.config)
        self.sig_provider_ready.emit(self.COMPLETION_PROVIDER_NAME)

    def shutdown(self):
        if self.started:
            self.snippets_actor.stop()
            self.started = False

    def send_request(self, language, req_type, req, req_id=None):
        request = {
            'type': req_type,
            'file': req['file'],
            'id': req_id,
            'msg': req
        }
        req['language'] = language
        self.snippets_actor.sig_mailbox.emit(request)

    @on_conf_change
    def update_snippets(self, snippets):
        if running_under_pytest():
            if not os.environ.get('SPY_TEST_USE_INTROSPECTION'):
                return

        self.config = snippets
        snippet_info = {}
        for language in SUPPORTED_LANGUAGES_PY:
            snippet_info[language] = snippets.get(language, {})
        self.snippets_actor.sig_update_snippets.emit(snippet_info)
