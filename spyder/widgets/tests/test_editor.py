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
from sys import platform
try:
    from unittest.mock import Mock, MagicMock
except ImportError:
    from mock import Mock, MagicMock  # Python 2

# Third party imports
import pytest
from flaky import flaky
from qtpy.QtCore import Qt
from qtpy.QtGui import QTextCursor

# Local imports
from spyder.utils.fixtures import setup_editor
from spyder.widgets.editor import EditorStack, EditorSplitter
from spyder.widgets.findreplace import FindReplace
from spyder.py3compat import PY2

# Qt Test Fixtures
#--------------------------------
@pytest.fixture
def base_editor_bot(qtbot):
    editor_stack = EditorStack(None, [])
    editor_stack.set_introspector(Mock())
    editor_stack.set_find_widget(Mock())
    editor_stack.set_io_actions(Mock(), Mock(), Mock(), Mock())
    return editor_stack, qtbot

@pytest.fixture
def editor_bot(base_editor_bot):
    """
    Set up EditorStack with CodeEditor containing some Python code.
    The cursor is at the empty line below the code.
    Returns tuple with EditorStack and CodeEditor.
    """
    editor_stack, qtbot = base_editor_bot
    text = ('a = 1\n'
            'print(a)\n'
            '\n'
            'x = 2')  # a newline is added at end
    finfo = editor_stack.new('foo.py', 'utf-8', text)
    qtbot.addWidget(editor_stack)
    return editor_stack, finfo.editor, qtbot

@pytest.fixture
def editor_find_replace_bot(base_editor_bot):
    editor_stack, qtbot = base_editor_bot
    text = ('spam bacon\n'
            'spam sausage\n'
            'spam egg')
    finfo = editor_stack.new('spam.py', 'utf-8', text)
    find_replace = FindReplace(None, enable_replace=True)
    editor_stack.set_find_widget(find_replace)
    find_replace.set_editor(finfo.editor)
    qtbot.addWidget(editor_stack)
    return editor_stack, finfo.editor, find_replace, qtbot

@pytest.fixture
def editor_cells_bot(base_editor_bot):
    editor_stack, qtbot = base_editor_bot
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
    find_replace = FindReplace(None, enable_replace=True)
    qtbot.addWidget(editor_stack)
    return editor_stack, finfo.editor, qtbot


@pytest.fixture
def editor_folding_bot(base_editor_bot):
    """
    Setup CodeEditor with some text useful for folding related tests.
    """
    editor_stack, qtbot = base_editor_bot
    text = ('# dummy test file\n'
            'class a():\n'  # fold-block level-0
            '    self.b = 1\n'
            '    print(self.b)\n'
            '    \n'
            )
    finfo = editor_stack.new('foo.py', 'utf-8', text)

    find_replace = FindReplace(None, enable_replace=True)
    editor_stack.set_find_widget(find_replace)
    find_replace.set_editor(finfo.editor)
    qtbot.addWidget(editor_stack)
    return editor_stack, finfo.editor, find_replace, qtbot


# Tests
#-------------------------------
def test_find_number_matches(qtbot):
    """Test for number matches in find/replace."""
    editor_stack, editor = setup_editor(qtbot)
    editor_stack.find_widget.case_button.setChecked(True)
    text = ' test \nTEST \nTest \ntesT '
    editor.set_text(text)

    editor_stack.find_widget.search_text.add_text('test')
    editor_stack.find_widget.find(changed=False, forward=True,
                                  rehighlight=False,
                                  multiline_replace_check=False)
    editor_text = editor_stack.find_widget.number_matches_text.text()
    assert editor_text == '1 of 1'

    editor_stack.find_widget.search_text.add_text('fail')
    editor_stack.find_widget.find(changed=False, forward=True,
                                  rehighlight=False,
                                  multiline_replace_check=False)
    editor_text = editor_stack.find_widget.number_matches_text.text()
    assert editor_text == 'no matches'


def test_move_current_line_up(editor_bot):
    editor_stack, editor, qtbot = editor_bot
        
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
    editor_stack, editor, qtbot = editor_bot
        
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
    editor_stack, editor, qtbot = editor_bot
    
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

def test_move_multiple_lines_down(editor_bot):
    editor_stack, editor, qtbot = editor_bot
    
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
    
def test_run_top_line(editor_bot):
    editor_stack, editor, qtbot = editor_bot
    editor.go_to_line(1) # line number is one based
    editor.move_cursor(3)
    with qtbot.waitSignal(editor_stack.exec_in_extconsole) as blocker:
        editor_stack.run_selection()
    assert blocker.signal_triggered
    assert blocker.args[0] == 'a = 1'
    # check cursor moves to start of next line; note line number is zero based
    assert editor.get_cursor_line_column() == (1, 0)

