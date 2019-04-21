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
from qtpy.QtCore import QObject, Signal, Slot
from qtpy.QtGui import QFont

# Local imports
from spyder.config.main import CONF
from spyder.plugins.editor.lsp.manager import LSPManager
from spyder.plugins.editor.widgets.codeeditor import CodeEditor
from spyder.plugins.editor.widgets.editor import EditorStack
from spyder.widgets.findreplace import FindReplace


class LSPWrapper(QObject):
    """
    Wrapper to start the LSP services in a CodeEditor instance, once
    an LSP Python client was started.
    """
    sig_lsp_services_started = Signal()

    def __init__(self, editor, lsp_manager):
        QObject.__init__(self)
        self.editor = editor
        self.lsp_manager = lsp_manager

    @Slot(dict, str)
    def start_lsp_services(self, settings, language):
        """Start LSP services in editor."""
        self.lsp_manager.register_file(
            'python', 'test.py', self.editor)
        self.editor.start_lsp_services(settings)
        self.sig_lsp_services_started.emit()


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
def lsp_codeeditor(qtbot):
    """CodeEditor instance with LSP services activated."""
    # Activate pycodestyle and pydocstyle
    CONF.set('lsp-server', 'pycodestyle', True)
    CONF.set('lsp-server', 'pydocstyle', True)

    # Tell CodeEditor to use introspection
    os.environ['SPY_TEST_USE_INTROSPECTION'] = 'True'

    # Create an LSPManager instance to be able to start an LSP client
    lsp_manager = LSPManager(parent=None)

    # Create a CodeEditor instance
    editor = CodeEditor(parent=None)
    editor.setup_editor(language='Python',
                        tab_mode=False,
                        markers=True,
                        color_scheme='spyder/dark',
                        font=QFont("Monospace", 10))
    editor.resize(640, 480)
    qtbot.addWidget(editor)
    editor.show()

    # Redirect editor LSP requests to lsp_manager
    editor.sig_perform_lsp_request.connect(lsp_manager.send_request)

    # Create wrapper
    lsp_wrapper = LSPWrapper(editor, lsp_manager)

    # Start LSP Python client
    with qtbot.waitSignal(lsp_wrapper.sig_lsp_services_started, timeout=30000):
        editor.filename = 'test.py'
        editor.language = 'Python'
        lsp_manager.start_client('python')
        python_client = lsp_manager.clients['python']['instance']
        python_client.sig_initialize.connect(lsp_wrapper.start_lsp_services)

    # Send a textDocument/didOpen request to the server
    with qtbot.waitSignal(editor.lsp_response_signal, timeout=30000):
        editor.document_did_open()

    yield editor

    # Tear down operations
    os.environ['SPY_TEST_USE_INTROSPECTION'] = 'False'
    CONF.set('lsp-server', 'pycodestyle', False)
    CONF.set('lsp-server', 'pydocstyle', False)
    lsp_manager.shutdown()
