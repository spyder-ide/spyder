# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
#

"""
Tests for editor.py
"""

# Standard library imports
import os
import os.path as osp
import sys
from unittest.mock import Mock, MagicMock

# Third party imports
import pytest
from flaky import flaky
from qtpy.QtCore import Qt
from qtpy.QtGui import QTextCursor
from qtpy.QtWidgets import QVBoxLayout, QWidget

# Local imports
from spyder.config.base import get_conf_path, running_in_ci
from spyder.plugins.editor.widgets.editor import EditorStack
from spyder.utils.stylesheet import APP_STYLESHEET
from spyder.widgets.findreplace import FindReplace


HERE = osp.abspath(osp.dirname(__file__))


# =============================================================================
# ---- Qt Test Fixtures
# =============================================================================
@pytest.fixture
def base_editor_bot(qtbot):
    editor_stack = EditorStack(None, [], False)
    editor_stack.set_find_widget(Mock())
    editor_stack.set_io_actions(Mock(), Mock(), Mock(), Mock())
    return editor_stack


@pytest.fixture
def editor_bot(base_editor_bot, mocker, qtbot):
    """
    Set up EditorStack with CodeEditor containing some Python code.
    The cursor is at the empty line below the code.
    The file in the editor is `foo.py` and has not been changed.
    Returns tuple with EditorStack and CodeEditor.
    """
    editor_stack = base_editor_bot
    text = ('a = 1\n'
            'print(a)\n'
            '\n'
            'x = 2')  # a newline is added at end
    finfo = editor_stack.new('foo.py', 'utf-8', text)
    finfo.newly_created = False
    editor_stack.autosave.file_hashes = {'foo.py': hash(text + '\n')}
    qtbot.addWidget(editor_stack)
    return editor_stack, finfo.editor


@pytest.fixture
def editor_find_replace_bot(base_editor_bot, qtbot):
    # Widget to show together the editor stack and findreplace ones together
    widget = QWidget()
    qtbot.addWidget(widget)
    widget.setStyleSheet(str(APP_STYLESHEET))

    # Widget's layout
    layout = QVBoxLayout()
    widget.setLayout(layout)

    editor_stack = base_editor_bot
    layout.addWidget(editor_stack)
    widget.editor_stack = editor_stack

    text = ('spam bacon\n'
            'spam sausage\n'
            'spam egg')
    finfo = editor_stack.new('spam.py', 'utf-8', text)
    widget.editor = finfo.editor

    find_replace = FindReplace(editor_stack, enable_replace=True)
    editor_stack.set_find_widget(find_replace)
    find_replace.set_editor(finfo.editor)
    widget.find_replace = find_replace
    layout.addWidget(find_replace)

    # Resize widget and show
    widget.resize(900, 360)
    widget.show()

    return widget


@pytest.fixture
def editor_cells_bot(base_editor_bot, qtbot):
    editor_stack = base_editor_bot
    text = ('# %%\n'
            '# 1 cell\n'
            '# print(1)\n'
            '# %%\n'
            '# 2 cell\n'
            '# print(2)\n'
            '# %%\n'
            '# 3 cell\n'
            '# print(3)\n')
    finfo = editor_stack.new('cells.py', 'utf-8', text)
    qtbot.addWidget(editor_stack)
    return editor_stack, finfo.editor


# =============================================================================
# ---- Tests
# =============================================================================
def test_find_number_matches(editor_find_replace_bot):
    """Test for number matches in find/replace."""
    editor = editor_find_replace_bot.editor
    finder = editor_find_replace_bot.find_replace

    finder.case_button.setChecked(True)
    text = ' test \nTEST \nTest \ntesT '
    editor.set_text(text)

    finder.search_text.add_text('test')
    finder.find(changed=False, forward=True, rehighlight=False,
                multiline_replace_check=False)
    editor_text = finder.number_matches_text.text()
    assert editor_text == '1 of 1'

    finder.search_text.add_text('fail')
    finder.find(changed=False, forward=True, rehighlight=False,
                multiline_replace_check=False)
    assert not finder.number_matches_text.isVisible()


