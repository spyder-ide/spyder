# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""
Tests for bookmarks.
"""

# Stdlib imports
from unittest.mock import Mock

# Third party imports
import pytest
from qtpy.QtGui import QTextCursor

# Local imports
import spyder.plugins.editor.widgets.codeeditor as codeeditor


# -----------------------------------------------------------------------------
# --- Helper functions
# -----------------------------------------------------------------------------
def reset_emits(editor):
    """Reset signal mocks."""
    editor.sig_bookmarks_changed.reset_mock()


def editor_assert_helper(editor, block=None, bm=None, emits=True):
    """
    Run the tests for call to add_remove_breakpoint.

    Args:
        editor (CodeEditor): CodeEditor instance.
        block (QTextBlock): Block of text.
        bm (list): A list containing slots and columns of bookmarks
        emits (bool): Boolean to test if signals were emitted?
    """
    data = block.userData()
    assert data.bookmarks == bm
    if emits:
        editor.sig_bookmarks_changed.emit.assert_called_with()
    else:
        editor.sig_bookmarks_changed.emit.assert_not_called()


# -----------------------------------------------------------------------------
# --- Fixtures
# -----------------------------------------------------------------------------
@pytest.fixture
def code_editor_bookmarks(qtbot):
    """Create code editor with default Python code."""
    editor = codeeditor.CodeEditor(parent=None)
    indent_chars = ' ' * 4
    tab_stop_width_spaces = 4
    editor.setup_editor(language='Python', indent_chars=indent_chars,
                        tab_stop_width_spaces=tab_stop_width_spaces)
    # Mock the signal emit to test when it's been called.
    editor.sig_bookmarks_changed = Mock()
    text = ('def f1(a, b):\n'
            '"Double quote string."\n'
            '\n'  # Blank line.
            '    c = a * b\n'
            '    return c\n'
            )
    editor.set_text(text)
    return editor, qtbot


# -----------------------------------------------------------------------------
# --- Tests
# -----------------------------------------------------------------------------
def test_add_bookmark(code_editor_bookmarks):
    """Test CodeEditor.add_bookmark. Adds bookmark data to Textblock."""
    editor, __ = code_editor_bookmarks

    editor.go_to_line(1)
    block = editor.textCursor().block()

    # Test with default call to slot 1 on text line containing code.
    reset_emits(editor)
    editor.add_bookmark(1)
    editor_assert_helper(editor, block, bm=[(1, 0)], emits=True)

    # Test on indented line and add multiple bookmarks.
    reset_emits(editor)
    editor.go_to_line(4)
    block = editor.textCursor().block()
    editor.add_bookmark(1)
    cursor = editor.textCursor()
    cursor.movePosition(QTextCursor.Right, n=2)
    editor.setTextCursor(cursor)
    editor.add_bookmark(2)
    editor_assert_helper(editor, block, bm=[(1, 0), (2, 2)], emits=True)


def test_get_bookmarks(code_editor_bookmarks):
    """Test CodeEditor.get_bookmarks. Returns data found in textblocks."""
    editor, __ = code_editor_bookmarks
    gb = editor.get_bookmarks

    assert(gb() == {})

    # Add bookmarks.
    bm = {1: ('filename', 1, 0), 2: ('filename', 3, 5), 3: ('filename', 4, 3)}
    editor.set_bookmarks(bm)
    assert(gb() == {1: [1, 0], 2: [3, 5], 3: [4, 3]})


def test_clear_bookmarks(code_editor_bookmarks):
    """Test CodeEditor.clear_bookmarks. Remove bookmarks from all blocks."""
    editor, __ = code_editor_bookmarks

    assert len(list(editor.blockuserdata_list())) == 1

    bm = {1: ('filename', 1, 0), 2: ('filename', 3, 5)}
    editor.set_bookmarks(bm)
    assert editor.get_bookmarks() == {1: [1, 0], 2: [3, 5]}
    assert len(list(editor.blockuserdata_list())) == 3

    editor.clear_bookmarks()
    assert editor.get_bookmarks() == {}
    # Even though there is a 'del data' that would pop the item from the
    # list, the __del__ function isn't called.
    assert len(list(editor.blockuserdata_list())) == 3
    for data in editor.blockuserdata_list():
        assert not data.bookmarks


def test_update_bookmarks(code_editor_bookmarks):
    """Test CodeEditor.update_bookmarks. Check if signal is emitted."""
    editor, __ = code_editor_bookmarks
    reset_emits(editor)
    editor.sig_bookmarks_changed.emit.assert_not_called()
    # update_bookmarks is the slot for the blockCountChanged signal.
    editor.textCursor().insertBlock()
    editor.sig_bookmarks_changed.emit.assert_called_with()


if __name__ == "__main__":
    pytest.main()
