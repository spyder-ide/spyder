# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
#
"""Tests for close brackets."""

# Third party imports
import pytest
from qtpy.QtGui import QTextCursor

# Local imports
from spyder.utils.qthelpers import qapplication
from spyder.plugins.editor.widgets.codeeditor import CodeEditor
from spyder.plugins.editor.utils.editor import TextHelper
from spyder.plugins.editor.extensions.closebrackets import (
        CloseBracketsExtension)


# =============================================================================
# ---- Fixtures
# =============================================================================
@pytest.fixture
def editor_close_brackets():
    """Set up Editor with close brackets activated."""
    app = qapplication()
    editor = CodeEditor(parent=None)
    kwargs = {}
    kwargs['language'] = 'Python'
    kwargs['close_parentheses'] = True
    editor.setup_editor(**kwargs)
    return editor


# =============================================================================
# ---- Tests
# =============================================================================
@pytest.mark.parametrize(
    'text, expected_text, cursor_column',
    [
        ("(", "()", 1),  # Close brackets
        ("{", "{}", 1),
        ("[", "[]", 1),
    ])
def test_close_brackets(qtbot, editor_close_brackets, text, expected_text,
                        cursor_column):
    """Test insertion of brackets."""
    editor = editor_close_brackets

    qtbot.keyClicks(editor, text)
    assert editor.toPlainText() == expected_text

    assert cursor_column == TextHelper(editor).current_column_nbr()


@pytest.mark.parametrize(
    'text, expected_text, cursor_column',
    [
        ('()', '(())', 2),  # Complete in brackets
        ('{}', '{()}', 2),
        ('[]', '[()]', 2),
        (',', '(),', 1),  # Complete before commas, colons and semi-colons
        (':', '():', 1),
        (';', '();', 1),
    ])
def test_nested_brackets(qtbot, editor_close_brackets, text, expected_text,
                      cursor_column):
    """
    Test completion of brackets inside brackets and before commas,
    colons and semi-colons.
    """
    editor = editor_close_brackets

    qtbot.keyClicks(editor, text)
    editor.move_cursor(-1)
    qtbot.keyClicks(editor, '(')
    assert editor.toPlainText() == expected_text

    assert cursor_column == TextHelper(editor).current_column_nbr()


def test_selected_text(qtbot, editor_close_brackets):
    """Test insert surronding brackets to selected text."""
    editor = editor_close_brackets
    editor.set_text("some text")

    # select some
    cursor = editor.textCursor()
    cursor.movePosition(QTextCursor.Right, QTextCursor.KeepAnchor, 4)
    editor.setTextCursor(cursor)

    qtbot.keyClicks(editor, "(")
    assert editor.toPlainText() == "(some) text"

    qtbot.keyClicks(editor, "}")
    assert editor.toPlainText() == "({some}) text"

    qtbot.keyClicks(editor, "[")
    assert editor.toPlainText() == "({[some]}) text"


def test_selected_text_multiple_lines(qtbot, editor_close_brackets):
    """Test insert surronding brackets to multiple lines selected text."""
    editor = editor_close_brackets
    text = ("some text\n"
            "\n"
            "some text")
    editor.set_text(text)

    # select until second some
    cursor = editor.textCursor()
    cursor.movePosition(QTextCursor.Right, QTextCursor.KeepAnchor, 4)
    cursor.movePosition(QTextCursor.Down, QTextCursor.KeepAnchor, 2)
    editor.setTextCursor(cursor)

    qtbot.keyClicks(editor, ")")
    assert editor.toPlainText() == ("(some text\n"
                                    "\n"
                                    "some) text")

    qtbot.keyClicks(editor, "{")
    assert editor.toPlainText() == ("({some text\n"
                                    "\n"
                                    "some}) text")

    qtbot.keyClicks(editor, "]")
    assert editor.toPlainText() == ("({[some text\n"
                                    "\n"
                                    "some]}) text")


def test_complex_completion(qtbot, editor_close_brackets):
    """Test bracket completion in nested brackets."""
    editor = editor_close_brackets
    # Test completion when following character is a right bracket
    editor.textCursor().insertText('foo(bar)')
    editor.move_cursor(-1)
    qtbot.keyClicks(editor, '(')
    assert editor.toPlainText() == 'foo(bar())'
    assert editor.textCursor().columnNumber() == 8
    # Test normal insertion when next character is not a right bracket
    editor.move_cursor(-1)
    qtbot.keyClicks(editor, '[')
    assert editor.toPlainText() == 'foo(bar[())'
    assert editor.textCursor().columnNumber() == 8
    # Test completion when following character is a comma
    qtbot.keyClicks(editor, ',')
    editor.move_cursor(-1)
    qtbot.keyClicks(editor, '{')
    assert editor.toPlainText() == 'foo(bar[{},())'
    assert editor.textCursor().columnNumber() == 9


def test_bracket_closing(qtbot, editor_close_brackets):
    """Test bracket completion with existing brackets."""
    editor = editor_close_brackets
    editor.textCursor().insertText('foo(bar(x')
    qtbot.keyClicks(editor, ')')
    assert editor.toPlainText() == 'foo(bar(x)'
    assert editor.textCursor().columnNumber() == 10
    qtbot.keyClicks(editor, ')')
    assert editor.toPlainText() == 'foo(bar(x))'
    assert editor.textCursor().columnNumber() == 11
    # same ')' closing with existing brackets starting at 'foo(bar(x|))'
    editor.move_cursor(-2)
    qtbot.keyClicks(editor, ')')
    assert editor.toPlainText() == 'foo(bar(x))'
    assert editor.textCursor().columnNumber() == 10
    qtbot.keyClicks(editor, ')')
    assert editor.toPlainText() == 'foo(bar(x))'
    assert editor.textCursor().columnNumber() == 11


def test_activate_deactivate(qtbot, editor_close_brackets):
    """Test activating/desctivating close quotes editor extension."""
    editor = editor_close_brackets
    bracket_extension = editor.editor_extensions.get(CloseBracketsExtension)

    qtbot.keyClicks(editor, "(")
    assert editor.toPlainText() == "()"

    editor.set_text("")
    bracket_extension.enabled = False
    qtbot.keyClicks(editor, "(")
    assert editor.toPlainText() == "("

    editor.set_text("")
    bracket_extension.enabled = True
    qtbot.keyClicks(editor, "(")
    assert editor.toPlainText() == "()"


if __name__ == '__main__':
    pytest.main()