def test_move_current_line_up(editor_bot):
    editor_stack, editor = editor_bot

    # Move second line up when nothing is selected.
    editor.go_to_line(2)
    editor.move_line_up()
    expected_new_text = ('print(a)\n'
                         'a = 1\n'
                         '\n'
                         'x = 2\n')
    assert editor.toPlainText() == expected_new_text

    # Move line up when already at the top.
    editor.move_line_up()
    assert editor.toPlainText() == expected_new_text

    # Move fourth line up when part of the line is selected.
    editor.go_to_line(4)
    editor.moveCursor(QTextCursor.Right, QTextCursor.MoveAnchor)
    for i in range(2):
        editor.moveCursor(QTextCursor.Right, QTextCursor.KeepAnchor)
    editor.move_line_up()
    expected_new_text = ('print(a)\n'
                         'a = 1\n'
                         'x = 2\n'
                         '\n')
    assert editor.toPlainText()[:] == expected_new_text


def test_move_current_line_down(editor_bot):
    editor_stack, editor = editor_bot

    # Move fourth line down when nothing is selected.
    editor.go_to_line(4)
    editor.move_line_down()
    expected_new_text = ('a = 1\n'
                         'print(a)\n'
                         '\n'
                         '\n'
                         'x = 2')
    assert editor.toPlainText() == expected_new_text

    # Move line down when already at the bottom.
    editor.move_line_down()
    assert editor.toPlainText() == expected_new_text

    # Move first line down when part of the line is selected.
    editor.go_to_line(1)
    editor.moveCursor(QTextCursor.Right, QTextCursor.MoveAnchor)
    for i in range(2):
        editor.moveCursor(QTextCursor.Right, QTextCursor.KeepAnchor)
    editor.move_line_down()
    expected_new_text = ('print(a)\n'
                         'a = 1\n'
                         '\n'
                         '\n'
                         'x = 2')
    assert editor.toPlainText() == expected_new_text


def test_move_multiple_lines_up(editor_bot):
    editor_stack, editor = editor_bot

    # Move second and third lines up.
    editor.go_to_line(2)
    cursor = editor.textCursor()
    cursor.movePosition(QTextCursor.Down, QTextCursor.KeepAnchor)
    cursor.movePosition(QTextCursor.Right, QTextCursor.KeepAnchor)
    editor.setTextCursor(cursor)
    editor.move_line_up()

    expected_new_text = ('print(a)\n'
                         '\n'
                         'a = 1\n'
                         'x = 2\n')
    assert editor.toPlainText() == expected_new_text

    # Move first and second lines up (to test already at top condition).
    editor.move_line_up()
    assert editor.toPlainText() == expected_new_text


@pytest.mark.skipif(not sys.platform.startswith('linux'),
                    reason="Works only on Linux")
def test_copy_lines_down_up(editor_bot, mocker, qtbot):
    """
    Test that copy lines down and copy lines up are working as expected.
    """
    editorstack, editor = editor_bot

    # We need to show the editor because the copy lines down and copy lines up
    # functionalities both rely on a paint event override to work as expected.
    editorstack.show()

    # We need to patch osp.isfile to avoid the 'this file does not exist'
    # message box.
    mocker.patch('spyder.plugins.editor.widgets.editor.osp.isfile',
                 returned_value=True)

    # Assert initial state.
    editorstack.go_to_line(1)
    assert editor.get_cursor_line_column() == (0, 0)

    # Select some text.
    cursor = editor.textCursor()
    cursor.movePosition(QTextCursor.Down, QTextCursor.KeepAnchor)
    cursor.movePosition(QTextCursor.Down, QTextCursor.KeepAnchor)
    editor.setTextCursor(cursor)
    assert editor.get_cursor_line_column() == (2, 0)
    assert editor.textCursor().selection().toPlainText() == 'a = 1\nprint(a)\n'

    # Copy lines down.
    editor.duplicate_line_down()
    qtbot.wait(100)
    assert editor.get_cursor_line_column() == (4, 0)
    assert editor.textCursor().selection().toPlainText() == 'a = 1\nprint(a)\n'
    assert editor.toPlainText() == 'a = 1\nprint(a)\n' * 2 + '\nx = 2\n'

    # Copy lines up.
    editor.duplicate_line_up()
    qtbot.wait(100)
    assert editor.get_cursor_line_column() == (4, 0)
    assert editor.textCursor().selection().toPlainText() == 'a = 1\nprint(a)\n'
    assert editor.toPlainText() == 'a = 1\nprint(a)\n' * 3 + '\nx = 2\n'


