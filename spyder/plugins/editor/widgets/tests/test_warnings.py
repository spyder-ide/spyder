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
from qtpy.QtCore import Signal, QObject

# Local imports
from spyder.utils.qthelpers import qapplication
from spyder.plugins.editor.widgets.codeeditor import CodeEditor
from spyder.py3compat import to_binary_string
from spyder.utils.codeanalysis import check_with_pyflakes, check_with_pep8
from spyder.plugins.lspmanager import LSPManager
from spyder.plugins.editor.lsp import LSPEventTypes
from spyder.py3compat import PY2


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
@pytest.fixture
def construct_editor(qtbot, *args, **kwargs):
    os.environ['SPY_TEST_USE_INTROSPECTION'] = 'True'
    app = qapplication()
    lsp_manager = LSPManager(parent=None)
    editor = CodeEditor(parent=None)
    kwargs['language'] = 'Python'
    editor.setup_editor(*args, **kwargs)
    wrapper = LSPEditorWrapper(None, editor, lsp_manager)

    lsp_manager.register_plugin_type(
        LSPEventTypes.DOCUMENT, wrapper.sig_initialize)
    with qtbot.waitSignal(wrapper.sig_initialize, timeout=30000):
        editor.filename = 'test.py'
        editor.language = 'Python'
        lsp_manager.start_lsp_client('python')

    text = ("def some_function():\n"  # D100, D103: Missing docstring
            "    \n"  # W293 trailing spaces
            "    a = 1 # a comment\n"  # E261 two spaces before inline comment
            "\n"
            "    a += s\n"  # Undefined variable s
            "    return a\n"
            )
    editor.set_text(text)
    with qtbot.waitSignal(editor.lsp_response_signal, timeout=30000):
        editor.document_did_open()

    yield editor, lsp_manager
    os.environ['SPY_TEST_USE_INTROSPECTION'] = 'False'
    lsp_manager.closing_plugin()


@pytest.mark.skipif(os.name == 'nt' and os.environ.get('CI') is not None,
                    reason="Times out on AppVeyor")
def test_adding_warnings(qtbot, construct_editor):
    """Test that warning are saved in the blocks of the editor."""
    editor, lsp_manager = construct_editor

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
    expected_warnings = {# 1: ['D100', 'D103'],
                         2: ['W293'],
                         3: ['E261'], 5: ['undefined name']}
    for i, warning in warnings:
            assert any([expected in warning
                        for expected in expected_warnings[i]])
            # assert expected in warning


@pytest.mark.skipif(os.name == 'nt' and os.environ.get('CI') is not None,
                    reason="Times out on AppVeyor")
def test_move_warnings(qtbot, construct_editor):
    editor, lsp_manager = construct_editor

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
