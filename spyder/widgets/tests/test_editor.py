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

# Local imports
from spyder.widgets.editor import EditorStack

def setup_editor(qtbot):
    """
    Set up EditorStack with CodeEditor containing some Python code.
    The cursor is at the empty line below the code.
    Returns tuple with EditorStack and CodeEditor.
    """
    text = ('a = 1\n'
            'print(a)\n'
            '\n'
            'x = 2')  # a newline is added at end
    editorStack = EditorStack(None, [])
    editorStack.set_introspector(Mock())
    editorStack.set_find_widget(Mock())
    editorStack.set_io_actions(Mock(), Mock(), Mock(), Mock())
    finfo = editorStack.new('foo.py', 'utf-8', text)
    qtbot.addWidget(editorStack)
    return editorStack, finfo.editor

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

    
if __name__ == "__main__":
    pytest.main()