def test_move_multiple_lines_down(editor_bot):
    editor_stack, editor = editor_bot

    # Move third and fourth lines down.
    editor.go_to_line(3)
    cursor = editor.textCursor()
    cursor.movePosition(QTextCursor.Down, QTextCursor.KeepAnchor)
    cursor.movePosition(QTextCursor.Right, QTextCursor.KeepAnchor)
    editor.setTextCursor(cursor)
    editor.move_line_down()

    expected_new_text = ('a = 1\n'
                         'print(a)\n'
                         '\n'
                         '\n'
                         'x = 2')
    assert editor.toPlainText() == expected_new_text

    # Move fourht and fifth lines down (to test already at bottom condition).
    editor.move_line_down()
    assert editor.toPlainText() == expected_new_text


def test_run_top_line(editor_bot, qtbot):
    editor_stack, editor = editor_bot
    editor.go_to_line(1) # line number is one based
    editor.move_cursor(3)
    text, _, _, _ = editor_stack.get_selection()
    editor_stack.advance_line()
    assert text == 'a = 1'

    # check cursor moves to start of next line; note line number is zero based
    assert editor.get_cursor_line_column() == (1, 0)


def test_run_last_nonempty_line(editor_bot, qtbot):
    editor_stack, editor = editor_bot
    editor.go_to_line(4)
    text, _, _, _ = editor_stack.get_selection()
    editor_stack.advance_line()
    assert text == 'x = 2'
    assert editor.get_cursor_line_column() == (4, 0) # check cursor moves down


def test_run_empty_line_in_middle(editor_bot, qtbot):
    editor_stack, editor = editor_bot
    editor.go_to_line(3)
    _, _, _, _ = editor_stack.get_selection()
    editor_stack.advance_line()
    assert editor.get_cursor_line_column() == (3, 0) # check cursor moves down


def test_run_last_line_when_empty(editor_bot, qtbot):
    editor_stack, editor = editor_bot
    _, _, _, _ = editor_stack.get_selection()
    editor_stack.advance_line()
    # check cursor doesn't move
    assert editor.get_cursor_line_column() == (4, 0)


def test_run_last_line_when_nonempty(editor_bot, qtbot):
    editor_stack, editor = editor_bot
    editor.stdkey_backspace() # delete empty line at end
    old_text = editor.toPlainText()
    text, _, _, _ = editor_stack.get_selection()
    editor_stack.advance_line()
    assert text == 'x = 2'
    expected_new_text = old_text + editor.get_line_separator()
    # check blank line got added
    assert editor.toPlainText() == expected_new_text
    assert editor.get_cursor_line_column() == (4, 0) # check cursor moves down


def test_find_replace_case_sensitive(editor_find_replace_bot):
    editor = editor_find_replace_bot.editor
    finder = editor_find_replace_bot.find_replace

    finder.show(hide_replace=False)
    finder.case_button.setChecked(True)
    text = ' test \nTEST \nTest \ntesT '
    editor.set_text(text)
    finder.search_text.add_text('test')
    finder.replace_text.add_text('pass')
    finder.replace_find()
    finder.replace_find()
    finder.replace_find()
    finder.replace_find()
    editor_text = editor.toPlainText()
    assert editor_text == ' pass \nTEST \nTest \ntesT '


def test_replace_current_selected_line(editor_find_replace_bot, qtbot):
    editor = editor_find_replace_bot.editor
    finder = editor_find_replace_bot.find_replace

    expected_new_text = ('ham bacon\n'
                         'spam sausage\n'
                         'spam egg')

    finder.show(hide_replace=False)
    qtbot.keyClicks(finder.search_text, 'spam')
    qtbot.keyClicks(finder.replace_text, 'ham')
    qtbot.keyPress(finder.replace_text, Qt.Key_Return)
    assert editor.toPlainText()[0:-1] == expected_new_text


