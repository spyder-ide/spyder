# -*- coding: utf-8 -*-

# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""Tests for the CodeEditor Extract function refactoring."""

# Third party imports
import pytest
from qtpy.QtGui import QTextCursor

# Local imports
from spyder.plugins.editor.widgets.codeeditor import codeeditor


CODE = """def compute(values):
    total = 0
    for value in values:
        squared = value * value
        total += squared
    print(total)
    return total
"""


def select_text(editor, start_text, end_text):
    """Select from the start of start_text to the end of end_text."""
    text = editor.toPlainText()
    cursor = editor.textCursor()
    cursor.setPosition(text.index(start_text))
    cursor.setPosition(
        text.index(end_text) + len(end_text), QTextCursor.KeepAnchor
    )
    editor.setTextCursor(cursor)


def patch_dialogs(monkeypatch, name='new_function', accepted=True):
    """Mock the name dialog and capture message boxes."""
    messages = []
    monkeypatch.setattr(
        codeeditor.QInputDialog,
        'getText',
        staticmethod(lambda *args, **kwargs: (name, accepted)),
    )
    monkeypatch.setattr(
        codeeditor.QMessageBox,
        'information',
        staticmethod(lambda parent, title, text, *a: messages.append(text)),
    )
    monkeypatch.setattr(
        codeeditor.QMessageBox,
        'warning',
        staticmethod(lambda parent, title, text, *a: messages.append(text)),
    )
    return messages


def test_extract_function(codeeditor, monkeypatch):
    """Extracting a block creates a function with the right signature."""
    editor = codeeditor
    editor.set_text(CODE)
    patch_dialogs(monkeypatch)
    select_text(editor, "    for value", "total += squared")

    editor.extract_function()

    new_text = editor.toPlainText()
    assert 'def new_function(' in new_text
    assert 'total = new_function(' in new_text
    # The extracted function must receive the block's inputs and return
    # the variable used afterwards.
    assert 'values' in new_text.split('def new_function(')[1].split(')')[0]
    assert 'return total' in new_text.split('def new_function(')[1]


def test_extract_function_undo(codeeditor, monkeypatch):
    """The refactoring is reverted with a single undo."""
    editor = codeeditor
    editor.set_text(CODE)
    patch_dialogs(monkeypatch)
    select_text(editor, "    for value", "total += squared")

    editor.extract_function()
    assert editor.toPlainText() != CODE

    editor.undo()
    assert editor.toPlainText() == CODE


def test_extract_function_no_selection(codeeditor, monkeypatch):
    """Without a selection the user is informed and nothing changes."""
    editor = codeeditor
    editor.set_text(CODE)
    messages = patch_dialogs(monkeypatch)

    editor.extract_function()

    assert editor.toPlainText() == CODE
    assert len(messages) == 1
    assert 'select' in messages[0]


def test_extract_function_invalid_name(codeeditor, monkeypatch):
    """An invalid function name shows a warning and nothing changes."""
    editor = codeeditor
    editor.set_text(CODE)
    messages = patch_dialogs(monkeypatch, name='1bad name')
    select_text(editor, "    for value", "total += squared")

    editor.extract_function()

    assert editor.toPlainText() == CODE
    assert len(messages) == 1
    assert 'identifier' in messages[0]


def test_extract_function_cancelled(codeeditor, monkeypatch):
    """Cancelling the name dialog leaves the text unchanged."""
    editor = codeeditor
    editor.set_text(CODE)
    messages = patch_dialogs(monkeypatch, accepted=False)
    select_text(editor, "    for value", "total += squared")

    editor.extract_function()

    assert editor.toPlainText() == CODE
    assert messages == []


def test_extract_function_invalid_selection(codeeditor, monkeypatch):
    """A selection that breaks statements shows a warning."""
    editor = codeeditor
    editor.set_text(CODE)
    messages = patch_dialogs(monkeypatch)
    # Select from the middle of one statement to the middle of another
    select_text(editor, "in values", "squared = value")

    editor.extract_function()

    assert editor.toPlainText() == CODE
    assert len(messages) == 1
    assert 'not possible to extract' in messages[0]


if __name__ == '__main__':
    pytest.main([__file__])
