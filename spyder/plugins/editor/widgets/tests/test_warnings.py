# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
#

"""Tests for editor codeanalysis warnings."""

# Stdlib imports
import os

# Third party imports
import pytest

# Local imports
from spyder.plugins.editor.widgets.tests.fixtures import (lsp_codeeditor,
    lsp_manager, qtbot_module)


TEXT = ("def some_function():\n"  # D100, D103: Missing docstring
        "    \n"  # W293 trailing spaces
        "    a = 1 # a comment\n"  # E261 two spaces before inline comment
        "\n"
        "    a += s\n"  # Undefined variable s
        "    return a\n")


@pytest.mark.slow
@pytest.mark.first
def test_adding_warnings(qtbot, lsp_codeeditor):
    """Test that warnings are saved in the editor blocks."""
    editor = lsp_codeeditor

    # Set text in editor
    editor.set_text(TEXT)

    # Notify changes
    with qtbot.waitSignal(editor.lsp_response_signal, timeout=30000):
        editor.document_did_change()

    block = editor.textCursor().block()
    line_count = editor.document().blockCount()

    warnings = []
    for i in range(line_count):
        data = block.userData()
        if data:
            for analysis in data.code_analysis:
                warnings.append((i+1, analysis[-1]))
        block = block.next()

    expected_warnings = {1: ['D100', 'D103'],
                         2: ['W293'],
                         3: ['E261'],
                         5: ['undefined name']}
    for i, warning in warnings:
        assert any([expected in warning for expected in expected_warnings[i]])


@pytest.mark.slow
@pytest.mark.first
def test_move_warnings(qtbot, lsp_codeeditor):
    """Test that moving to next/previous warnings is working."""
    editor = lsp_codeeditor

    # Set text in editor
    editor.set_text(TEXT)

    # Notify changes
    with qtbot.waitSignal(editor.lsp_response_signal, timeout=30000):
        editor.document_did_change()

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


@pytest.mark.slow
@pytest.mark.first
def test_get_warnings(qtbot, lsp_codeeditor):
    """Test that the editor is returning the right list of warnings."""
    editor = lsp_codeeditor

    # Set text in editor
    editor.set_text(TEXT)

    # Notify changes
    with qtbot.waitSignal(editor.lsp_response_signal, timeout=30000):
        editor.document_did_change()

    # Get current warnings
    warnings = editor.get_current_warnings()

    expected = [['D100: Missing docstring in public module', 1],
                ['D103: Missing docstring in public function', 1],
                ['W293 blank line contains whitespace', 2],
                ['E261 at least two spaces before inline comment', 3],
                ["undefined name 's'", 5]]

    assert warnings == expected
