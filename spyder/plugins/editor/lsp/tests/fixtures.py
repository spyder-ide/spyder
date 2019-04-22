# -*- coding: utf-8 -*-

# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

import os

import pytest
from pytestqt.plugin import QtBot

from spyder.config.main import CONF
from spyder.plugins.editor.lsp import SERVER_CAPABILITES
from spyder.plugins.editor.lsp.manager import LSPManager


@pytest.fixture(scope="module")
def qtbot_module(qapp, request):
    """Module fixture for qtbot."""
    result = QtBot(request)
    return result


@pytest.fixture(scope="module")
def lsp_manager(qtbot_module):
    """Create an LSP manager instance."""
    # Activate pycodestyle and pydocstyle
    CONF.set('lsp-server', 'pycodestyle', True)
    CONF.set('lsp-server', 'pydocstyle', True)

    # Create the manager
    os.environ['SPY_TEST_USE_INTROSPECTION'] = 'True'
    manager = LSPManager(parent=None)

    with qtbot_module.waitSignal(manager.sig_initialize, timeout=30000) as blocker:
        manager.start_client('python')

    settings, language = blocker.args
    assert all([option in SERVER_CAPABILITES for option in settings.keys()])
    manager.clients[language]['server_settings'] = settings

    yield manager

    # Tear down operations
    manager.shutdown()
    os.environ['SPY_TEST_USE_INTROSPECTION'] = 'False'
    CONF.set('lsp-server', 'pycodestyle', False)
    CONF.set('lsp-server', 'pydocstyle', False)
