# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
#
'''
Tests for editor codeanalysis warnings.
'''

# Third party imports
import os
import pytest
from qtpy.QtCore import QObject, Signal, Slot

# Local imports
from spyder.config.main import CONF
from spyder.plugins.editor.widgets.codeeditor import CodeEditor
from spyder.plugins.editor.lsp.manager import LSPManager
from spyder.plugins.editor.lsp import LSPEventTypes


class LSPWrapper(QObject):
    """
    Wrapper to start the LSP services in a CodeEditor instance, once we
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


# --- Fixtures
# -----------------------------------------------------------------------------
@pytest.fixture
def build_lsp_editor(qtbot):
    """Build CodeEditor instance with LSP services."""
    # Activate pycodestyle and pydocstyle
    CONF.set('lsp-server', 'pycodestyle', True)
    CONF.set('lsp-server', 'pydocstyle', True)
    
    # Tell CodeEditor to use introspection
    os.environ['SPY_TEST_USE_INTROSPECTION'] = 'True'

    # Create an LSPManager instance to be able to start an LSP client
    lsp_manager = LSPManager(parent=None)

    # Create a CodeEditor instance
    editor = CodeEditor(parent=None)
    editor.setup_editor(language='Python')

    # Redirect editor LSP requests to lsp_manager
    editor.sig_perform_lsp_request.connect(lsp_manager.send_request)

    # Create wrapper
    lsp_wrapper = LSPWrapper(editor, lsp_manager)

    # Start LSP Python client
    lsp_manager.register_event_type(LSPEventTypes.DOCUMENT)
    with qtbot.waitSignal(lsp_wrapper.sig_lsp_services_started, timeout=30000):
        editor.filename = 'test.py'
        editor.language = 'Python'
        lsp_manager.start_client('python')
        python_client = lsp_manager.clients['python']['instance']
        python_client.sig_document_event.connect(lsp_wrapper.start_lsp_services)

    # Set the following text on editor
    text = ("def some_function():\n"  # D100, D103: Missing docstring
            "    \n"  # W293 trailing spaces
            "    a = 1 # a comment\n"  # E261 two spaces before inline comment
            "\n"
            "    a += s\n"  # Undefined variable s
            "    return a\n"
            )
    editor.set_text(text)

    # Send a textDocument/didOpen request to the server
    with qtbot.waitSignal(editor.lsp_response_signal, timeout=30000):
        editor.document_did_open()

    yield editor, lsp_manager

    # Tear down operations
    os.environ['SPY_TEST_USE_INTROSPECTION'] = 'False'
    CONF.set('lsp-server', 'pycodestyle', False)
    CONF.set('lsp-server', 'pydocstyle', False)
    lsp_manager.shutdown()


@pytest.mark.skipif(os.name == 'nt' and os.environ.get('CI') is not None,
                    reason="Times out on AppVeyor")
def test_adding_warnings(qtbot, build_lsp_editor):
    """Test that warnings are saved in the editor blocks."""
    editor, lsp_manager = build_lsp_editor

    block = editor.textCursor().block()
    line_count = editor.document().blockCount()

    warnings = []
    for i in range(line_count):
        data = block.userData()
        if data:
            for analysis in data.code_analysis:
                warnings.append((i+1, analysis[-1]))
        block = block.next()

    print(warnings)
    expected_warnings = {1: ['D100', 'D103'],
                         2: ['W293'],
                         3: ['E261'],
                         5: ['undefined name']}
    for i, warning in warnings:
        assert any([expected in warning for expected in expected_warnings[i]])


@pytest.mark.skipif(os.name == 'nt' and os.environ.get('CI') is not None,
                    reason="Times out on AppVeyor")
def test_move_warnings(qtbot, build_lsp_editor):
    """Test that moving to next/previous warnings is working."""
    editor, lsp_manager = build_lsp_editor

    # Move between warnings
    editor.go_to_next_warning()
    assert 2 == editor.get_cursor_line_number()

    editor.go_to_next_warning()
    assert 3 == editor.get_cursor_line_number()

    editor.go_to_previous_warning()
    assert 2 == editor.get_cursor_line_number()

    # Test cycling behaviour
    editor.go_to_line(5)
    editor.go_to_next_warning()
    assert 1 == editor.get_cursor_line_number()

    editor.go_to_previous_warning()
    assert 5 == editor.get_cursor_line_number()


@pytest.mark.skipif(os.name == 'nt' and os.environ.get('CI') is not None,
                    reason="Times out on AppVeyor")
def test_get_warnings(qtbot, build_lsp_editor):
    """Test that the editor is returning the right list of warnings."""
    editor, lsp_manager = build_lsp_editor

    # Get current warnings
    warnings = editor.get_current_warnings()

    expected = [['D100: Missing docstring in public module', 1],
                ['D103: Missing docstring in public function', 1],
                ['W293 blank line contains whitespace', 2],
                ['E261 at least two spaces before inline comment', 3],
                ["undefined name 's'", 5]]

    assert warnings == expected
