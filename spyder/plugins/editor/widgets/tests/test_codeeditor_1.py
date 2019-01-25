# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
#

"""
Tests for codeeditor.py.
"""

try:
    from unittest.mock import Mock
except ImportError:
    from mock import Mock  # Python 2
import os.path as osp

# Third party imports
import pytest
from qtpy.QtGui import QTextCursor
from qtpy.QtCore import QMimeData, QUrl
from qtpy.QtWidgets import QApplication

# Local imports
from spyder import version_info
import spyder.plugins.editor.widgets.codeeditor as codeeditor
from spyder.py3compat import to_text_string


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


def test_paste(code_editor_bot, tmpdir):
    """Test CodeEditor.paste()."""
    editor = code_editor_bot[0]

    # Copy a file into the clipboard.
    temp_directory = to_text_string(tmpdir.mkdir('folder'))
    tmpfile = osp.join(temp_directory, 'script.py')
    with open(tmpfile, 'w') as fh:
        fh.write('def f1(a, b):\n')
    file_content = QMimeData()
    file_content.setUrls([QUrl.fromLocalFile(tmpfile)])
    cb = QApplication.clipboard()
    cb.setMimeData(file_content, mode=cb.Clipboard)

    # Paste clipboard data which contains a file as its path into the editor.
    cursor = editor.textCursor()
    cursor.movePosition(QTextCursor.Start)
    editor.setTextCursor(cursor)
    editor.paste()
    assert osp.exists(tmpfile)
    assert editor.get_text_line(0) == tmpfile.replace(osp.os.sep, '/')

    # Paste clipboard data which contains normal text.
    with open(tmpfile, 'r') as fh:
        text = fh.read()
    cb.setText(text, mode=cb.Clipboard)
    cursor = editor.textCursor()
    cursor.movePosition(QTextCursor.Start)
    editor.setTextCursor(cursor)
    editor.paste()
    assert editor.get_text_line(0) == 'def f1(a, b):'


if __name__ == "__main__":
    pytest.main()
