# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
#

"""Tests for editor codeanalysis warnings."""

# Stdlib imports
import os
import sys

# Third party imports
from flaky import flaky
import pytest
from qtpy.QtCore import Qt

# Local imports
from spyder.config.manager import CONF


TEXT = ("def some_function():\n"  # D100, D103: Missing docstring
        "    \n"  # W293 trailing spaces
        "    a = 1 # a comment\n"  # E261 two spaces before inline comment
        "\n"
        "    a += s\n"  # Undefined variable s
        "    return a\n"
        "undefined_function()")  # Undefined name 'undefined_function'


@pytest.mark.slow
@pytest.mark.second
@flaky(max_runs=5)
def test_ignore_warnings(qtbot, lsp_codeeditor):
    """Test that the editor is ignoring some warnings."""
    editor, manager = lsp_codeeditor

    # Set text in editor
    editor.set_text(TEXT)

    CONF.set('lsp-server', 'pydocstyle/ignore', 'D100')
    CONF.set('lsp-server', 'pycodestyle/ignore', 'E261')

    # After this call the manager needs to be reinitialized
    manager.update_configuration()
    qtbot.wait(2000)

    # Notify changes
    with qtbot.waitSignal(editor.lsp_response_signal, timeout=30000):
        editor.document_did_change()

    # Get current warnings
    warnings = editor.get_current_warnings()

    expected = [['D103: Missing docstring in public function', 1],
                ['W293 blank line contains whitespace', 2],
                ["undefined name 's'", 5],
                ["undefined name 'undefined_function'", 7],
                ["W292 no newline at end of file", 7],
                ["""E305 expected 2 blank lines after class or """
                 """function definition, found 0""", 7]]

    CONF.set('lsp-server', 'pydocstyle/ignore', '')
    CONF.set('lsp-server', 'pycodestyle/ignore', '')
    manager.update_configuration()
    qtbot.wait(2000)

    assert warnings == expected


@pytest.mark.slow
@pytest.mark.second
@flaky(max_runs=5)
def test_adding_warnings(qtbot, lsp_codeeditor):
    """Test that warnings are saved in the editor blocks."""
    editor, _ = lsp_codeeditor

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
                         5: ['undefined name'],
                         7: ['undefined name', 'W292', 'E305']}
    for i, warning in warnings:
        assert any([expected in warning for expected in expected_warnings[i]])


@pytest.mark.slow
@pytest.mark.second
@flaky(max_runs=5)
def test_move_warnings(qtbot, lsp_codeeditor):
    """Test that moving to next/previous warnings is working."""
    editor, _ = lsp_codeeditor

    # Set text in editor
    editor.set_text(TEXT)

    # Notify changes
    with qtbot.waitSignal(editor.lsp_response_signal, timeout=30000):
        editor.document_did_change()

    # Wait for linting info to arrive
    qtbot.wait(2000)

    # Move between warnings
    editor.go_to_next_warning()
    assert 2 == editor.get_cursor_line_number()

    editor.go_to_next_warning()
    assert 3 == editor.get_cursor_line_number()

    editor.go_to_previous_warning()
    assert 2 == editor.get_cursor_line_number()

    # Test cycling behaviour
    editor.go_to_line(7)
    editor.go_to_next_warning()
    assert 1 == editor.get_cursor_line_number()

    editor.go_to_previous_warning()
    assert 7 == editor.get_cursor_line_number()


@pytest.mark.slow
@pytest.mark.second
@flaky(max_runs=5)
def test_get_warnings(qtbot, lsp_codeeditor):
    """Test that the editor is returning the right list of warnings."""
    editor, _ = lsp_codeeditor

    # Set text in editor
    editor.set_text(TEXT)

    # Notify changes
    with qtbot.waitSignal(editor.lsp_response_signal, timeout=30000):
        editor.document_did_change()

    # Wait for linting info to arrive
    qtbot.wait(2000)

    # Get current warnings
    warnings = editor.get_current_warnings()

    expected = [['D100: Missing docstring in public module', 1],
                ['D103: Missing docstring in public function', 1],
                ['W293 blank line contains whitespace', 2],
                ['E261 at least two spaces before inline comment', 3],
                ["undefined name 's'", 5],
                ["undefined name 'undefined_function'", 7],
                ["W292 no newline at end of file", 7],
                ["""E305 expected 2 blank lines after class or """
                 """function definition, found 0""", 7]]

    assert warnings == expected


