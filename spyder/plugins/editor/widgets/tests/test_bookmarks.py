# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
#

"""
Tests for bookmarks.
"""

# Standard library imports
import os.path as osp

try:
    from unittest.mock import Mock
except ImportError:
    from mock import Mock  # Python 2

# Third party imports
import pytest
from qtpy.QtGui import QTextCursor
from qtpy.QtWidgets import QMainWindow

# Local imports
from spyder import version_info
from spyder.py3compat import to_text_string
from spyder.utils.qthelpers import qapplication
import spyder.plugins.editor.widgets.codeeditor as codeeditor


# --- Helper methods
# -----------------------------------------------------------------------------
def reset_emits(editor):
    "Reset signal mocks."
    editor.bookmarks_changed.reset_mock()


def editor_assert_helper(editor, block=None, bm=None, emits=True):
    """Run the tests for call to add_remove_breakpoint.

    Args:
        editor: CodeEditor instance.
        block: Block of text.
        bm: A list containing slots and columns of bookmarks
        emits: Boolean to test if signals were emitted?
    """
    data = block.userData()
    assert data.bookmarks == bm
    if emits:
        editor.bookmarks_changed.emit.assert_called_with()
    else:
        editor.bookmarks_changed.emit.assert_not_called()


# --- Fixtures
# -----------------------------------------------------------------------------
@pytest.fixture
def code_editor_bot(qtbot):
    """Create code editor with default Python code."""
    editor = codeeditor.CodeEditor(parent=None)
    indent_chars = ' ' * 4
    tab_stop_width_spaces = 4
    editor.setup_editor(language='Python', indent_chars=indent_chars,
                        tab_stop_width_spaces=tab_stop_width_spaces)
    # Mock the signal emit to test when it's been called.
    editor.bookmarks_changed = Mock()
    text = ('def f1(a, b):\n'
            '"Double quote string."\n'
            '\n'  # Blank line.
            '    c = a * b\n'
            '    return c\n'
            )
    editor.set_text(text)
    return editor, qtbot


# ---- Qt Test Fixtures
@pytest.fixture
def setup_editor(qtbot, monkeypatch):
    """Set up the Editor plugin."""
    qapplication()
    from spyder.plugins.editor.plugin import Editor

    monkeypatch.setattr('spyder.plugins.editor.plugin.add_actions', Mock())

    class MainMock(QMainWindow):
        def __getattr__(self, attr):
            if attr.endswith('actions'):
                return []
            elif attr == 'projects':
                projects = Mock()
                projects.get_active_project.return_value = None
                return projects
            else:
                return Mock()

    window = MainMock()
    editor = Editor(window)
    window.setCentralWidget(editor)
    window.resize(640, 480)
    qtbot.addWidget(window)
    window.show()

    yield editor


@pytest.fixture(scope="module")
def test_file(tmpdir_factory):
    """Create and save some python code and text in temporary file."""
    tmpdir = tmpdir_factory.mktemp("files")

    filename = osp.join(tmpdir.strpath, 'foo1.py')
    with open(filename, 'w') as f:
        f.write("# -*- coding: utf-8 -*-\n"
                "def foo:\n"
                "    print(Hello World!)\n")

    return filename


# --- Tests
# -----------------------------------------------------------------------------
def test_add_bookmark(code_editor_bot, mocker):
    """Test CodeEditor.add_bookmark. Adds bookmark data to Textblock."""
    editor, _ = code_editor_bot
    ab = editor.add_bookmark

    mocker.patch.object(codeeditor.QInputDialog, 'getText')

    editor.go_to_line(1)
    block = editor.textCursor().block()

    # Test with default call to slot 1 on text line containing code.
    reset_emits(editor)
    ab(1)
    editor_assert_helper(editor, block, bm=[(1, 0)], emits=True)

    # Test on indented line and add multiple bookmarks.
    reset_emits(editor)
    editor.go_to_line(4)
    block = editor.textCursor().block()
    ab(1)
    cursor = editor.textCursor()
    cursor.movePosition(QTextCursor.Right, n=2)
    editor.setTextCursor(cursor)
    ab(2)
    editor_assert_helper(editor, block, bm=[(1, 0), (2, 2)], emits=True)


