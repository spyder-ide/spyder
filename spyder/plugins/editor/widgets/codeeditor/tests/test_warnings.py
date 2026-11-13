# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
#

"""Tests for editor codeanalysis warnings."""

# Stdlib imports
import sys

# Third party imports
from flaky import flaky
import pytest
from qtpy.QtCore import Qt

# Local imports
from spyder.config.manager import CONF


TEXT = ("def some_function():\n"
        "    \n"  # W293 blank line with whitespace
        "    a = 1 # a comment\n"
        "\n"
        "    a += s\n"  # Undefined variable s
        "    return a\n"
        "undefined_function()")  # Undefined name 'undefined_function', W292


@pytest.fixture
def completions_codeeditor_linting(request, qtbot, completions_codeeditor):
    editor, completion_plugin = completions_codeeditor
    # Style rules on top of ruff's defaults, like flake8 reported.
    CONF.set('language_services',
             ('providers', 'ruff', 'values', 'extend_select'),
             'E, W')

    # After this call the manager needs to be reinitialized
    completion_plugin.after_configuration_update([])
    qtbot.wait(2000)

    def teardown():
        CONF.set('language_services',
                 ('providers', 'ruff', 'values', 'extend_select'),
                 '')

        # After this call the manager needs to be reinitialized
        completion_plugin.after_configuration_update([])
        qtbot.wait(2000)

    request.addfinalizer(teardown)

    return editor, completion_plugin


@pytest.mark.order(2)
@flaky(max_runs=5)
def test_ignore_warnings(qtbot, completions_codeeditor_linting):
    """Test that the editor is ignoring some warnings."""
    editor, completion_plugin = completions_codeeditor_linting

    CONF.set('language_services',
             ('providers', 'ruff', 'values', 'ignore'),
             'W293')

    # After this call the manager needs to be reinitialized
    completion_plugin.after_configuration_update([])
    qtbot.wait(2500)

    # Set text in editor
    with qtbot.waitSignal(editor.completions_response_signal, timeout=30000):
        editor.set_text(TEXT)

    # Get current warnings
    qtbot.wait(2500)
    warnings = editor.get_current_warnings()

    expected = [["Could not find name `s`", 5],
                ["Undefined name `s`", 5],
                ["Could not find name `undefined_function`", 7],
                ["Undefined name `undefined_function`", 7],
                ["No newline at end of file", 7]]

    CONF.set('language_services',
             ('providers', 'ruff', 'values', 'ignore'),
             '')

    completion_plugin.after_configuration_update([])
    qtbot.wait(2500)

    assert warnings == expected


@pytest.mark.order(2)
@flaky(max_runs=5)
def test_adding_warnings(qtbot, completions_codeeditor_linting):
    """Test that warnings are saved in the editor blocks."""
    editor, _ = completions_codeeditor_linting

    # Set text in editor
    with qtbot.waitSignal(editor.completions_response_signal, timeout=30000):
        editor.set_text(TEXT)

    qtbot.wait(2000)
    block = editor.textCursor().block()
    line_count = editor.document().blockCount()

    warnings = []
    for i in range(line_count):
        data = block.userData()
        if data:
            for analysis in data.code_analysis:
                warnings.append((i+1, analysis[-1]))
        block = block.next()

    expected_warnings = {2: ['Blank line contains whitespace'],
                         5: ['Could not find name', 'Undefined name'],
                         7: ['Could not find name', 'Undefined name',
                             'No newline at end of file']}
    for i, warning in warnings:
        assert any([expected in warning for expected in expected_warnings[i]])


@pytest.mark.order(2)
@flaky(max_runs=5)
def test_move_warnings(qtbot, completions_codeeditor_linting):
    """Test that moving to next/previous warnings is working."""
    editor, _ = completions_codeeditor_linting


    # Set text in editor
    with qtbot.waitSignal(editor.completions_response_signal, timeout=30000):
        editor.set_text(TEXT)


    # Wait for linting info to arrive
    qtbot.wait(2000)

    # Move between warnings
    editor.go_to_next_warning()
    assert 2 == editor.get_cursor_line_number()

    editor.go_to_next_warning()
    assert 5 == editor.get_cursor_line_number()

    editor.go_to_next_warning()
    assert 7 == editor.get_cursor_line_number()

    # Test cycling behaviour
    editor.go_to_line(7)
    editor.go_to_next_warning()
    assert 2 == editor.get_cursor_line_number()

    editor.go_to_previous_warning()
    assert 7 == editor.get_cursor_line_number()


@pytest.mark.order(2)
@flaky(max_runs=5)
@pytest.mark.skipif(sys.platform == "darwin", reason="Fails sometimes on Mac")
def test_get_warnings(qtbot, completions_codeeditor_linting):
    """Test that the editor is returning the right list of warnings."""
    editor, _ = completions_codeeditor_linting

    # Set text in editor
    with qtbot.waitSignal(editor.completions_response_signal, timeout=30000):
        editor.set_text(TEXT)

    # Wait for linting info to arrive
    qtbot.wait(2000)

    # Get current warnings
    warnings = editor.get_current_warnings()

    expected = [["Blank line contains whitespace", 2],
                ["Could not find name `s`", 5],
                ["Undefined name `s`", 5],
                ["Could not find name `undefined_function`", 7],
                ["Undefined name `undefined_function`", 7],
                ["No newline at end of file", 7]]

    assert warnings == expected