@pytest.mark.skipif(sys.platform.startswith('linux'), reason="Fails in Linux")
def test_replace_enter_press(editor_find_replace_bot, qtbot):
    """Test advance forward pressing Enter, and backwards with Shift+Enter."""
    editor = editor_find_replace_bot.editor
    finder = editor_find_replace_bot.find_replace

    text = '  \nspam \nspam \nspam '
    editor.set_text(text)
    finder.search_text.add_text('spam')
    finder.search_text.lineEdit().setFocus()

    # search forward
    qtbot.keyClick(finder.search_text.lineEdit(), Qt.Key_Return)
    assert editor.get_cursor_line_column() == (1,4)

    qtbot.keyClick(finder.search_text.lineEdit(), Qt.Key_Return)
    assert editor.get_cursor_line_column() == (2,4)

    qtbot.keyClick(finder.search_text.lineEdit(), Qt.Key_Return)
    assert editor.get_cursor_line_column() == (3,4)

    # search backwards
    qtbot.keyClick(finder.search_text.lineEdit(), Qt.Key_Return,
                   modifier=Qt.ShiftModifier)
    assert editor.get_cursor_line_column() == (2,4)

    qtbot.keyClick(finder.search_text.lineEdit(), Qt.Key_Return,
                   modifier=Qt.ShiftModifier)
    assert editor.get_cursor_line_column() == (1,4)

    qtbot.keyClick(finder.search_text.lineEdit(), Qt.Key_Return,
                   modifier=Qt.ShiftModifier)
    assert editor.get_cursor_line_column() == (3,4)


def test_replace_plain_regex(editor_find_replace_bot, qtbot):
    """Test that regex reserved characters are displayed as plain text."""
    editor = editor_find_replace_bot.editor
    finder = editor_find_replace_bot.find_replace

    expected_new_text = ('.\\[()]*test bacon\n'
                         'spam sausage\n'
                         'spam egg')
    finder.show(hide_replace=False)

    qtbot.keyClicks(finder.search_text, 'spam')
    qtbot.keyClicks(finder.replace_text, r'.\[()]*test')
    qtbot.keyPress(finder.replace_text, Qt.Key_Return)
    assert editor.toPlainText()[0:-1] == expected_new_text


def test_replace_invalid_regex(editor_find_replace_bot, qtbot):
    """Assert that replacing an invalid regexp does nothing."""
    editor = editor_find_replace_bot.editor
    finder = editor_find_replace_bot.find_replace

    old_text = editor.toPlainText()
    finder.show(hide_replace=False)

    # Test with invalid search_text and valid replace_text
    qtbot.keyClicks(finder.search_text, '\\')
    qtbot.keyClicks(finder.replace_text, 'anything')

    if not finder.re_button.isChecked():
        qtbot.mouseClick(finder.re_button, Qt.LeftButton)

    qtbot.mouseClick(finder.replace_button, Qt.LeftButton)
    assert editor.toPlainText() == old_text
    qtbot.mouseClick(finder.replace_sel_button, Qt.LeftButton)
    assert editor.toPlainText() == old_text
    qtbot.mouseClick(finder.replace_all_button, Qt.LeftButton)
    assert editor.toPlainText() == old_text

    # Test with valid search_text and invalid replace_text
    qtbot.keyClicks(finder.search_text, 'anything')
    qtbot.keyClicks(finder.replace_text, '\\')

    qtbot.mouseClick(finder.replace_button, Qt.LeftButton)
    assert editor.toPlainText() == old_text
    qtbot.mouseClick(finder.replace_sel_button, Qt.LeftButton)
    assert editor.toPlainText() == old_text
    qtbot.mouseClick(finder.replace_all_button, Qt.LeftButton)
    assert editor.toPlainText() == old_text


def test_replace_honouring_case(editor_find_replace_bot, qtbot):
    editor = editor_find_replace_bot.editor
    finder = editor_find_replace_bot.find_replace

    expected_new_text = ('Spam bacon\n'
                         'Spam sausage\n'
                         'Spam egg\n'
                         'Spam potatoes')
    qtbot.keyClicks(editor, 'SpaM potatoes')

    finder.show(hide_replace=False)
    qtbot.keyClicks(finder.search_text, 'Spa[a-z]')
    qtbot.keyClicks(finder.replace_text, 'Spam')

    # Make sure regex button is set
    if not finder.re_button.isChecked():
        qtbot.mouseClick(finder.re_button, Qt.LeftButton)

    # Make sure case button is not set
    if finder.case_button.isChecked():
        qtbot.mouseClick(finder.case_button, Qt.LeftButton)

    # Replace all
    qtbot.mouseClick(finder.replace_all_button, Qt.LeftButton)
    assert editor.toPlainText() == expected_new_text


