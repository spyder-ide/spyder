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
from qtpy.QtGui import QFont

# Local imports
from spyder.config.main import CONF
from spyder.plugins.editor.tests.conftest import (
    editor_plugin, editor_plugin_open_files, python_files)
from spyder.plugins.languageserver.tests.conftest import (
    qtbot_module, MainWindowMock)
from spyder.plugins.editor.widgets.codeeditor import CodeEditor
from spyder.plugins.editor.widgets.editor import EditorStack
from spyder.plugins.completion.plugin import CompletionPlugin
from spyder.plugins.explorer.widgets.tests.conftest import create_folders_files
from spyder.widgets.findreplace import FindReplace


def codeeditor_factory():
    editor = CodeEditor(parent=None)
    editor.setup_editor(language='Python',
                        tab_mode=False,
                        markers=True,
                        close_quotes=True,
                        close_parentheses=True,
                        color_scheme='spyder/dark',
                        font=QFont("Monospace", 10))
    editor.resize(640, 480)
    return editor


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


@pytest.fixture
def fallback_codeeditor(fallback, qtbot_module, request):
    """CodeEditor instance with Fallback enabled."""

    completions = CompletionPlugin(None, ['fallback'])
    qtbot_module.addWidget(completions)

    # Create a CodeEditor instance
    editor = codeeditor_factory()
    qtbot_module.addWidget(editor)
    editor.show()

    # Redirect editor fallback requests to FallbackActor
    editor.sig_perform_completion_request.connect(completions.send_request)
    editor.filename = 'test.py'
    editor.language = 'Python'
    editor.completions_available = True
    qtbot_module.wait(2000)

    def teardown():
        editor.hide()
        editor.completion_widget.hide()

    request.addfinalizer(teardown)
    return editor, fallback


@pytest.fixture
def lsp_codeeditor(qtbot_module, request):
    """CodeEditor instance with LSP services activated."""
    # Create a CodeEditor instance
    # Activate pycodestyle and pydocstyle
    CONF.set('lsp-server', 'pycodestyle', True)
    CONF.set('lsp-server', 'pydocstyle', True)
    CONF.set('lsp-server', 'stdio', False)

    # Create the manager
    os.environ['SPY_TEST_USE_INTROSPECTION'] = 'True'

    main = MainWindowMock()
    completions = CompletionPlugin(main, ['lsp'])
    editor = codeeditor_factory()
    qtbot_module.addWidget(editor)
    editor.show()

    # Redirect editor LSP requests to lsp_manager
    editor.sig_perform_completion_request.connect(completions.send_request)

    editor.filename = 'test.py'
    editor.language = 'Python'
    completions.register_file('python', 'test.py', editor)
    server_settings = main.editor.lsp_editor_settings['python']
    editor.start_completion_services()
    editor.update_completion_configuration(server_settings)

    with qtbot_module.waitSignal(editor.lsp_response_signal, timeout=30000):
        editor.document_did_open()

    def teardown():
        completions.shutdown()
        os.environ['SPY_TEST_USE_INTROSPECTION'] = 'False'
        CONF.set('lsp-server', 'pycodestyle', False)
        CONF.set('lsp-server', 'pydocstyle', False)

        editor.hide()
        editor.completion_widget.hide()

    request.addfinalizer(teardown)
    return editor, completions
