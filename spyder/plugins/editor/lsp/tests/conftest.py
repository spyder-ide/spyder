# -*- coding: utf-8 -*-

# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

import os
try:
    from unittest.mock import Mock
except ImportError:
    from mock import Mock # Python 2

from qtpy.QtCore import QObject, Signal, Slot
import pytest
from pytestqt.plugin import QtBot

from spyder.config.main import CONF
from spyder.plugins.editor.lsp import SERVER_CAPABILITES
from spyder.plugins.editor.lsp.manager import LSPManager


class EditorMock(QObject):
    """
    Mock for the Editor plugin with the interface needed by LSPManager.
    """
    sig_lsp_initialized = Signal()

    def __init__(self):
        QObject.__init__(self)
        self.lsp_editor_settings = {}

    @Slot(dict, str)
    def register_lsp_server_settings(self, settings, language):
        self.lsp_editor_settings[language] = settings
        self.sig_lsp_initialized.emit()


class MainWindowMock(QObject):
    """Mock for the Main Window."""
    def __init__(self):
        QObject.__init__(self)
        self.editor = EditorMock()

    def __getattr__(self, attr):
        if attr == 'editor':
            return self.editor
        elif attr == 'projects':
            # TODO: Add tests for project switching
            return None
        else:
            return Mock()


@pytest.fixture(scope="module")
def qtbot_module(qapp, request):
    """Module fixture for qtbot."""
    result = QtBot(request)
    return result


def lsp_context(is_stdio):
    @pytest.fixture(scope='module')
    def wrapper(qtbot_module, request):
        # Activate pycodestyle and pydocstyle
        CONF.set('lsp-server', 'pycodestyle', True)
        CONF.set('lsp-server', 'pydocstyle', True)
        CONF.set('lsp-server', 'stdio', is_stdio)

        # Create the manager
        os.environ['SPY_TEST_USE_INTROSPECTION'] = 'True'
        manager = LSPManager(parent=MainWindowMock())
        # Wait for the client to be started
        editor = manager.main.editor
        with qtbot_module.waitSignal(
                editor.sig_lsp_initialized, timeout=30000):
            manager.start_client('python')

        settings = editor.lsp_editor_settings['python']
        assert all(
            [option in SERVER_CAPABILITES for option in settings.keys()])

        def teardown():
            manager.shutdown()

            os.environ['SPY_TEST_USE_INTROSPECTION'] = 'False'
            CONF.set('lsp-server', 'pycodestyle', False)
            CONF.set('lsp-server', 'pydocstyle', False)

        request.addfinalizer(teardown)
        return manager
    return wrapper


lsp_manager = lsp_context(is_stdio=False)
lsp_stdio_manager = lsp_context(is_stdio=True)