@pytest.mark.order(2)
@flaky(max_runs=5)
@pytest.mark.skipif(sys.platform == "darwin", reason="Fails sometimes on Mac")
def test_update_warnings_after_delete_line(qtbot, completions_codeeditor_linting):
    """
    Test that code style warnings are correctly updated after deleting a line
    in the Editor.

    Regression test for spyder-ide/spyder#9299.
    """
    editor, _ = completions_codeeditor_linting
    
    # Set text in editor
    with qtbot.waitSignal(editor.completions_response_signal, timeout=30000):
        editor.set_text(TEXT)

    # Wait for linting info to arrive
    qtbot.wait(2000)

    # Delete the blank line that is causing the W293 warning on line 2.
    editor.go_to_line(2)
    editor.delete_line()

    # Wait for the lsp_response_signal.
    qtbot.waitSignal(editor.completions_response_signal, timeout=30000)

    # Assert that the W293 warning is gone.
    expected = [["Could not find name `s`", 4],
                ["Undefined name `s`", 4],
                ["Could not find name `undefined_function`", 6],
                ["Undefined name `undefined_function`", 6],
                ["No newline at end of file", 6]]

    assert editor.get_current_warnings() == expected


@pytest.mark.order(2)
@flaky(max_runs=5)
@pytest.mark.skipif(sys.platform == "darwin", reason="Fails sometimes on Mac")
def test_update_warnings_after_closequotes(qtbot, completions_codeeditor_linting):
    """
    Test that code errors are correctly updated after activating closequotes
    in the Editor.

    Regression test for spyder-ide/spyder#9323.
    """
    editor, _ = completions_codeeditor_linting

    # Pyrefly and ruff both report the error, with different messages
    expected = [
        ['Parse error: missing closing quote in string literal', 1],
        ['missing closing quote in string literal', 1],
        ['Parse error: unexpected EOF while parsing', 2],
        ['unexpected EOF while parsing', 2],
    ]

    # Notify changes.
    with qtbot.waitSignal(editor.completions_response_signal, timeout=30000):
        editor.textCursor().insertText("print('test)\n")

    # Wait for linting info to arrive
    qtbot.wait(2000)

    assert editor.get_current_warnings() == expected

    # Wait for the lsp_response_signal.
    with qtbot.waitSignal(editor.completions_response_signal, timeout=30000):
        # Add a single quote to fix the error
        editor.move_cursor(-2)
        qtbot.keyPress(editor, Qt.Key_Apostrophe)
        assert editor.toPlainText() == "print('test')\n"

    # Assert that the error is gone.
    qtbot.wait(2000)
    expected = []
    assert editor.get_current_warnings() == expected


@pytest.mark.order(2)
@flaky(max_runs=5)
@pytest.mark.skipif(sys.platform == "darwin", reason="Fails sometimes on Mac")
def test_update_warnings_after_closebrackets(qtbot, completions_codeeditor_linting):
    """
    Test that code errors are correctly updated after activating closebrackets
    in the Editor.

    Regression test for spyder-ide/spyder#9323.
    """
    editor, _ = completions_codeeditor_linting

    expected = [
        ['Parse error: unexpected EOF while parsing', 2],
        ['unexpected EOF while parsing', 2],
    ]

    # Notify changes.
    with qtbot.waitSignal(editor.completions_response_signal, timeout=30000):
        editor.textCursor().insertText("print('test'\n")

    # Wait for linting info to arrive
    qtbot.wait(2000)

    assert editor.get_current_warnings() == expected

    # Wait for the lsp_response_signal.
    with qtbot.waitSignal(editor.completions_response_signal, timeout=30000):
        # Add a bracket to fix the error
        editor.move_cursor(-1)
        qtbot.keyPress(editor, Qt.Key_ParenRight)
        assert editor.toPlainText() == "print('test')\n"

    # Assert that the error is gone.
    qtbot.wait(2000)
    expected = [] 

    assert editor.get_current_warnings() == expected


@pytest.mark.order(2)
@flaky(max_runs=5)
@pytest.mark.parametrize(
    'ignore_comment', ['#noqa', '# NOQA', '# analysis:ignore', '# no-work']
)
@pytest.mark.skipif(sys.platform == "darwin", reason="Fails sometimes on Mac")
def test_ignore_warnings_with_comments(
    qtbot, completions_codeeditor_linting, ignore_comment
):
    """
    Test that ignoring linting messages with inline comments works as
    expected.
    """
    editor, _ = completions_codeeditor_linting

    if ignore_comment == '# no-work':
        expected = [
            ['Could not find name `foo`', 1],
            ['Undefined name `foo`', 1],
            ['Could not find name `bar`', 2],
            ['Undefined name `bar`', 2],
        ]
    else:
        expected = [['Could not find name `bar`', 2],
                    ['Undefined name `bar`', 2]]

    # Notify changes.
    with qtbot.waitSignal(editor.completions_response_signal, timeout=30000):
        editor.textCursor().insertText(
            f"foo {ignore_comment}\n"
            "bar\n"
        )

    # Wait for linting info to arrive
    qtbot.wait(2000)

    assert editor.get_current_warnings() == expected
