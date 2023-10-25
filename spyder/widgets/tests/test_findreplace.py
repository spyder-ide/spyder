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
from qtpy.QtGui import QFont, QTextCursor
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
    widget.resize(900, 360)
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
           findreplace.no_matches_icon.cacheKey()
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


def test_replace_text_button(findreplace_editor, qtbot):
    """
    Test that replace_text_button is checked/unchecked under different
    scenarios.
    """
    findreplace = findreplace_editor.findreplace
    findreplace.hide()

    # Show replace row directly
    findreplace.show(hide_replace=False)
    qtbot.wait(500)
    assert findreplace.replace_text_button.isChecked()

    # Hide with the close button and show find row only
    qtbot.mouseClick(findreplace.close_button, Qt.LeftButton)
    findreplace.show(hide_replace=True)
    qtbot.wait(500)
    assert not findreplace.replace_text_button.isChecked()

    # Show both find and replace rows and then only the find one
    findreplace.show(hide_replace=False)
    qtbot.wait(500)
    findreplace.show(hide_replace=True)
    assert not findreplace.replace_text_button.isChecked()


def test_update_matches(findreplace_editor, qtbot):
    """
    Test that we update the total number of matches when the editor text has
    changed.
    """
    editor = findreplace_editor.editor
    findreplace = findreplace_editor.findreplace
    editor.set_text('foo\nfoo\n')

    # Search for present text
    edit = findreplace.search_text.lineEdit()
    edit.clear()
    edit.setFocus()
    qtbot.keyClicks(edit, 'foo')
    assert findreplace.number_matches_text.text() == '1 of 2'

    # Add the same text and check matches were updated
    editor.setFocus()
    cursor = editor.textCursor()
    cursor.movePosition(QTextCursor.End)
    editor.setTextCursor(cursor)
    qtbot.keyClicks(editor, 'foo')
    qtbot.wait(500)
    assert findreplace.number_matches_text.text() == '3 matches'

    # Assert found results are highlighted in the editor
    assert len(editor.found_results) == 3

    # Check we don't update matches when the widget is hidden
    findreplace.hide()
    qtbot.wait(500)
    qtbot.keyClick(editor, Qt.Key_Return)
    qtbot.keyClicks(editor, 'foo')
    qtbot.wait(500)
    assert findreplace.number_matches_text.text() == '3 matches'


def test_clear_action(findreplace_editor, qtbot):
    """
    Test that clear_action in the search_text line edit is working as expected.
    """
    editor = findreplace_editor.editor
    findreplace = findreplace_editor.findreplace
    clear_action = findreplace.search_text.clear_action
    editor.set_text('foo\nfoo\n')

    # clear_action should not be visible when the widget is shown
    assert not clear_action.isVisible()

    # Search for some existing text and check clear_action is visible
    edit = findreplace.search_text.lineEdit()
    edit.setFocus()
    qtbot.keyClicks(edit, 'foo')
    assert clear_action.isVisible()
    qtbot.wait(500)

    # Trigger clear_action and assert it's hidden, along with
    # number_matches_text
    clear_action.triggered.emit()
    assert not clear_action.isVisible()
    assert not findreplace.number_matches_text.isVisible()

    # Search for unexisting text
    edit.clear()
    edit.setFocus()
    qtbot.keyClicks(edit, 'bar')
    qtbot.wait(500)
    assert findreplace.messages_action.isVisible()

    # Trigger clear_action and assert messages_action is hidden
    clear_action.triggered.emit()
    qtbot.wait(500)
    assert not findreplace.messages_action.isVisible()


def test_replace_all_backslash(findreplace_editor, qtbot):
    """
    Test that we can replace all occurrences of a certain text with an
    expression that contains backslashes.

    This is a regression test for issue spyder-ide/spyder#21007
    """
    editor = findreplace_editor.editor
    findreplace = findreplace_editor.findreplace

    # Replace all instances of | by \
    editor.set_text("a | b | c")
    edit = findreplace.search_text.lineEdit()
    edit.setFocus()
    qtbot.keyClicks(edit, '|')

    findreplace.replace_text_button.setChecked(True)
    findreplace.replace_text.setCurrentText('\\')
    qtbot.wait(100)
    findreplace.replace_find_all()
    assert editor.toPlainText() == "a \\ b \\ c"

    # Clear editor and edit
    editor.selectAll()
    qtbot.keyClick(edit, Qt.Key_Delete)
    edit.clear()

    # Replace all instances of \alpha by \beta
    editor.set_text("\\Psi\n\\alpha\n\\beta\n\\alpha")
    edit.setFocus()
    qtbot.keyClicks(edit, "\\alpha")

    findreplace.replace_text.setCurrentText('\\beta')
    qtbot.wait(100)
    findreplace.replace_find_all()
    assert editor.toPlainText() == "\\Psi\n\\beta\n\\beta\n\\beta"


if __name__ == "__main__":
    pytest.main([os.path.basename(__file__)])
