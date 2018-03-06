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

# Local imports
from spyder.utils.qthelpers import qapplication
from spyder.plugins.editor.widgets.codeeditor import CodeEditor
from spyder.py3compat import to_binary_string
from spyder.utils.codeanalysis import check_with_pyflakes, check_with_pep8


# --- Fixtures
# -----------------------------------------------------------------------------
def construct_editor(*args, **kwargs):
    app = qapplication()
    editor = CodeEditor(parent=None)
    kwargs['language'] = 'Python'
    editor.setup_editor(*args, **kwargs)

    text = ("def some_function():\n"
            "    \n"  # W293 trailing spaces
            "    a = 1 # a comment\n"  # E261 two spaces before inline comment
            "\n"
            "    a += s\n"  # Undefined variable s
            "    return a\n"
            )
    editor.set_text(text)
    source_code = to_binary_string(editor.toPlainText())
    results = check_with_pyflakes(source_code) + check_with_pep8(source_code)
    editor.process_code_analysis(results)

    return editor


def test_adding_warnings():
    """Test that warning are saved in the blocks of the editor."""
    editor = construct_editor()

    block = editor.textCursor().block()
    line_count = editor.document().blockCount()

    warnings = []
    for i in range(line_count):
        data = block.userData()
        if data:
            warnings.append((i+1, data.code_analysis[0][0]))
        block = block.next()

    expected_warnings = {2: 'W293', 3: 'E261', 5: 'undefined name'}
    for i, warning in warnings:
        assert expected_warnings[i] in warning


def test_move_warnings():
    editor = construct_editor()

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