def test_selection_escape_characters(editor_find_replace_bot, qtbot):
    editor = editor_find_replace_bot.editor
    finder = editor_find_replace_bot.find_replace

    expected_new_text = ('spam bacon\n'
                         'spam sausage\n'
                         'spam egg\n'
                         '\\n \\t some escape characters')
    qtbot.keyClicks(editor, '\\n \\t escape characters')

    finder.show(hide_replace=False)
    qtbot.keyClicks(finder.search_text, 'escape')
    qtbot.keyClicks(finder.replace_text, 'some escape')

    # Select last line
    cursor = editor.textCursor()
    cursor.select(QTextCursor.LineUnderCursor)
    assert cursor.selection().toPlainText() == "\\n \\t escape characters"

    # Replace
    finder.replace_find_selection()

    # Test that selection is correct
    assert cursor.selection().toPlainText() == "\\n \\t some escape characters"
    assert editor.toPlainText() == expected_new_text


def test_selection_backslash(editor_find_replace_bot, qtbot):
    editor = editor_find_replace_bot.editor
    finder = editor_find_replace_bot.find_replace

    expected_new_text = ('spam bacon\n'
                         'spam sausage\n'
                         'spam egg\n'
                         r'a = r"\left\{" + "\\}\\right\n"')
    text_to_add = 'a = r"\\leeft\\{" + "\\\\}\\\\right\\n"'
    qtbot.keyClicks(editor, text_to_add)

    finder.show(hide_replace=False)
    qtbot.keyClicks(finder.search_text, 'leeft')
    qtbot.keyClicks(finder.replace_text, 'left')

    # Select last line
    cursor = editor.textCursor()
    cursor.select(QTextCursor.LineUnderCursor)
    assert cursor.selection().toPlainText() == text_to_add

    # Replace
    finder.replace_find_selection()
    assert editor.toPlainText() == expected_new_text


def test_advance_cell(editor_cells_bot):
    editor_stack, editor = editor_cells_bot

    # cursor at the end of the file
    assert editor.get_cursor_line_column() == (10, 0)

    # advance backwards to the beginning of the 3rd cell
    editor_stack.advance_cell(reverse=True)
    assert editor.get_cursor_line_column() == (6, 0)

    # advance backwards to 2nd cell
    editor_stack.advance_cell(reverse=True)
    assert editor.get_cursor_line_column() == (3, 0)
    # advance backwards to 1st cell
    editor_stack.advance_cell(reverse=True)
    assert editor.get_cursor_line_column() == (0, 0)

    # advance to 2nd cell
    editor_stack.advance_cell()
    assert editor.get_cursor_line_column() == (3, 0)
    # advance to 3rd cell
    editor_stack.advance_cell()
    assert editor.get_cursor_line_column() == (6, 0)


def test_get_current_word(base_editor_bot, qtbot):
    """Test getting selected valid python word."""
    editor_stack = base_editor_bot
    text = ('some words with non-ascii  characters\n'
            'niño\n'
            'garçon\n'
            'α alpha greek\n'
            '123valid_python_word')
    finfo = editor_stack.new('foo.py', 'utf-8', text)
    qtbot.addWidget(editor_stack)
    editor = finfo.editor
    editor.go_to_line(1)

    # Select some
    editor.moveCursor(QTextCursor.EndOfWord, QTextCursor.KeepAnchor)
    assert 'some' == editor.textCursor().selectedText()
    assert editor.get_current_word() == 'some'

    # Select niño
    editor.go_to_line(2)
    editor.moveCursor(QTextCursor.EndOfWord, QTextCursor.KeepAnchor)
    assert 'niño' == editor.textCursor().selectedText()
    assert editor.get_current_word() == 'niño'

    # Select garçon
    editor.go_to_line(3)
    editor.moveCursor(QTextCursor.EndOfWord, QTextCursor.KeepAnchor)
    assert 'garçon' == editor.textCursor().selectedText()
    assert editor.get_current_word() == 'garçon'

    # Select α
    editor.go_to_line(4)
    editor.moveCursor(QTextCursor.EndOfWord, QTextCursor.KeepAnchor)
    assert 'α' == editor.textCursor().selectedText()
    assert editor.get_current_word() == 'α'

    # Select valid_python_word, should search first valid python word
    editor.go_to_line(5)
    editor.moveCursor(QTextCursor.EndOfWord, QTextCursor.KeepAnchor)
    assert '123valid_python_word' == editor.textCursor().selectedText()
    assert editor.get_current_word() == 'valid_python_word'