@pytest.mark.slow
@pytest.mark.second
@flaky(max_runs=5)
def test_update_warnings_after_delete_line(qtbot, lsp_codeeditor):
    """
    Test that code style warnings are correctly updated after deleting a line
    in the Editor.

    Regression test for spyder-ide/spyder#9299.
    """
    editor, _ = lsp_codeeditor
    editor.set_text(TEXT)

    # Notify changes.
    with qtbot.waitSignal(editor.lsp_response_signal, timeout=30000):
        editor.document_did_change()

    # Wait for linting info to arrive
    qtbot.wait(2000)

    # Delete the blank line that is causing the W293 warning on line 2.
    editor.go_to_line(2)
    editor.delete_line()

    # Wait for the lsp_response_signal.
    qtbot.waitSignal(editor.lsp_response_signal, timeout=30000)

    # Assert that the W293 warning is gone.
    expected = [['D100: Missing docstring in public module', 1],
                ['D103: Missing docstring in public function', 1],
                ['E261 at least two spaces before inline comment', 2],
                ["undefined name 's'", 4],
                ["undefined name 'undefined_function'", 6],
                ["W292 no newline at end of file", 6],
                ["""E305 expected 2 blank lines after class or """
                 """function definition, found 0""", 6]]
    assert editor.get_current_warnings() == expected


@pytest.mark.slow
@pytest.mark.second
@flaky(max_runs=5)
def test_update_warnings_after_closequotes(qtbot, lsp_codeeditor):
    """
    Test that code errors are correctly updated after activating closequotes
    in the Editor.

    Regression test for spyder-ide/spyder#9323.
    """
    editor, _ = lsp_codeeditor
    editor.textCursor().insertText("print('test)\n")

    expected = [['EOL while scanning string literal', 1]]

    # Notify changes.
    with qtbot.waitSignal(editor.lsp_response_signal, timeout=30000):
        editor.document_did_change()

    # Wait for linting info to arrive
    qtbot.wait(2000)

    assert editor.get_current_warnings() == expected

    # Wait for the lsp_response_signal.
    with qtbot.waitSignal(editor.lsp_response_signal, timeout=30000):
        # Add a single quote to fix the error
        editor.move_cursor(-2)
        qtbot.keyPress(editor, Qt.Key_Apostrophe)
        assert editor.toPlainText() == "print('test')\n"

    # Assert that the error is gone.
    expected = [['D100: Missing docstring in public module', 1]]
    assert editor.get_current_warnings() == expected


@pytest.mark.slow
@pytest.mark.second
@flaky(max_runs=5)
def test_update_warnings_after_closebrackets(qtbot, lsp_codeeditor):
    """
    Test that code errors are correctly updated after activating closebrackets
    in the Editor.

    Regression test for spyder-ide/spyder#9323.
    """
    editor, _ = lsp_codeeditor
    editor.textCursor().insertText("print('test'\n")

    expected = [['unexpected EOF while parsing', 1],
                ['E901 TokenError: EOF in multi-line statement', 2]]

    # Notify changes.
    with qtbot.waitSignal(editor.lsp_response_signal, timeout=30000):
        editor.document_did_change()

    # Wait for linting info to arrive
    qtbot.wait(2000)

    assert editor.get_current_warnings() == expected

    # Wait for the lsp_response_signal.
    with qtbot.waitSignal(editor.lsp_response_signal, timeout=30000):
        # Add a bracket to fix the error
        editor.move_cursor(-1)
        qtbot.keyPress(editor, Qt.Key_ParenRight)
        assert editor.toPlainText() == "print('test')\n"

    # Assert that the error is gone.
    expected = [['D100: Missing docstring in public module', 1]]
    assert editor.get_current_warnings() == expected
