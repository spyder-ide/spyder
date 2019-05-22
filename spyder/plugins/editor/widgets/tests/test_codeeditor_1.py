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


@pytest.mark.usefixtures("create_folders_files")
@pytest.fixture
def copy_files_clipboard(create_folders_files):
    """Fixture to copy files/folders into the clipboard"""
    file_paths = create_folders_files[0]
    file_content = QMimeData()
    file_content.setUrls([QUrl.fromLocalFile(fname) for fname in file_paths])
    cb = QApplication.clipboard()
    cb.setMimeData(file_content, mode=cb.Clipboard)
    return file_paths


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


def test_paste_files(code_editor_bot, copy_files_clipboard):
    """Test pasting files/folders into the editor."""
    editor = code_editor_bot[0]
    file_paths = copy_files_clipboard
    cursor = editor.textCursor()
    cursor.movePosition(QTextCursor.Start)
    editor.setTextCursor(cursor)
    editor.paste()
    editor.selectAll()
    text = editor.toPlainText()
    path_list_in_editor = [path.strip(',"') for path in text.splitlines()]
    assert len(file_paths) == len(path_list_in_editor)
    for path, expected_path in zip(path_list_in_editor, file_paths):
        assert osp.normpath(path) == osp.normpath(expected_path)


@pytest.mark.parametrize('line_ending_char', ['\n', '\r\n', '\r'])
@pytest.mark.parametrize('text', ['def fun(a, b):\n\treturn a + b',
                                  'https://www.spyder-ide.org'])
def test_paste_text(code_editor_bot, text, line_ending_char):
    """Test pasting text into the editor."""
    editor = code_editor_bot[0]
    text = text.replace(osp.os.linesep, line_ending_char)
    cb = QApplication.clipboard()
    cb.setText(text, mode=cb.Clipboard)
    cursor = editor.textCursor()
    cursor.movePosition(QTextCursor.Start)
    editor.setTextCursor(cursor)
    editor.paste()
    for line_no, txt in enumerate(text.splitlines()):
        assert editor.get_text_line(line_no) == txt


if __name__ == "__main__":
    pytest.main()
