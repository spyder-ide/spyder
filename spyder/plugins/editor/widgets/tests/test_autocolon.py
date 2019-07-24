# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
#

"""
Tests for the automatic insertion of colons in the editor
"""

# Third party imports
from qtpy.QtGui import QTextCursor
import pytest

# Local imports
from spyder.utils.qthelpers import qapplication
from spyder.plugins.editor.widgets.codeeditor import CodeEditor


# --- Fixtures
# -----------------------------------------------------------------------------
def construct_editor(text):
    app = qapplication()
    editor = CodeEditor(parent=None)
    editor.setup_editor(language='Python')
    editor.set_text(text)
    cursor = editor.textCursor()
    cursor.movePosition(QTextCursor.End)
    editor.setTextCursor(cursor)
    return editor


# --- Tests
# -----------------------------------------------------------------------------
def test_no_auto_colon_after_simple_statement():
    editor = construct_editor("x = 1")
    assert editor.autoinsert_colons() == False

def test_auto_colon_after_if_statement():
    editor = construct_editor("if x == 1")
    assert editor.autoinsert_colons() == True

def test_no_auto_colon_if_not_at_end_of_line():
    editor = construct_editor("if x == 1")
    cursor = editor.textCursor()
    cursor.movePosition(QTextCursor.Left)
    editor.setTextCursor(cursor)
    assert editor.autoinsert_colons() == False

def test_no_auto_colon_if_unterminated_string():
    editor = construct_editor("if x == '1")
    assert editor.autoinsert_colons() == False

def test_no_auto_colon_in_comment():
    editor = construct_editor("if x == 1 # comment")
    assert editor.autoinsert_colons() == False

def test_no_auto_colon_if_already_ends_in_colon():
    editor = construct_editor("if x == 1:")
    assert editor.autoinsert_colons() == False

def test_no_auto_colon_if_ends_in_backslash():
    editor = construct_editor("if x == 1 \\")
    assert editor.autoinsert_colons() == False

def test_no_auto_colon_in_one_line_if_statement():
    editor = construct_editor("if x < 0: x = 0")
    assert editor.autoinsert_colons() == False

def test_auto_colon_even_if_colon_inside_brackets():
    editor = construct_editor("if text[:-1].endswith('bla')")
    assert editor.autoinsert_colons() == True

def test_no_auto_colon_in_listcomp_over_two_lines():
    editor = construct_editor("ns = [ n for ns in range(10) \n if n < 5 ]")
    assert editor.autoinsert_colons() == False


# --- Failing tests
# -----------------------------------------------------------------------------
@pytest.mark.xfail
def test_auto_colon_even_if_colon_inside_quotes():
    editor = construct_editor("if text == ':'")
    assert editor.autoinsert_colons() == True

@pytest.mark.xfail
def test_no_auto_colon_in_listcomp_over_three_lines():
    editor = construct_editor("ns = [ n \n for ns in range(10) \n if n < 5 ]")
    cursor = editor.textCursor()
    cursor.movePosition(QTextCursor.Up)
    cursor.movePosition(QTextCursor.EndOfLine)
    editor.setTextCursor(cursor)
    assert editor.autoinsert_colons() == False

@pytest.mark.xfail
def test_auto_colon_in_two_if_statements_on_one_line():
    editor = construct_editor("if x < 0: x = 0; if x == 0")
    assert editor.autoinsert_colons() == True


if __name__ == "__main__":
    pytest.main()