def test_get_bookmarks(code_editor_bot):
    """Test CodeEditor.get_bookmarks. Returns data found in textblocks."""
    editor, _ = code_editor_bot
    gb = editor.get_bookmarks

    assert(gb() == {})

    # Add bookmarks.
    bm = {1: ('filename', 1, 0), 2: ('filename', 3, 5), 3: ('filename', 4, 3)}
    editor.set_bookmarks(bm)
    assert(gb() == {1: [1, 0], 2: [3, 5], 3: [4, 3]})


def test_clear_bookmarks(code_editor_bot):
    """Test CodeEditor.clear_bookmarks. Removes bookmarks from all blocks."""
    editor, _ = code_editor_bot

    assert len(editor.blockuserdata_list) == 0

    bm = {1: ('filename', 1, 0), 2: ('filename', 3, 5)}
    editor.set_bookmarks(bm)
    assert editor.get_bookmarks() == {1: [1, 0], 2: [3, 5]}
    assert len(editor.blockuserdata_list) == 2

    editor.clear_bookmarks()
    assert editor.get_bookmarks() == {}
    # Even though there is a 'del data' that would pop the item from the
    # list, the __del__ funcion isn't called.
    assert len(editor.blockuserdata_list) == 2
    for data in editor.blockuserdata_list:
        assert not data.bookmarks


def test_update_bookmarks(code_editor_bot):
    """Test CodeEditor.update_bookmarks. Check if signal is emitted."""
    editor, _ = code_editor_bot
    reset_emits(editor)
    editor.bookmarks_changed.emit.assert_not_called()
    # update_bookmarks is the slot for the blockCountChanged signal.
    editor.textCursor().insertBlock()
    editor.bookmarks_changed.emit.assert_called_with()


def test_save_bookmark(setup_editor):
    """Test Plugin.save_bookmark.

    Test saving of bookmarks by looking at data in blocks. Reassignment
    should remove data from old block and put it in new.
    """
    editor = setup_editor

    editor.setup_open_files()

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


def test_load_bookmark(setup_editor, test_file):
    """Test that loading a bookmark works.

    Check this by saving and loading bookmarks and checking for cursor
    position. Also over multiple files.
    """
    editor = setup_editor

    editor.setup_open_files()

    # Get current editorstack, active editor and cursor
    editorstack = editor.get_current_editorstack()
    edtr = editorstack.get_current_editor()
    cursor = edtr.textCursor()

    # Basic functionality: save and load a bookmark and
    # check if the cursor is there.
    editor.save_bookmark(1)
    cursor.movePosition(QTextCursor.Down, n=2)
    cursor.movePosition(QTextCursor.Right, n=13)
    edtr.setTextCursor(cursor)

    editor.load_bookmark(1)

    assert edtr.get_cursor_line_column() == (0, 0)

    # Mover cursor to end of line and remove characters
    cursor = edtr.textCursor()
    cursor.movePosition(QTextCursor.Down, n=2)
    cursor.movePosition(QTextCursor.Right, n=13)
    edtr.setTextCursor(cursor)

    editor.save_bookmark(2)
    edtr.stdkey_backspace()
    editor.load_bookmark(2)

    assert edtr.get_cursor_line_column() == (2, 12)

    # Check if loading bookmark switches file correctly
    editorstack.load(test_file, set_current=True)
    editor.save_bookmark(2)
    editorstack.tabs.setCurrentIndex(0)
    editor.load_bookmark(2)
    assert editorstack.tabs.currentIndex() == 1


if __name__ == "__main__":
    pytest.main()