def test_run_last_nonempty_line(editor_bot):
    editor_stack, editor, qtbot = editor_bot
    editor.go_to_line(4)
    with qtbot.waitSignal(editor_stack.exec_in_extconsole) as blocker:
        editor_stack.run_selection()
    assert blocker.signal_triggered
    assert blocker.args[0] == 'x = 2'
    assert editor.get_cursor_line_column() == (4, 0) # check cursor moves down

def test_run_empty_line_in_middle(editor_bot):
    editor_stack, editor, qtbot = editor_bot
    editor.go_to_line(3)
    with qtbot.assertNotEmitted(editor_stack.exec_in_extconsole):
        editor_stack.run_selection()
    assert editor.get_cursor_line_column() == (3, 0) # check cursor moves down

def test_run_last_line_when_empty(editor_bot):
    editor_stack, editor, qtbot = editor_bot
    with qtbot.assertNotEmitted(editor_stack.exec_in_extconsole):
        editor_stack.run_selection()
    # check cursor doesn't move
    assert editor.get_cursor_line_column() == (4, 0)

def test_run_last_line_when_nonempty(editor_bot):
    editor_stack, editor, qtbot = editor_bot
    editor.stdkey_backspace() # delete empty line at end
    old_text = editor.toPlainText()
    with qtbot.waitSignal(editor_stack.exec_in_extconsole) as blocker:
        editor_stack.run_selection()
    assert blocker.signal_triggered
    assert blocker.args[0] == 'x = 2'
    expected_new_text = old_text + editor.get_line_separator()
    # check blank line got added
    assert editor.toPlainText() == expected_new_text
    assert editor.get_cursor_line_column() == (4, 0) # check cursor moves down

def test_find_replace_case_sensitive(qtbot):
    editor_stack, editor = setup_editor(qtbot)
    editor_stack.find_widget.case_button.setChecked(True)
    text = ' test \nTEST \nTest \ntesT '
    editor.set_text(text)
    editor_stack.find_widget.search_text.add_text('test')
    editor_stack.find_widget.replace_text.add_text('pass')
    editor_stack.find_widget.replace_find()
    editor_stack.find_widget.replace_find()
    editor_stack.find_widget.replace_find()
    editor_stack.find_widget.replace_find()
    editor_text = editor.toPlainText()
    assert editor_text == ' pass \nTEST \nTest \ntesT '

def test_replace_current_selected_line(editor_find_replace_bot):
    editor_stack, editor, finder, qtbot = editor_find_replace_bot
    expected_new_text = ('ham bacon\n'
                         'spam sausage\n'
                         'spam egg')
    old_text = editor.toPlainText()
    finder.show()
    finder.show_replace()
    qtbot.keyClicks(finder.search_text, 'spam')
    qtbot.keyClicks(finder.replace_text, 'ham')
    qtbot.keyPress(finder.replace_text, Qt.Key_Return)
    assert editor.toPlainText()[0:-1] == expected_new_text

def test_replace_enter_press(editor_find_replace_bot):
    """Test advance forward pressing Enter, and backwards with Shift+Enter."""
    editor_stack, editor, finder, qtbot = editor_find_replace_bot
    text = '  \nspam \nspam \nspam '
    editor.set_text(text)
    finder.show()

    finder.search_text.add_text('spam')

    # search forward
    qtbot.keyPress(finder.search_text, Qt.Key_Return)
    assert editor.get_cursor_line_column() == (1,4)

    qtbot.keyPress(finder.search_text, Qt.Key_Return)
    assert editor.get_cursor_line_column() == (2,4)

    qtbot.keyPress(finder.search_text, Qt.Key_Return)
    assert editor.get_cursor_line_column() == (3,4)

    # search backwards
    qtbot.keyPress(finder.search_text, Qt.Key_Return, modifier=Qt.ShiftModifier)
    assert editor.get_cursor_line_column() == (2,4)

    qtbot.keyPress(finder.search_text, Qt.Key_Return, modifier=Qt.ShiftModifier)
    assert editor.get_cursor_line_column() == (1,4)

    qtbot.keyPress(finder.search_text, Qt.Key_Return, modifier=Qt.ShiftModifier)
    assert editor.get_cursor_line_column() == (3,4)

def test_replace_plain_regex(editor_find_replace_bot):
    """Test that regex reserved characters are displayed as plain text."""
    editor_stack, editor, finder, qtbot = editor_find_replace_bot
    expected_new_text = ('.\\[()]*test bacon\n'
                         'spam sausage\n'
                         'spam egg')
    finder.show()
    finder.show_replace()
    qtbot.keyClicks(finder.search_text, 'spam')
    qtbot.keyClicks(finder.replace_text, '.\[()]*test')
    qtbot.keyPress(finder.replace_text, Qt.Key_Return)
    assert editor.toPlainText()[0:-1] == expected_new_text

