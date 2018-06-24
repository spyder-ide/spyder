# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
#
'''
Tests for editor codeanalysis warnings.
'''

# Third party imports
import pytest
from qtpy.QtCore import Signal, QObject

# Local imports
from spyder.utils.qthelpers import qapplication
from spyder.widgets.sourcecode.codeeditor import CodeEditor
from spyder.py3compat import to_binary_string
from spyder.utils.codeanalysis import check_with_pyflakes, check_with_pep8
from spyder.plugins.lspmanager import LSPManager
from spyder.utils.code_analysis import LSPEventTypes


class LSPEditorWrapper(QObject):
    sig_initialize = Signal(dict, str)

    def __init__(self, parent, editor, lsp_manager):
        QObject.__init__(self, parent)
        self.editor = editor
        self.lsp_manager = lsp_manager
        self.editor.sig_perform_lsp_request.connect(self.perform_request)
        self.sig_initialize.connect(self.initialize_callback)

    def initialize_callback(self, settings, language):
        self.lsp_manager.register_file(
            'python', 'test.py', self.editor.lsp_response_signal)
        self.editor.start_lsp_services(settings)

    def perform_request(self, language, request, params):
        self.lsp_manager.send_request(language, request, params)

# --- Fixtures
# -----------------------------------------------------------------------------
def construct_editor(qtbot, *args, **kwargs):
    app = qapplication()
    lsp_manager = LSPManager(parent=None)
    editor = CodeEditor(parent=None)
    kwargs['language'] = 'Python'
    editor.setup_editor(*args, **kwargs)
    print("Ah?")
    wrapper = LSPEditorWrapper(None, editor, lsp_manager)

    lsp_manager.register_plugin_type(
        LSPEventTypes.DOCUMENT, wrapper.sig_initialize)
    with qtbot.waitSignal(wrapper.sig_initialize, timeout=30000):
        editor.filename = 'test.py'
        editor.language = 'Python'
        lsp_manager.start_lsp_client('python')

    text = ("def some_function():\n"
            "    \n"  # W293 trailing spaces
            "    a = 1 # a comment\n"  # E261 two spaces before inline comment
            "\n"
            "    a += s\n"  # Undefined variable s
            "    return a\n"
            )
    editor.set_text(text)
    with qtbot.waitSignal(editor.lsp_response_signal, timeout=30000):
        editor.document_did_open()

    return editor, lsp_manager


def test_adding_warnings(qtbot):
    """Test that warning are saved in the blocks of the editor."""
    editor, lsp_manager = construct_editor(qtbot)

    block = editor.textCursor().block()
    line_count = editor.document().blockCount()

    warnings = []
    for i in range(line_count):
        data = block.userData()
        if data:
            print(data.code_analysis)
            warnings.append((i+1, data.code_analysis[0][-1]))
        block = block.next()

    expected_warnings = {2: 'W293', 3: 'E261', 5: 'undefined name'}
    for i, warning in warnings:
        assert expected_warnings[i] in warning
    lsp_manager.close_client('python')


def test_move_warnings(qtbot):
    editor, lsp_manager = construct_editor(qtbot)

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
    assert 2 == editor.get_cursor_line_number()

    editor.go_to_previous_warning()
    assert 5 == editor.get_cursor_line_number()
    lsp_manager.close_client('python')
