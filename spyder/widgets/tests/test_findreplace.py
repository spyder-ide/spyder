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
from qtpy.QtCore import Qt
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


def test_messages_action(findreplace_editor, qtbot):
    """
    Test that we set the right icons and tooltips on messages_action.
    """
    editor = findreplace_editor.editor
    findreplace = findreplace_editor.findreplace
    editor.set_text('Spyder as great!')

    # Assert messages_action is not visible by default
    assert not findreplace.messages_action.isVisible()

    # Search for missing text
    edit = findreplace.search_text.lineEdit()
    edit.clear()
    qtbot.keyClicks(edit, 'foo')
    assert not findreplace.number_matches_text.isVisible()
    assert findreplace.messages_action.icon().cacheKey() == \
           findreplace.warning_icon.cacheKey()
    assert findreplace.messages_action.toolTip() == \
           findreplace.TOOLTIP['no_matches']

    # Assert messages_action is not visible when there's no text
    edit.selectAll()
    qtbot.keyClick(edit, Qt.Key_Delete)
    assert not findreplace.messages_action.isVisible()

    # Search with wrong regexp
    msg = ': nothing to repeat at position 0'
    edit.clear()
    findreplace.re_button.setChecked(True)
    qtbot.keyClicks(edit, '?')
    assert not findreplace.number_matches_text.isVisible()
    assert findreplace.messages_action.icon().cacheKey() == \
           findreplace.error_icon.cacheKey()
    assert findreplace.messages_action.toolTip() == \
           findreplace.TOOLTIP['regexp_error'] + msg

    # Search for available text
    edit.clear()
    qtbot.keyClicks(edit, 'great')
    qtbot.wait(500)
    assert not findreplace.messages_action.isVisible()
    assert findreplace.number_matches_text.isVisible()
    assert findreplace.number_matches_text.text() == '1 of 1'


def test_replace_button(findreplace_editor, qtbot):
    """
    Test that the replace button is checked when showing the replace row
    directly.
    """
    findreplace = findreplace_editor.findreplace
    findreplace.hide()
    findreplace.show(hide_replace=False)
    qtbot.wait(500)
    assert findreplace.replace_text_button.isChecked()


if __name__ == "__main__":
    pytest.main([os.path.basename(__file__)])