def test_replace_invalid_regex(editor_find_replace_bot):
    """Assert that replacing an invalid regexp does nothing."""
    editor_stack, editor, finder, qtbot = editor_find_replace_bot
    old_text = editor.toPlainText()
    finder.show()
    finder.show_replace()
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


def test_selection_escape_characters(editor_find_replace_bot):
    editor_stack, editor, finder, qtbot = editor_find_replace_bot
    expected_new_text = ('spam bacon\n'
                         'spam sausage\n'
                         'spam egg\n'
                         '\\n \\t some escape characters')
    qtbot.keyClicks(editor, '\\n \\t escape characters')

    finder.show()
    finder.show_replace()
    qtbot.keyClicks(finder.search_text, 'escape')
    qtbot.keyClicks(finder.replace_text, 'some escape')

    # Select last line
    cursor = editor.textCursor()
    cursor.select(QTextCursor.LineUnderCursor)
    assert cursor.selection().toPlainText() == "\\n \\t escape characters"

    #replace
    finder.replace_find_selection()
    assert editor.toPlainText() == expected_new_text


def test_advance_cell(editor_cells_bot):
    editor_stack, editor, qtbot = editor_cells_bot

    # cursor at the end of the file
    assert editor.get_cursor_line_column() == (10, 0)

    # advance backwards to the begining of the 3rd cell
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


def test_unfold_when_searching(editor_folding_bot):
    editor_stack, editor, finder, qtbot = editor_folding_bot
    folding_panel = editor.panels.get('FoldingPanel')
    line_search = editor.document().findBlockByLineNumber(3)

    # fold region
    block = editor.document().findBlockByLineNumber(1)
    folding_panel.toggle_fold_trigger(block)
    assert not line_search.isVisible()

    # unfolded when searching
    finder.show()
    qtbot.keyClicks(finder.search_text, 'print')
    qtbot.keyPress(finder.search_text, Qt.Key_Return)
    assert line_search.isVisible()


def test_unfold_goto(editor_folding_bot):
    editor_stack, editor, finder, qtbot = editor_folding_bot
    folding_panel = editor.panels.get('FoldingPanel')
    line_goto = editor.document().findBlockByLineNumber(3)

    # fold region
    block = editor.document().findBlockByLineNumber(1)
    folding_panel.toggle_fold_trigger(block)
    assert not line_goto.isVisible()

    # unfolded when goto
    editor.go_to_line(4)
    assert line_goto.isVisible()


@pytest.mark.skipif(PY2, reason="Python2 does not support unicode very well")
def test_get_current_word(base_editor_bot):
    """Test getting selected valid python word."""
    editor_stack, qtbot = base_editor_bot
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


def test_tab_keypress_properly_caught_find_replace(editor_find_replace_bot):
    """Test that tab works in find/replace dialog. Regression test for #3674.
    Mock test—more isolated but less flimsy."""
    editor_stack, editor, finder, qtbot = editor_find_replace_bot
    text = '  \nspam \nspam \nspam '
    editor.set_text(text)
    finder.show()
    finder.show_replace()

    finder.focusNextChild = MagicMock(name="focusNextChild")
    qtbot.keyPress(finder.search_text, Qt.Key_Tab)
    finder.focusNextChild.assert_called_once_with()


@flaky(max_runs=3)
@pytest.mark.skipif(os.environ.get('CI', None) is None and
                    platform.startswith('linux'),
                    reason="Fails on some Linux platforms locally.")
def test_tab_moves_focus_from_search_to_replace(editor_find_replace_bot):
    """Test that tab works in find/replace dialog. Regression test for #3674.
    "Real world" test—more comprehensive but potentially less robust."""
    editor_stack, editor, finder, qtbot = editor_find_replace_bot
    text = '  \nspam \nspam \nspam '
    editor.set_text(text)
    finder.show()
    finder.show_replace()

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
@pytest.mark.skipif(platform.startswith('linux'), reason="Fails on Linux.")
def test_tab_copies_find_to_replace(editor_find_replace_bot):
    """Check that text in the find box is copied to the replace box on tab
    keypress. Regression test #4482."""
    editor_stack, editor, finder, qtbot = editor_find_replace_bot
    finder.show()
    finder.show_replace()
    finder.search_text.setFocus()
    finder.search_text.set_current_text('This is some test text!')
    qtbot.keyClick(finder.search_text, Qt.Key_Tab)
    qtbot.wait(500)
    assert finder.replace_text.currentText() == 'This is some test text!'


if __name__ == "__main__":
    pytest.main()