def test_tab_keypress_properly_caught_find_replace(editor_find_replace_bot,
                                                   qtbot):
    """
    Test that tab works in find/replace dialog.

    Regression test for spyder-ide/spyder#3674.
    Mock test—more isolated but less flimsy.
    """
    editor = editor_find_replace_bot.editor
    finder = editor_find_replace_bot.find_replace

    text = '  \nspam \nspam \nspam '
    editor.set_text(text)

    finder.focusNextChild = MagicMock(name="focusNextChild")
    qtbot.keyPress(finder.search_text, Qt.Key_Tab)
    finder.focusNextChild.assert_called_once_with()


@flaky(max_runs=3)
@pytest.mark.skipif(sys.platform.startswith('linux'), reason="Fails on Linux")
def test_tab_moves_focus_from_search_to_replace(editor_find_replace_bot,
                                                qtbot):
    """
    Test that tab works in find/replace dialog.

    Regression test for spyder-ide/spyder#3674.
    "Real world" test—more comprehensive but potentially less robust.
    """
    editor = editor_find_replace_bot.editor
    finder = editor_find_replace_bot.find_replace

    text = '  \nspam \nspam \nspam '
    editor.set_text(text)
    finder.show(hide_replace=False)

    qtbot.wait(100)
    finder.search_text.setFocus()
    qtbot.wait(100)
    assert finder.search_text.hasFocus()
    assert not finder.replace_text.hasFocus()
    qtbot.keyPress(finder.search_text, Qt.Key_Tab)
    qtbot.wait(100)
    assert not finder.search_text.hasFocus()
    assert finder.replace_text.hasFocus()


@flaky(max_runs=3)
@pytest.mark.skipif(running_in_ci(), reason="Fails on CIs")
def test_tab_copies_find_to_replace(editor_find_replace_bot, qtbot):
    """Check that text in the find box is copied to the replace box on tab
    keypress. Regression test spyder-ide/spyder#4482."""
    finder = editor_find_replace_bot.find_replace

    finder.show(hide_replace=False)
    finder.search_text.setFocus()
    finder.search_text.set_current_text('This is some test text!')
    qtbot.wait(500)
    qtbot.keyClick(finder.search_text, Qt.Key_Tab)
    assert finder.replace_text.currentText() == 'This is some test text!'


def test_update_matches_in_find_replace(editor_find_replace_bot, qtbot):
    """
    Check that the total number of matches in the FindReplace widget is updated
    when switching files.
    """
    editor_stack = editor_find_replace_bot.editor_stack
    finder = editor_find_replace_bot.find_replace

    # Search for "spam" in current file
    finder.show(hide_replace=False)
    finder.search_text.setFocus()
    finder.search_text.set_current_text('spam')
    qtbot.wait(500)
    qtbot.keyClick(finder.search_text, Qt.Key_Return)

    # Open a new file and only write "spam" on it
    editor_stack.new('foo.py', 'utf-8', 'spam')

    # Focus new file and check the number of matches was updated
    editor_stack.set_stack_index(1)
    assert finder.number_matches_text.text() == '1 matches'
    qtbot.wait(500)

    # Focus initial file and check the number of matches was updated
    editor_stack.set_stack_index(0)
    qtbot.wait(500)
    assert finder.number_matches_text.text() == '3 matches'


def test_autosave_all(editor_bot, mocker):
    """
    Test that `autosave_all()` calls maybe_autosave() on all open buffers.

    The `editor_bot` fixture is constructed with one open file and the test
    opens another one with `new()`, so maybe_autosave should be called twice.
    """
    editor_stack, editor = editor_bot
    editor_stack.new('ham.py', 'utf-8', '')
    mocker.patch.object(editor_stack.autosave, 'maybe_autosave')
    editor_stack.autosave.autosave_all()
    expected_calls = [mocker.call(0), mocker.call(1)]
    actual_calls = editor_stack.autosave.maybe_autosave.call_args_list
    assert actual_calls == expected_calls


