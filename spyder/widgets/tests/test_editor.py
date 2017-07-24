# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
#

"""
Tests for editor.py
"""

# Standard library imports
try:
    from unittest.mock import Mock
except ImportError:
    from mock import Mock # Python 2

# Third party imports
import pytest
from qtpy.QtCore import Qt

# Local imports
from spyder.utils.fixtures import setup_editor
from spyder.widgets.editor import EditorStack
from spyder.widgets.findreplace import FindReplace

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
    Setup CodeEditor with some text usepful for folding related tests.
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


if __name__ == "__main__":
    pytest.main()
