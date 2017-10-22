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
from qtpy import PYQT4
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


@pytest.fixture
def editor_splitter_bot(qtbot):
    """Create editor splitter."""
    es = editor_splitter = EditorSplitter(None, Mock(), [], first=True)
    qtbot.addWidget(es)
    es.show()
    yield es
    es.destroy()


@pytest.fixture
def editor_splitter_layout_bot(editor_splitter_bot):
    """Create editor splitter for testing layouts."""
    es = editor_splitter_bot

    # Allow the split() to duplicate editor stacks.
    def clone(editorstack):
        editorstack.close_action.setEnabled(False)
        editorstack.set_introspector(Mock())
        editorstack.set_find_widget(Mock())
        editorstack.set_io_actions(Mock(), Mock(), Mock(), Mock())
        editorstack.new('foo.py', 'utf-8', 'a = 1\nprint(a)\n\nx = 2')
        editorstack.new('layout_test.py', 'utf-8', 'print(spam)')
        with open(__file__) as f:
            text = f.read()
        editorstack.new(__file__, 'utf-8', text)

    es.plugin.clone_editorstack.side_effect = clone

    # Setup editor info for this EditorStack.
    clone(es.editorstack)
    return es


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


class TestEditorSplitter:
    """Tests for EditorSplitter methods."""

    def test_init(self, editor_splitter_bot):
        """"Test __init__."""
        es = editor_splitter_bot
        assert es.orientation() == Qt.Horizontal
        assert es.testAttribute(Qt.WA_DeleteOnClose)
        assert not es.childrenCollapsible()
        assert not es.toolbar_list
        assert not es.menu_list
        assert es.register_editorstack_cb == es.plugin.register_editorstack
        assert es.unregister_editorstack_cb == es.plugin.unregister_editorstack

        # No menu actions in parameter call.
        assert not es.menu_actions
        # EditorStack adds its own menu actions to the existing actions.
        assert es.editorstack.menu_actions != []

        assert isinstance(es.editorstack, EditorStack)
        es.plugin.register_editorstack.assert_called_with(es.editorstack)
        es.plugin.unregister_editorstack.assert_not_called()
        es.plugin.clone_editorstack.assert_not_called()

        assert es.count() == 1
        assert es.widget(0) == es.editorstack

    def test_close(self, editor_splitter_bot):
        """Test close().

        This is a widget close function that only hides the split
        panel.  It does not close the files on the tabs or close any plugin.
        """
        es = editor_splitter_bot
        es.split()
        es.widget(1).split()
        es.widget(1).split()
        esw1w2 = es.widget(1).widget(2)
        esw1w2.split(Qt.Horizontal)
        assert not es.isHidden()
        assert not es.widget(1).isHidden()
        assert not es.widget(1).widget(1).isHidden()
        assert not esw1w2.isHidden()

        # Close last split only.
        esw1w2.editorstack.sig_close_split.emit()  # Signal call.
        assert not es.isHidden()
        assert not es.widget(1).isHidden()
        assert not es.widget(1).widget(1).isHidden()
        assert esw1w2.isHidden()

        # Close all splits.
        assert es.widget(1).close()  # Call directly.
        assert es.widget(1).isHidden()

    def test_split(self, editor_splitter_layout_bot):
        """Test split() that adds new splitters to this instance."""
        es = editor_splitter_layout_bot

        # Split main panel with default split.
        es.split()  # Call directly.
        assert es.orientation() == Qt.Vertical
        assert not es.editorstack.horsplit_action.isEnabled()
        assert es.editorstack.versplit_action.isEnabled()
        assert es.count() == 2
        assert isinstance(es.widget(1), EditorSplitter)
        # Each splitter gets its own editor stack as the first widget.
        assert es.widget(1).count() == 1
        assert es.widget(1).editorstack == es.widget(1).widget(0)
        es.widget(1).plugin.clone_editorstack.assert_called_with(
                                        editorstack=es.widget(1).editorstack)

        # Create a horizontal split on original widget.
        es.editorstack.sig_split_horizontally.emit()  # Call from signal.
        assert es.orientation() == Qt.Horizontal
        assert es.editorstack.horsplit_action.isEnabled()
        assert not es.editorstack.versplit_action.isEnabled()
        assert es.count() == 3
        assert isinstance(es.widget(2), EditorSplitter)
        # Two splits have been created and each contains one EditorStack.
        assert es.widget(1).count() == 1
        assert es.widget(2).count() == 1

        # Test splitting one of the children.
        es1 = es.widget(1)
        es1.editorstack.sig_split_vertically.emit()
        assert es.orientation() == Qt.Horizontal  # Main split didn't change.
        assert es1.orientation() == Qt.Vertical  # Child splitter.
        assert not es1.editorstack.horsplit_action.isEnabled()
        assert es1.editorstack.versplit_action.isEnabled()
        assert es1.count() == 2
        assert isinstance(es1.widget(0), EditorStack)
        assert isinstance(es1.widget(1), EditorSplitter)
        assert not es1.widget(1).isHidden()

    def test_iter_editorstacks(self, editor_splitter_bot):
        """Test iter_editorstacks."""
        es = editor_splitter_bot
        es_iter = es.iter_editorstacks

        # Check base splitter.
        assert es_iter() == [(es.editorstack, es.orientation())]

        # Split once.
        es.split(Qt.Vertical)
        esw1 = es.widget(1)
        assert es_iter() == [(es.editorstack, es.orientation()),
                             (esw1.editorstack, esw1.orientation())]

        # Second splitter on base isn't iterated.
        es.split(Qt.Horizontal)
        assert es_iter() == [(es.editorstack, es.orientation()),
                             (esw1.editorstack, esw1.orientation())]

        # Split a child.
        esw1.split(Qt.Vertical)
        esw1w1 = es.widget(1).widget(1)
        assert es_iter() == [(es.editorstack, es.orientation()),
                             (esw1.editorstack, esw1.orientation()),
                             (esw1w1.editorstack, esw1w1.orientation())]

    def test_get_layout_settings(self, editor_splitter_bot, qtbot, mocker):
        """Test get_layout_settings()."""
        es = editor_splitter_bot

        # Initial settings from setup.
        setting = es.get_layout_settings()
        assert setting['splitsettings'] == [(False, None, [])]

        # Add some editors to patch output of iter_editorstacks.
        stack1 = base_editor_bot(qtbot)[0]
        stack1.new('foo.py', 'utf-8', 'a = 1\nprint(a)\n\nx = 2')
        stack1.new('layout_test.py', 'utf-8', 'spam egg\n')

        stack2 = base_editor_bot(qtbot)[0]
        stack2.new('test.py', 'utf-8', 'test text')

        mocker.patch.object(EditorSplitter, "iter_editorstacks")
        EditorSplitter.iter_editorstacks.return_value = (
            [(stack1, Qt.Vertical), (stack2, Qt.Horizontal)])

        setting = es.get_layout_settings()
        assert setting['hexstate']
        assert setting['sizes'] == es.sizes()
        assert setting['splitsettings'] == [(False, 'foo.py', [5, 3]),
                                            (False, 'test.py', [2])]

    def test_set_layout_settings_dont_goto(self, editor_splitter_layout_bot):
        """Test set_layout_settings()."""
        es = editor_splitter_layout_bot
        linecount = es.editorstack.data[2].editor.get_cursor_line_number()

        # New layout to restore.
        state = '000000ff000000010000000200000231000001ff00ffffffff010000000200'
        sizes = [561, 511]
        splitsettings = [(False, 'layout_test.py', [2, 1, 52]),
                         (False, 'foo.py', [3, 2, 125]),
                         (False, __file__, [1, 1, 1])]

        new_settings = {'hexstate': state,
                        'sizes': sizes,
                        'splitsettings': splitsettings}

        # Current widget doesn't have saved settings applied.
        get_settings = es.get_layout_settings()
        assert es.count() == 1
        assert get_settings['hexstate'] != state
        assert get_settings['splitsettings'] != splitsettings

        # Invalid settings value.
        assert es.set_layout_settings({'spam': 'test'}) is None

        # Restore layout with dont_goto set.
        es.set_layout_settings(new_settings, dont_goto=True)
        get_settings = es.get_layout_settings()

        # Check that the panels were restored.
        assert es.count() == 2  # One EditorStack and one EditorSplitter.
        assert es.widget(1).count() == 2  # One EditorStack and one EditorSplitter.
        assert es.widget(1).widget(1).count() == 1  # One EditorStack.
        if not PYQT4:
            assert get_settings['hexstate'] == state

        # All the lines for each tab and split are at the last line number.
        assert get_settings['splitsettings'] == [(False, 'foo.py', [5, 2, linecount]),
                                                 (False, 'foo.py', [5, 2, linecount]),
                                                 (False, 'foo.py', [5, 2, linecount])]

    def test_set_layout_settings_goto(self, editor_splitter_layout_bot):
        """Test set_layout_settings()."""
        es = editor_splitter_layout_bot

        # New layout to restore.
        state = '000000ff000000010000000200000231000001ff00ffffffff010000000200'
        sizes = [561, 511]
        splitsettings = [(False, 'layout_test.py', [2, 1, 52]),
                         (False, 'foo.py', [3, 2, 125]),
                         (False, __file__, [1, 1, 1])]

        new_settings = {'hexstate': state,
                        'sizes': sizes,
                        'splitsettings': splitsettings}

        # Restore layout without dont_goto, meaning it should position to the lines.
        es.set_layout_settings(new_settings, dont_goto=None)
        get_settings = es.get_layout_settings()
        # Even though the original splitsettings had different file names
        # selected, the current tab isn't restored in set_layout_settings().
        # However, this shows that the current line was positioned for each tab
        # and each split.
        assert get_settings['splitsettings'] == [(False, 'foo.py', [2, 1, 52]),
                                                 (False, 'foo.py', [3, 2, 125]),
                                                 (False, 'foo.py', [1, 1, 1])]


if __name__ == "__main__":
    pytest.main()
