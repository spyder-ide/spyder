# -*- coding: utf-8 -*-

# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""Custom text snippets completion plugin."""

# Standard library imports
import logging

# Local imports
from spyder.api.completion import SpyderCompletionPlugin
from spyder.plugins.completion.snippets.actor import SnippetsActor


logger = logging.getLogger(__name__)


class SnippetsPlugin(SpyderCompletionPlugin):
    CONF_SECTION = 'snippet-completions'
    CONF_FILE = False
    COMPLETION_CLIENT_NAME = 'snippets'

    def __init__(self, parent):
        SpyderCompletionPlugin.__init__(self, parent)
        self.snippets_actor = SnippetsActor(self)
