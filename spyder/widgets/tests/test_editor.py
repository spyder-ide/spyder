# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
#

"""
Tests for editor.py
"""

# Third party imports
import pytest

# Local imports
from spyder.utils.fixtures import setup_editor

def test_run_top_line(qtbot):
    editorStack, editor = setup_editor(qtbot)
    editor.go_to_line(1) # line number is one based
    editor.move_cursor(3)
    with qtbot.waitSignal(editorStack.exec_in_extconsole) as blocker:
        editorStack.run_selection()
    assert blocker.signal_triggered
    assert blocker.args[0] == 'a = 1'
    # check cursor moves to start of next line; note line number is zero based
    assert editor.get_cursor_line_column() == (1, 0) 

def test_run_last_nonempty_line(qtbot):
    editorStack, editor = setup_editor(qtbot)
    editor.go_to_line(4)
    with qtbot.waitSignal(editorStack.exec_in_extconsole) as blocker:
        editorStack.run_selection()
    assert blocker.signal_triggered
    assert blocker.args[0] == 'x = 2'
    assert editor.get_cursor_line_column() == (4, 0) # check cursor moves down

def test_run_empty_line_in_middle(qtbot):
    editorStack, editor = setup_editor(qtbot)
    editor.go_to_line(3)
    with qtbot.assertNotEmitted(editorStack.exec_in_extconsole):
        editorStack.run_selection()
    assert editor.get_cursor_line_column() == (3, 0) # check cursor moves down


def test_run_last_line_when_empty(qtbot):
    editorStack, editor = setup_editor(qtbot)
    with qtbot.assertNotEmitted(editorStack.exec_in_extconsole):
        editorStack.run_selection()
    assert editor.get_cursor_line_column() == (4, 0) # check cursor doesn't move

def test_run_last_line_when_nonempty(qtbot):
    editorStack, editor = setup_editor(qtbot)
    editor.stdkey_backspace() # delete empty line at end
    old_text = editor.toPlainText()
    with qtbot.waitSignal(editorStack.exec_in_extconsole) as blocker:
        editorStack.run_selection()
    assert blocker.signal_triggered
    assert blocker.args[0] == 'x = 2'
    expected_new_text = old_text + editor.get_line_separator()
    assert editor.toPlainText() == expected_new_text # check blank line got added
    assert editor.get_cursor_line_column() == (4, 0) # check cursor moves down

def test_find_replace_case_sensitive(qtbot):
    editorStack, editor = setup_editor(qtbot)
    editorStack.find_widget.case_button.setChecked(True)
    text = ' test \nTEST \nTest \ntesT '
    editor.set_text(text)
    editorStack.find_widget.search_text.add_text('test')
    editorStack.find_widget.replace_text.add_text('pass')
    editorStack.find_widget.replace_find()
    editorStack.find_widget.replace_find()
    editorStack.find_widget.replace_find()
    editorStack.find_widget.replace_find()
    editor_text = editor.toPlainText()
    assert editor_text == ' pass \nTEST \nTest \ntesT '


if __name__ == "__main__":
    pytest.main()
