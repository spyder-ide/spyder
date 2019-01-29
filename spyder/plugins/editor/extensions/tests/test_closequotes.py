# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
#
"""Tests for close quotes."""

# Third party imports
import pytest
from qtpy.QtCore import Qt
from qtpy.QtGui import QTextCursor

# Local imports
from spyder.utils.qthelpers import qapplication
from spyder.plugins.editor.widgets.codeeditor import CodeEditor
from spyder.plugins.editor.utils.editor import TextHelper
from spyder.plugins.editor.extensions.closequotes import (
        CloseQuotesExtension)


# --- Fixtures
# -----------------------------------------------------------------------------
@pytest.fixture
def editor_close_quotes():
    """Set up Editor with close quotes activated."""
    app = qapplication()
    editor = CodeEditor(parent=None)
    kwargs = {}
    kwargs['language'] = 'Python'
    kwargs['close_quotes'] = True
    editor.setup_editor(**kwargs)
    return editor

# --- Tests
# -----------------------------------------------------------------------------


@pytest.mark.parametrize(
    'text, expected_text, cursor_column',
    [
        ('"', '""', 1),  # Complete single quotes
        ("'", "''", 1),
        ('#"', '#"', 2),  # In comment, dont add extra quote
        ("#'", "#'", 2),
        ('"""', '"""', 3),  # Three quotes, dont add extra quotes
        ("'''", "'''", 3),
        ('""""', '""""""', 3),  # Four, complete docstring quotes
        ("''''", "''''''", 3),
        ('"some_string"', '"some_string"', 13),  # Write a string
        ("'some_string'", "'some_string'", 13),
    ])
def test_close_quotes(qtbot, editor_close_quotes, text, expected_text,
                      cursor_column):
    """Test insertion of extra quotes."""
    editor = editor_close_quotes

    qtbot.keyClicks(editor, text)
    assert editor.toPlainText() == expected_text

    assert cursor_column == TextHelper(editor).current_column_nbr()


@pytest.mark.parametrize(
    'text, expected_text, cursor_column',
    [
        ('()', '("")', 2),  # Complete in brackets
        ('{}', '{""}', 2),
        ('[]', '[""]', 2),
        (',', '"",', 1),  # Complete before commas, colons and semi-colons
        (':', '"":', 1),
        (';', '"";', 1),
        ('a', '"a', 1),  # No Completion before other text
    ])
def test_trailing_text(qtbot, editor_close_quotes, text, expected_text,
                       cursor_column):
    """
    Test insertion of extra quotes inside brackets and before commas,
    colons and semi-colons.
    """
    editor = editor_close_quotes

    qtbot.keyClicks(editor, text)
    editor.move_cursor(-1)
    qtbot.keyClicks(editor, '"')
    assert editor.toPlainText() == expected_text

    assert cursor_column == TextHelper(editor).current_column_nbr()


def test_selected_text(qtbot, editor_close_quotes):
    """Test insert surronding quotes to selected text."""
    editor = editor_close_quotes
    editor.set_text('some text')

    # select some
    cursor = editor.textCursor()
    cursor.movePosition(QTextCursor.Right, QTextCursor.KeepAnchor, 4)
    editor.setTextCursor(cursor)

    qtbot.keyClicks(editor, '"')
    assert editor.toPlainText() == '"some" text'

    qtbot.keyClicks(editor, '"')
    assert editor.toPlainText() == '""some"" text'

    qtbot.keyClicks(editor, '"')
    assert editor.toPlainText() == '"""some""" text'


def test_selected_text_multiple_lines(qtbot, editor_close_quotes):
    """Test insert surronding quotes to multiple lines selected text."""
    editor = editor_close_quotes
    text = ('some text\n'
            '\n'
            'some text')
    editor.set_text(text)

    # select until second some
    cursor = editor.textCursor()
    cursor.movePosition(QTextCursor.Right, QTextCursor.KeepAnchor, 4)
    cursor.movePosition(QTextCursor.Down, QTextCursor.KeepAnchor, 2)
    editor.setTextCursor(cursor)

    qtbot.keyClicks(editor, '"')
    assert editor.toPlainText() == ('"some text\n'
                                    '\n'
                                    'some" text')

    qtbot.keyClicks(editor, '"')
    assert editor.toPlainText() == ('""some text\n'
                                    '\n'
                                    'some"" text')

    qtbot.keyClicks(editor, '"')
    assert editor.toPlainText() == ('"""some text\n'
                                    '\n'
                                    'some""" text')


def test_close_quotes_in_brackets(qtbot, editor_close_quotes):
    """Test quote completion in nested brackets."""
    editor = editor_close_quotes
    # Test closing when following character is a right parentheses
    editor.textCursor().insertText('foo()')
    editor.move_cursor(-1)
    qtbot.keyClicks(editor, '"')
    assert editor.toPlainText() == 'foo("")'
    assert editor.textCursor().columnNumber() == 5
    # Test not closing when single quote is before a bracket
    qtbot.keyPress(editor, Qt.Key_Delete)  # now 'foo(")'
    qtbot.keyClicks(editor, '"')
    assert editor.toPlainText() == 'foo("")'
    assert editor.textCursor().columnNumber() == 6
    # Test closing when following character is a comma
    qtbot.keyClicks(editor, ', ,')
    editor.move_cursor(-1)
    qtbot.keyClicks(editor, '"')
    assert editor.toPlainText() == 'foo("", "",)'
    assert editor.textCursor().columnNumber() == 9
    # Test closing when following character is a right brace
    # and white preceding the next character
    editor.move_cursor(2)
    qtbot.keyClicks(editor, ' { },')
    editor.move_cursor(-3)
    qtbot.keyClicks(editor, '"')
    assert editor.toPlainText() == 'foo("", "", {"" },)'
    assert editor.textCursor().columnNumber() == 14
    # Test not closing otherwise
    editor.move_cursor(4)
    qtbot.keyClicks(editor, ' bar')
    editor.move_cursor(-3)
    qtbot.keyClicks(editor, '"')
    assert editor.toPlainText() == 'foo("", "", {"" }, "bar)'
    assert editor.textCursor().columnNumber() == 20


def test_activate_deactivate(qtbot, editor_close_quotes):
    """Test activating/desctivating close quotes editor extension."""
    editor = editor_close_quotes
    quote_extension = editor.editor_extensions.get(CloseQuotesExtension)

    qtbot.keyClicks(editor, '"')
    assert editor.toPlainText() == '""'

    editor.set_text('')
    quote_extension.enabled = False
    qtbot.keyClicks(editor, '"')
    assert editor.toPlainText() == '"'

    editor.set_text('')
    quote_extension.enabled = True
    qtbot.keyClicks(editor, '"')
    assert editor.toPlainText() == '""'


if __name__ == '__main__':
    pytest.main()
