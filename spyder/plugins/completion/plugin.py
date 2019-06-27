
# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""
Backend plugin to manage multiple code completion and introspection clients.
"""

# Standard library imports
import logging
import os
import os.path as osp

# Third-party imports
from qtpy.QtCore import QObject, Slot

# Local imports
from spyder.config.base import get_conf_path, running_under_pytest
from spyder.config.lsp import PYTHON_CONFIG
from spyder.config.main import CONF
from spyder.api.completion import SpyderCompletionPlugin
from spyder.utils.misc import select_port, getcwd_or_home
from spyder.plugins.languageserver.plugin import LanguageServerPlugin
# from spyder.plugins.languageserver.client import LSPClient
# from spyder.plugins.languageserver.confpage import LanguageServerConfigPage


logger = logging.getLogger(__name__)


class CompletionPlugin(SpyderCompletionPlugin):
    def __init__(self, parent):
        QObject.__init__(self, parent)
        SpyderPlugin.__init__(self, parent)
        self.main = parent
        self.clients = {}
