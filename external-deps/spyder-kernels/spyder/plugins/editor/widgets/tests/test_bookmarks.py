# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""
Tests for bookmarks.
"""

# Third party imports
import pytest
from qtpy.QtGui import QTextCursor


# -----------------------------------------------------------------------------
# --- Tests
# -----------------------------------------------------------------------------
def test_save_bookmark(editor_plugin_open_files):
    """
    Test Plugin.save_bookmark.

    Test saving of bookmarks by looking at data in blocks. Reassignment
    should remove data from old block and put it in new.
    """
    editor, _, _ = editor_plugin_open_files(None, None)

    # Get current editorstack, active editor and cursor
    editorstack = editor.get_current_editorstack()
    edtr = editorstack.get_current_editor()
    cursor = edtr.textCursor()

    # Basic functionality: save a bookmark and check if it's there
    editor.save_bookmark(1)
    bookmarks = edtr.document().findBlockByNumber(0).userData().bookmarks
    assert bookmarks == [(1, 0)]

    # Move the cursor and reset the same bookmark
    cursor.movePosition(QTextCursor.Down, n=1)
    cursor.movePosition(QTextCursor.Right, n=2)
    edtr.setTextCursor(cursor)
    editor.save_bookmark(1)

    # Check if bookmark is there
    bookmarks = edtr.document().findBlockByNumber(1).userData().bookmarks
    assert bookmarks == [(1, 2)]

    # Check if bookmark was removed from previous block
    bookmarks = edtr.document().findBlockByNumber(0).userData().bookmarks
    assert bookmarks == []


def test_load_bookmark(editor_plugin_open_files):
    """
    Test that loading a bookmark works.

    Check this by saving and loading bookmarks and checking for cursor
    position. Also over multiple files.
    """
    editor, _, _ = editor_plugin_open_files(None, None)

    # Get current editorstack, active editor and cursor
    editorstack = editor.get_current_editorstack()
    edtr = editorstack.get_current_editor()
    cursor = edtr.textCursor()

    # Basic functionality: save and load a bookmark and
    # check if the cursor is there.
    editor.save_bookmark(1)
    cursor.movePosition(QTextCursor.Down, n=1)
    cursor.movePosition(QTextCursor.Right, n=4)
    edtr.setTextCursor(cursor)

    assert edtr.get_cursor_line_column() != (0, 0)

    editor.load_bookmark(1)

    assert edtr.get_cursor_line_column() == (0, 0)

    # Move cursor to end of line and remove characters
    cursor.movePosition(QTextCursor.Down, n=1)
    cursor.movePosition(QTextCursor.Right, n=19)
    edtr.setTextCursor(cursor)

    editor.save_bookmark(2)
    edtr.stdkey_backspace()
    edtr.stdkey_backspace()
    editor.load_bookmark(2)

    assert edtr.get_cursor_line_column() == (1, 20)

    # Check if loading bookmark switches file correctly
    editor.save_bookmark(2)
    editorstack.tabs.setCurrentIndex(1)
    editor.load_bookmark(2)
    assert editorstack.tabs.currentIndex() == 0


if __name__ == "__main__":
    pytest.main()
