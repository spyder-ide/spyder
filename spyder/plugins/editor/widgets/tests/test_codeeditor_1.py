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
def test_format_signature(code_editor_bot):
    """Test signature format method."""
    signature = """
    concatenate((a1, a2, a...), [b1, b2, b...], axis={}, index=[],
                *args, **kargs)"""
    editor, qtbot = code_editor_bot

    format_signature = editor._format_signature(signature, parameter="(a1")

    assert "color:#DAA520'><b>a1</b></span>" in format_signature

    format_signature = editor._format_signature(signature, parameter="a2")
    assert "color:#DAA520'><b>a2</b></span>" in format_signature

    format_signature = editor._format_signature(signature, parameter="a...")
    print(format_signature)
    assert "color:#DAA520'><b>a...</b></span>" in format_signature

    format_signature = editor._format_signature(signature, parameter="[b1")
    assert "color:#DAA520'><b>b1</b></span>" in format_signature

    format_signature = editor._format_signature(signature, parameter="b2")
    assert "color:#DAA520'><b>b2</b></span>" in format_signature

    format_signature = editor._format_signature(signature, parameter="b...")
    assert "color:#DAA520'><b>b...</b></span>" in format_signature

    format_signature = editor._format_signature(signature, parameter="axis")
    assert "color:#DAA520'><b>axis</b></span>" in format_signature

    format_signature = editor._format_signature(signature, parameter="index")
    assert "color:#DAA520'><b>index</b></span>" in format_signature

    format_signature = editor._format_signature(signature, parameter="*args")
    assert "color:#DAA520'><b>*args</b></span>" in format_signature

    format_signature = editor._format_signature(signature, parameter="**kargs")
    assert "color:#DAA520'><b>**kargs</b></span>" in format_signature


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
