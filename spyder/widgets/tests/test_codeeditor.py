# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
#

# Third party imports
from qtpy.QtCore import Qt
from qtpy.QtGui import QFont, QTextCursor
                            
from pytestqt import qtbot
import pytest

# Local imports
from spyder.widgets.editor import codeeditor


# --- Fixtures
# -----------------------------------------------------------------------------
@pytest.fixture
def editorbot(qtbot):
    widget = codeeditor.CodeEditor(None)
    widget.setup_editor(linenumbers=True, markers=True, tab_mode=False,
                         font=QFont("Courier New", 10),
                         show_blanks=True, color_scheme='Zenburn')
    widget.setup_editor(language='Python')
    qtbot.addWidget(widget)
    widget.show()
    return qtbot, widget

# --- Tests
# -----------------------------------------------------------------------------
# testing lowercase transformation functionality

def test_editor_upper_to_lower(editorbot):
    qtbot, widget = editorbot
    text = 'UPPERCASE'
    widget.set_text(text)
    cursor = widget.textCursor()
    cursor.movePosition(QTextCursor.NextCharacter,
                        QTextCursor.KeepAnchor)
    widget.setTextCursor(cursor)
    widget.transform_to_lowercase()
    new_text = widget.get_text('sof', 'eof')
    assert text != new_text

def test_editor_lower_to_upper(editorbot):
    qtbot, widget = editorbot
    text = 'uppercase'
    widget.set_text(text)
    cursor = widget.textCursor()
    cursor.movePosition(QTextCursor.NextCharacter,
                        QTextCursor.KeepAnchor)
    widget.setTextCursor(cursor)
    widget.transform_to_uppercase()
    new_text = widget.get_text('sof', 'eof')
    assert text != new_text

def test_editor_complete_backet(editorbot):
    qtbot, editor = editorbot
    editor.textCursor().insertText('foo')
    qtbot.keyClicks(editor, '(')
    assert editor.toPlainText() == 'foo()'
    assert editor.textCursor().columnNumber() == 4

def test_editor_complete_bracket_nested(editorbot):
    qtbot, editor = editorbot
    editor.textCursor().insertText('foo(bar)')
    editor.move_cursor(-1)
    qtbot.keyClicks(editor, '(')
    assert editor.toPlainText() == 'foo(bar())'
    assert editor.textCursor().columnNumber() == 8

def test_editor_bracket_closing(editorbot):
    qtbot, editor = editorbot
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

