# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
#

"""
Testing utilities to be used with pytest.
"""

# Stdlib imports
import os
try:
    from unittest.mock import Mock
except ImportError:
    from mock import Mock # Python 2

# Third party imports
import pytest
from pytestqt.plugin import QtBot
from qtpy.QtGui import QFont

# Local imports
from spyder.config.main import CONF
from spyder.plugins.editor.lsp.manager import LSPManager
from spyder.plugins.editor.widgets.codeeditor import CodeEditor
from spyder.plugins.editor.widgets.editor import EditorStack
from spyder.widgets.findreplace import FindReplace


@pytest.fixture
def setup_editor(qtbot):
    """
    Set up EditorStack with CodeEditor containing some Python code.
    The cursor is at the empty line below the code.
    Returns tuple with EditorStack and CodeEditor.
    """
    text = ('a = 1\n'
            'print(a)\n'
            '\n'
            'x = 2')  # a newline is added at end
    editorStack = EditorStack(None, [])
    editorStack.set_find_widget(FindReplace(editorStack))
    editorStack.set_io_actions(Mock(), Mock(), Mock(), Mock())
    finfo = editorStack.new('foo.py', 'utf-8', text)
    qtbot.addWidget(editorStack)
    return editorStack, finfo.editor


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
    manager.clients[language]['server_settings'] = settings

    yield manager

    # Tear down operations
    manager.shutdown()
    os.environ['SPY_TEST_USE_INTROSPECTION'] = 'False'
    CONF.set('lsp-server', 'pycodestyle', False)
    CONF.set('lsp-server', 'pydocstyle', False)


@pytest.fixture
def lsp_codeeditor(lsp_manager, qtbot_module):
    """CodeEditor instance with LSP services activated."""
    # Create a CodeEditor instance
    editor = CodeEditor(parent=None)
    editor.setup_editor(language='Python',
                        tab_mode=False,
                        markers=True,
                        color_scheme='spyder/dark',
                        font=QFont("Monospace", 10))
    editor.resize(640, 480)
    qtbot_module.addWidget(editor)
    editor.show()

    # Redirect editor LSP requests to lsp_manager
    editor.sig_perform_lsp_request.connect(lsp_manager.send_request)

    editor.filename = 'test.py'
    editor.language = 'Python'
    lsp_manager.register_file('python', 'test.py', editor)
    editor.start_lsp_services(lsp_manager.clients['python']['server_settings'])

    with qtbot_module.waitSignal(editor.lsp_response_signal, timeout=30000):
        editor.document_did_open()

    yield editor

    # Teardown operations
    editor.hide()
    editor.completion_widget.hide()