def test_maybe_autosave(editor_bot):
    """
    Test that maybe_autosave() saves text to correct autosave file if contents
    are changed.
    """
    editor_stack, editor = editor_bot
    editor.set_text('spam\n')
    editor_stack.autosave.maybe_autosave(0)
    autosave_filename = os.path.join(get_conf_path('autosave'), 'foo.py')
    assert open(autosave_filename).read() == 'spam\n'
    os.remove(autosave_filename)


def test_maybe_autosave_saves_only_if_changed(editor_bot, mocker):
    """
    Test that maybe_autosave() only saves text if text has changed.

    The `editor_bot` fixture creates a clean editor, so the first call to
    `maybe_autosave()` should not autosave. After call #2 we change the text,
    so call #2 should autosave. The text is not changed after call #2, so
    call #3 should not autosave.
    """
    editor_stack, editor = editor_bot
    mocker.patch.object(editor_stack, '_write_to_file')
    editor_stack.autosave.maybe_autosave(0)  # call #1, should not write
    assert editor_stack._write_to_file.call_count == 0
    editor.set_text('ham\n')
    editor_stack.autosave.maybe_autosave(0)  # call #2, should write
    assert editor_stack._write_to_file.call_count == 1
    editor_stack.autosave.maybe_autosave(0)  # call #3, should not write
    assert editor_stack._write_to_file.call_count == 1


def test_maybe_autosave_does_not_save_new_files(editor_bot, mocker):
    """Test that maybe_autosave() does not save newly created files."""
    editor_stack, editor = editor_bot
    editor_stack.data[0].newly_created = True
    mocker.patch.object(editor_stack, '_write_to_file')
    editor_stack.autosave.maybe_autosave(0)
    editor_stack._write_to_file.assert_not_called()


def test_opening_sets_file_hash(base_editor_bot, mocker):
    """Test that opening a file sets the file hash."""
    editor_stack = base_editor_bot
    mocker.patch('spyder.plugins.editor.widgets.editor.encoding.read',
                 return_value=('my text', 42))
    filename = osp.realpath('/mock-filename')
    editor_stack.load(filename)
    expected = {filename: hash('my text')}
    assert editor_stack.autosave.file_hashes == expected


def test_reloading_updates_file_hash(base_editor_bot, mocker):
    """Test that reloading a file updates the file hash."""
    editor_stack = base_editor_bot
    mocker.patch('spyder.plugins.editor.widgets.editor.encoding.read',
                 side_effect=[('my text', 42), ('new text', 42)])
    filename = osp.realpath('/mock-filename')
    finfo = editor_stack.load(filename)
    index = editor_stack.data.index(finfo)
    editor_stack.reload(index)
    expected = {filename: hash('new text')}
    assert editor_stack.autosave.file_hashes == expected


def test_closing_removes_file_hash(base_editor_bot, mocker):
    """Test that closing a file removes the file hash."""
    editor_stack = base_editor_bot
    mocker.patch('spyder.plugins.editor.widgets.editor.encoding.read',
                 return_value=('my text', 42))
    filename = osp.realpath('/mock-filename')
    finfo = editor_stack.load(filename)
    index = editor_stack.data.index(finfo)
    editor_stack.close_file(index)
    assert editor_stack.autosave.file_hashes == {}


@pytest.mark.parametrize('filename', ['ham.py', 'ham.txt'])
def test_maybe_autosave_does_not_save_after_open(base_editor_bot, mocker,
                                                 qtbot, filename):
    """
    Test that maybe_autosave() does not save files immediately after opening.

    Files should only be autosaved after the user made changes.
    Editors use different highlighters depending on the filename, so we test
    both Python and text files. The latter covers spyder-ide/spyder#8654.
    """
    editor_stack = base_editor_bot
    mocker.patch('spyder.plugins.editor.widgets.editor.encoding.read',
                 return_value=('spam\n', 42))
    editor_stack.load(filename)
    mocker.patch.object(editor_stack, '_write_to_file')
    qtbot.wait(100)  # Wait for PygmentsSH.makeCharlist() if applicable
    editor_stack.autosave.maybe_autosave(0)
    editor_stack._write_to_file.assert_not_called()


