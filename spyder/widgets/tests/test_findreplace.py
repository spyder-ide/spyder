# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
#

"""
Tests for pathmanager.py
"""
# Standard library imports
import os

# Test library imports
import pytest
from qtpy.QtGui import QFont
from qtpy.QtWidgets import QVBoxLayout, QWidget

# Local imports
from spyder.plugins.editor.widgets.codeeditor import CodeEditor
from spyder.widgets.findreplace import FindReplace
from spyder.utils.stylesheet import APP_STYLESHEET


@pytest.fixture
def findreplace_editor(qtbot, request):
    """Set up editor with FindReplace widget."""
    # Widget to show together the two other below
    widget = QWidget()
    qtbot.addWidget(widget)
    widget.setStyleSheet(str(APP_STYLESHEET))

    # Widget's layout
    layout = QVBoxLayout()
    widget.setLayout(layout)

    # Code editor
    editor = CodeEditor(parent=widget)
    editor.setup_editor(
        color_scheme='spyder/dark',
        font=QFont("Courier New", 10)
    )
    widget.editor = editor
    layout.addWidget(editor)

    # Find replace
    findreplace = FindReplace(editor, enable_replace=True)
    findreplace.set_editor(editor)
    widget.findreplace = findreplace
    layout.addWidget(findreplace)

    # Resize widget and show
    widget.resize(480, 360)
    widget.show()

    return widget


def test_findreplace_multiline_replacement(findreplace_editor, qtbot):
    """
    Test find replace widget for multiline regex replacements
    See: spyder-ide/spyder#2675
    """
    expected = '\n\nhello world!\n\n'
    editor = findreplace_editor.editor
    findreplace = findreplace_editor.findreplace
    editor.set_text('\n\nhello\n\n\nworld!\n\n')
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
    editor = findreplace_editor.editor
    findreplace = findreplace_editor.findreplace
    editor.set_text('Spyder as great!\nSpyder as great!')
    editor.select_lines(0, 2)
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
