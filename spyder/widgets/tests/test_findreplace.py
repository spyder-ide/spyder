# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
#

"""
Tests for pathmanager.py
"""
# Standard library imports
import sys
import os

# Test library imports
import pytest
from qtpy.QtCore import Qt, QTimer
from qtpy.QtWidgets import QMessageBox, QPushButton

# Local imports
from spyder.plugins.editor.widgets.codeeditor import CodeEditor
from spyder.widgets.findreplace import FindReplace


@pytest.fixture
def findreplace_editor(qtbot, request):
    """Set up PathManager."""
    editor = CodeEditor()
    editor.setup_editor()
    widget = FindReplace(None)
    widget.set_editor(editor)
    qtbot.addWidget(widget)
    qtbot.addWidget(editor)
    return widget, editor


def test_findreplace_multiline_replacement(findreplace_editor, qtbot):
    """
    Test find replace widget for multiline regex replacements
    See: spyder-ide/spyder#2675
    """
    expected = '\n\nhello world!\n\n'
    findreplace, editor = findreplace_editor
    editor.set_text('\n\nhello\n\n\nworld!\n\n')
    editor.show()

    findreplace.show()
    findreplace.show_replace()

    findreplace.re_button.setChecked(True)
    edit = findreplace.search_text.lineEdit()
    edit.clear()
    edit.setText('\\n\\n\\n')
    findreplace.replace_text.setCurrentText(' ')
    qtbot.wait(1000)
    findreplace.replace_find_all()
    qtbot.wait(1000)
    assert editor.toPlainText() == expected


def test_replace_selection(findreplace_editor, qtbot):
    """Test find replace final selection in the editor.
    For further information see spyder-ide/spyder#12745
    """
    expected = 'Spyder is greit!\nSpyder is greit!'

    findreplace, editor = findreplace_editor
    editor.set_text('Spyder as great!\nSpyder as great!')
    editor.show()
    editor.select_lines(0, 2)

    findreplace.show()
    findreplace.show_replace()

    edit = findreplace.search_text.lineEdit()
    edit.clear()
    edit.setText('a')

    findreplace.replace_text.setCurrentText('i')
    findreplace.replace_find_selection()
    qtbot.wait(1000)
    assert editor.get_selected_text() == expected
    assert len(editor.get_selected_text()) == len(expected)


if __name__ == "__main__":
    pytest.main([os.path.basename(__file__)])
