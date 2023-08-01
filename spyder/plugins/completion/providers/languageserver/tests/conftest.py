# -*- coding: utf-8 -*-

# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

import os
from unittest.mock import Mock, MagicMock

from qtpy.QtCore import QObject, Signal, Slot
from qtpy.QtWidgets import QWidget
import pytest
from pytestqt.qtbot import QtBot

from spyder.config.manager import CONF
from spyder.plugins.completion.api import SERVER_CAPABILITES
from spyder.plugins.completion.tests.conftest import qtbot_module
from spyder.plugins.completion.providers.languageserver.provider import (
    LanguageServerProvider)


class CompletionPluginMock(QObject, MagicMock):
    """Mock for the completion plugin."""
    CONF_SECTION = 'completions'

    def __init__(self, conf):
        super().__init__()
        self.conf = conf

    def get_conf(self, option, default=None, section=None):
        if section == 'completions':
            option = option[-1]
            return self.conf.get(option, default)
        else:
            return CONF.get(section, option, default)


def lsp_context(is_stdio):
    @pytest.fixture(scope='module')
    def wrapper(qtbot_module, request):
        # Activate pycodestyle and pydocstyle
        conf = dict(LanguageServerProvider.CONF_DEFAULTS)
        conf['pycodestyle'] = True
        conf['pydocstyle'] = True
        conf['stdio'] = is_stdio

        # Create the manager
        os.environ['SPY_TEST_USE_INTROSPECTION'] = 'True'
        provider = LanguageServerProvider(CompletionPluginMock(conf), conf)

        # Wait for the client to be started
        with qtbot_module.waitSignal(
                provider.sig_language_completions_available,
                timeout=30000) as block:
            provider.start_completion_services_for_language('python')

        capabilities, _ = block.args
        assert all(
            [option in SERVER_CAPABILITES for option in capabilities.keys()])

        def teardown():
            provider.shutdown()
            os.environ['SPY_TEST_USE_INTROSPECTION'] = 'False'

        request.addfinalizer(teardown)
        return provider
    return wrapper


lsp_provider = lsp_context(is_stdio=False)
lsp_stdio_provider = lsp_context(is_stdio=True)
