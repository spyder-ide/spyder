# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
#

"""
Tests for codeeditor.py.
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
from qtpy.QtCore import QMimeData, QUrl
from qtpy.QtWidgets import QApplication

# Local imports
from spyder import version_info
import spyder.plugins.editor.widgets.codeeditor as codeeditor


@pytest.fixture
def code_editor_bot(qtbot):
    """Create code editor with default Python code."""
    editor = codeeditor.CodeEditor(parent=None)
    indent_chars = ' ' * 4
    tab_stop_width_spaces = 4
    editor.setup_editor(language='Python', indent_chars=indent_chars,
                        tab_stop_width_spaces=tab_stop_width_spaces)
    # Mock the screen updates and signal emits to test when they've been
    # called.
    editor.linenumberarea = Mock()
    if version_info > (4, ):
        editor.sig_flags_changed = Mock()
    else:
        editor.get_linenumberarea_width = Mock(return_value=1)
    editor.breakpoints_changed = Mock()
    return editor, qtbot


@pytest.mark.usefixtures("create_folders_files")
@pytest.fixture
def copy_files_clipboard(create_folders_files):
    """Fixture to copy files/folders into the clipboard"""
    def _paste(data_type='text'):
        file_content = QMimeData()
        if data_type == 'files':
            data = create_folders_files[0]
            file_content.setUrls([QUrl.fromLocalFile(fname) for fname in data])
        elif data_type == 'text':
            data = 'First line.\nSecond line.\nThird line.'
            file_content.setText(data)
        cb = QApplication.clipboard()
        cb.setMimeData(file_content, mode=cb.Clipboard)
        return data
    return _paste


# --- Tests
# -----------------------------------------------------------------------------
def test_delete(code_editor_bot, mocker):
    """Test CodeEditor.delete()."""
    editor, qtbot = code_editor_bot
    text = ('def f1(a, b):\n')
    editor.set_text(text)

    # Move to start and delete next character without selection.
    cursor = editor.textCursor()
    cursor.movePosition(QTextCursor.Start)
    editor.setTextCursor(cursor)
    editor.delete()
    assert editor.get_text_line(0) == 'ef f1(a, b):'

    # Delete selection.
    cursor = editor.textCursor()
    cursor.select(QTextCursor.WordUnderCursor)
    editor.setTextCursor(cursor)
    editor.delete()
    assert editor.get_text_line(0) == ' f1(a, b):'

    # Move to end of document - nothing to delete after cursor.
    cursor = editor.textCursor()
    cursor.movePosition(QTextCursor.End)
    editor.setTextCursor(cursor)
    editor.delete()
    assert editor.get_text_line(0) == ' f1(a, b):'


@pytest.mark.parametrize('data_type', ['files', 'text'])
def test_paste(code_editor_bot, copy_files_clipboard, data_type):
    """Test CodeEditor.paste() from clipboard files/folders as paths."""
    editor = code_editor_bot[0]

    def _editor_fun():
        """CodeEditor function call."""
        cursor = editor.textCursor()
        cursor.movePosition(QTextCursor.Start)
        editor.setTextCursor(cursor)
        editor.paste()

    # Paste clipboard data which contains a file as its path into the editor.
    if data_type == 'files':
        file_paths = copy_files_clipboard(data_type='files')
        _editor_fun()
        editor.selectAll()
        text = editor.toPlainText()
        path_list_in_editor = [path.strip(',"') for path in text.splitlines()]
        assert len(file_paths) == len(path_list_in_editor)
        for path, expected_path in zip(path_list_in_editor, file_paths):
            assert osp.normpath(path) == osp.normpath(expected_path)

    # Paste clipboard data which contains normal text.
    elif data_type == 'text':
        org_text = copy_files_clipboard(data_type='text')
        _editor_fun()
        for line_no, text in enumerate(org_text.splitlines()):
            assert editor.get_text_line(line_no) == text


if __name__ == "__main__":
    pytest.main()