def test_maybe_autosave_does_not_save_after_reload(base_editor_bot, mocker):
    """
    Test that maybe_autosave() does not save files immediately after reloading.

    Spyder reloads the file if it has changed on disk. In that case, there is
    no need to autosave because the contents in Spyder are identical to the
    contents on disk.
    """
    editor_stack = base_editor_bot
    txt = 'spam\n'
    editor_stack.create_new_editor('ham.py', 'ascii', txt, set_current=True)
    mocker.patch.object(editor_stack, '_write_to_file')
    mocker.patch('spyder.plugins.editor.widgets.editor.encoding.read',
                 return_value=(txt, 'ascii'))
    editor_stack.reload(0)
    editor_stack.autosave.maybe_autosave(0)
    editor_stack._write_to_file.assert_not_called()

def test_autosave_updates_name_mapping(editor_bot, mocker, qtbot):
    """Test that maybe_autosave() updates name_mapping."""
    editor_stack, editor = editor_bot
    assert editor_stack.autosave.name_mapping == {}
    mocker.patch.object(editor_stack, '_write_to_file')
    editor.set_text('spam\n')
    editor_stack.autosave.maybe_autosave(0)
    expected = {'foo.py': os.path.join(get_conf_path('autosave'), 'foo.py')}
    assert editor_stack.autosave.name_mapping == expected


def test_maybe_autosave_handles_error(editor_bot, mocker):
    """Test that autosave() ignores errors when writing to file."""
    editor_stack, editor = editor_bot
    mock_write = mocker.patch.object(editor_stack, '_write_to_file')
    mock_dialog = mocker.patch(
        'spyder.plugins.editor.utils.autosave.AutosaveErrorDialog')
    try:
        mock_write.side_effect = PermissionError
    except NameError:  # Python 2
        mock_write.side_effect = IOError
    editor.set_text('spam\n')
    editor_stack.autosave.maybe_autosave(0)
    assert mock_dialog.called


def test_remove_autosave_file(editor_bot, mocker, qtbot):
    """
    Test that remove_autosave_file() removes the autosave file.

    Also, test that it updates `name_mapping`.
    """
    editor_stack, editor = editor_bot
    autosave = editor_stack.autosave
    editor.set_text('spam\n')

    autosave.maybe_autosave(0)

    autosave_filename = os.path.join(get_conf_path('autosave'), 'foo.py')
    assert os.access(autosave_filename, os.R_OK)
    expected = {'foo.py': autosave_filename}
    assert autosave.name_mapping == expected

    autosave.remove_autosave_file(editor_stack.data[0].filename)

    assert not os.access(autosave_filename, os.R_OK)
    assert autosave.name_mapping == {}


def test_ipython_files(base_editor_bot, qtbot):
    """Test support for IPython files in the editor."""
    # Load IPython file
    editor_stack = base_editor_bot
    editor_stack.load(osp.join(HERE, 'assets', 'ipython_file.ipy'))

    editor = editor_stack.get_current_editor()
    editor.completions_available = True

    # Assert file is recognized as IPython
    assert editor.is_ipython()

    # Assert we transform IPython cells to valid Python code when opening
    # the file
    with qtbot.waitSignal(editor.sig_perform_completion_request) as blocker:
        editor.document_did_open()

    request_params = blocker.args[2]
    assert 'get_ipython' in request_params['text']

    # Assert we transform IPython cells to valid Python code when modifying
    # the file
    with qtbot.waitSignal(editor.sig_perform_completion_request) as blocker:
        editor.document_did_change()

    params = blocker.args[2]
    assert 'get_ipython' in params['text']

    # Mock linting results for this file. This is actually what's returned by
    # Pyflakes.
    editor._diagnostics = [
        {
            'source': 'pyflakes',
            'range': {
                'start': {'line': 8, 'character': 0},
                'end': {'line': 8, 'character': 19}
            },
            'message': "'numpy as np' imported but unused", 'severity': 2
        },
        {
            'source': 'pyflakes',
            'range': {
                'start': {'line': 11, 'character': 0},
                'end': {'line': 11, 'character': 47}
            },
            'message': "undefined name 'get_ipython'", 'severity': 1
        }
    ]

    # Setting them in the editor
    editor.set_errors()

    # Measure how many blocks have attached linting data to them
    blocks_with_data = 0
    block = editor.document().firstBlock()
    while block.isValid():
        data = block.userData()
        if data and data.code_analysis:
            blocks_with_data += 1
        block = block.next()

    # Assert we omitted the get_ipython message from linting
    assert blocks_with_data == 1


if __name__ == "__main__":
    pytest.main(['test_editor.py'])
