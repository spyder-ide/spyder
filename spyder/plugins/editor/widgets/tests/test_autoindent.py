# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
#

"""
Tests for the autoindent features
"""

# Third party imports
from qtpy.QtGui import QTextCursor
import pytest

# Local imports
from spyder.utils.qthelpers import qapplication
from spyder.py3compat import to_text_string
from spyder.plugins.editor.widgets.codeeditor import CodeEditor


# ---- Fixtures
def get_indent_fix(text, indent_chars=" " * 4, tab_stop_width_spaces=4,
                   sol=False, forward=True, language='Python'):
    """Return text with last line's indentation fixed."""
    app = qapplication()
    editor = CodeEditor(parent=None)
    editor.setup_editor(language=language, indent_chars=indent_chars,
                        tab_stop_width_spaces=tab_stop_width_spaces)

    editor.set_text(text)
    cursor = editor.textCursor()
    cursor.movePosition(QTextCursor.End)
    if sol:
        lines = text.splitlines(True)
        repeat = len(lines[-1].lstrip())
        cursor.movePosition(QTextCursor.Left, n=repeat)
    editor.setTextCursor(cursor)
    editor.fix_indent(forward=forward)
    return to_text_string(editor.toPlainText())


# ---- Tests
def test_simple_tuple():
    text = get_indent_fix("this_tuple = (1, 2)\n")
    assert text == "this_tuple = (1, 2)\n"


def test_def_with_newline():
    text = get_indent_fix("\ndef function():\n")
    assert text == "\ndef function():\n    ", repr(text)


def test_def_with_indented_comment():
    text = get_indent_fix("def function():\n    # Comment\n")
    assert text == "def function():\n    # Comment\n    ", repr(text)


def test_brackets_alone():
    text = get_indent_fix("def function():\n    print []\n")
    assert text == "def function():\n    print []\n    ", repr(text)


def test_simple_def():
    text = get_indent_fix("def function():\n")
    assert text == "def function():\n    ", repr(text)


def test_open_parenthesis():
    # An open parenthesis with no item is followed by a hanging indent
    text = get_indent_fix("open_parenthesis(\n")
    assert text == "open_parenthesis(\n        ", repr(text)


def test_open_bracket():
    # An open bracket with no item is followed by a hanging indent
    text = get_indent_fix("open_bracket[\n")
    assert text == "open_bracket[\n        ", repr(text)


def test_open_curly():
    # An open curly bracket with no item is followed by a hanging indent
    text = get_indent_fix("open_curly{\n")
    assert text == "open_curly{\n        ", repr(text)


def test_align_on_parenthesis():
    # An open parenthesis with one or more item is followed by an indent
    # up to the parenthesis.
    text = get_indent_fix("parenthesis_w_item = (1,\n")
    assert text == "parenthesis_w_item = (1,\n                      ", repr(text)


def test_align_on_bracket():
    # An open bracket with one or more item is followed by an indent
    # up to the parenthesis.
    text = get_indent_fix("bracket_w_item = (1,\n")
    assert text == "bracket_w_item = (1,\n                  ", repr(text)


def test_align_on_curly():
    # An open curly bracket with one or more item is followed by an indent
    # up to the parenthesis.
    text = get_indent_fix("curly_w_item = (1,\n")
    assert text == "curly_w_item = (1,\n                ", repr(text)


def test_keep_unindent():
    # Keep line unindented if there is more than one line under the statement
    text = ("    def foo(bar):\n"
            "        generic = bar\n"
            "    \n"
            "    keep_unindent\n")
    correct_text = ("    def foo(bar):\n"
                    "        generic = bar\n"
                    "    \n"
                    "    keep_unindent\n")
    text = get_indent_fix(text, sol=True)
    assert text == correct_text, repr(text)


def test_keep_unindent_fix_indent():
    # Keep line unindented but fix indent if not multiple of len(indent_chars)
    text = ("    for x in range(n):\n"
            "        increment += 1\n"
            "  \n"
            "  keep_unindent\n")
    correct_text = ("    for x in range(n):\n"
                    "        increment += 1\n"
                    "  \n"
                    "    keep_unindent\n")
    text = get_indent_fix(text, sol=True)
    assert text == correct_text, repr(text)


def test_keep_unindent_if_blank():
    # Keep line unindented if return is pressed on a line which is both
    # blank and unindented.
    text = ("    def f(x):\n"
            "        return x\n"
            "\n"
            "")
    text = get_indent_fix(text)
    assert text == "    def f(x):\n        return x\n\n", repr(text)


def test_first_line():
    # Test fix_indent() when the cursor is on the first line.
    text = get_indent_fix("import numpy")
    assert text == "import numpy", repr(text)


@pytest.mark.parametrize(
    "text_input, expected, test_text",
    [
        ("tags = ['(a)', '(b)', '(c)']\n", "tags = ['(a)', '(b)', '(c)']\n",
         "test_commented_brackets"),
        ("s = a[(a['a'] == l) & (a['a'] == 1)]['a']\n", "s = a[(a['a'] == l) & (a['a'] == 1)]['a']\n",
         "test_balanced_brackets"),
        ("a = (a  #  some comment\n", "a = (a  #  some comment\n     ", "test_inline_comment"),
        ("len(a) == 1\n", "len(a) == 1\n", "test_balanced_brackets_not_ending_in_bracket"),
        ("x = f(\n", "x = f(\n      ", "test_short_open_bracket_not_hanging_indent"),
        ("def some_func():\n    return 10\n", "def some_func():\n    return 10\n",
         "test_return"),
        ("def some_func():\n    returns = 10\n", "def some_func():\n    returns = 10\n    ",
         "test_return_not_keyword"),
        ("foo = 1  # Comment open parenthesis (\n",
             "foo = 1  # Comment open parenthesis (\n",
             "test_comment_with parenthesis"),
    ])
def test_indentation_with_spaces(text_input, expected, test_text):
    text = get_indent_fix(text_input)
    assert text == expected, test_text

def test_def_with_unindented_comment():
    text = get_indent_fix("def function():\n# Comment\n")
    assert text == "def function():\n# Comment\n    ", repr(text)


@pytest.mark.parametrize("tab_stop_width_spaces", [1,2,3,4,5,6,7,8])
@pytest.mark.parametrize(
    "text_input, expected, test_text",
    [
# ---- Tabs tests
        ("this_tuple = (1, 2)\n", "this_tuple = (1, 2)\n", "simple tuple"),
        ("\ndef function():\n", "\ndef function():\n\t", "def with new line"),
        ("def function():\n\t# Comment\n", "def function():\n\t# Comment\n\t",
         "test with indented comment"),
        ("def function():\n\tprint []\n", "def function():\n\tprint []\n\t",
         "test brackets alone"),
        ("\nsome_long_name = {\n", "\nsome_long_name = {\n\t\t", "indentation after opening bracket"),
        ("def function():\n", "def function():\n\t", "test simple def"),
        ("open_parenthesis(\n", "open_parenthesis(\n\t\t",
         "open parenthesis"),
        ("tags = ['(a)', '(b)', '(c)']\n", "tags = ['(a)', '(b)', '(c)']\n",
         "test_commented_brackets"),
        ("s = a[(a['a'] == l) & (a['a'] == 1)]['a']\n", "s = a[(a['a'] == l) & (a['a'] == 1)]['a']\n",
         "test_balanced_brackets"),
        ("def some_func():\n\treturn 10\n", "def some_func():\n\treturn 10\n",
         "test_return"),
        ("def some_func():\n\treturns = 10\n", "def some_func():\n\treturns = 10\n\t",
         "test_return_not_keyword"),
        ("def function():\n# Comment\n", "def function():\n# Comment\n\t",
             "test_def_with_unindented_comment"),
    ])
def test_indentation_with_tabs(text_input, expected, test_text,
                               tab_stop_width_spaces):
    text = get_indent_fix(text_input, indent_chars="\t",
                          tab_stop_width_spaces=tab_stop_width_spaces)
    assert text == expected, test_text


@pytest.mark.parametrize(
    "text_input, expected, tab_stop_width_spaces",
    [
        ("print(\n)", "print(\n\t\t)", 1),
        ("print(\n)", "print(\n\t\t)", 2),
        ("print(\n)", "print(\n\t\t)", 3),
        ("print(\n)", "print(\n\t  )", 4),
        ("print(\n)", "print(\n\t )", 5),
        ("print(\n)", "print(\n\t)", 6),
        ("print(\n)", "print(\n      )", 7),
        ("print(\n)", "print(\n      )", 8),
        ("a = (a  #  some comment\n", "a = (a  #  some comment\n\t ", 4),
    ])
def test_indentation_with_tabs_parenthesis(text_input, expected,
                                           tab_stop_width_spaces):
    """Simple parenthesis indentation test with different tab stop widths."""
    text = get_indent_fix(text_input, indent_chars="\t",
                          tab_stop_width_spaces=tab_stop_width_spaces)
    assert text == expected, tab_stop_width_spaces


@pytest.mark.parametrize("tab_stop_width_spaces", [1,2,3,4,5,6,7,8])
@pytest.mark.parametrize(
    "text_input, expected, test_text",
    [
        ("\tx = 1", "x = 1", "simple test"),
    ])
def test_unindentation_with_tabs(text_input, expected, test_text,
                               tab_stop_width_spaces):
    text = get_indent_fix(text_input, indent_chars="\t",
                          tab_stop_width_spaces=tab_stop_width_spaces, 
                          forward=False)
    assert text == expected, test_text



@pytest.mark.parametrize(
    "text_input, expected, test_text",
    [
# ---- Simple indentation tests
        ("hola\n", "hola\n", "witout indentation"),
        ("  hola\n", "  hola\n  ", "some indentation"),
        ("\thola\n", "\thola\n\t", "tab indentation"),
        ("  hola(\n", "  hola(\n  ", "line with parenthesis"),
    ])
def test_simple_indentation(text_input, expected, test_text,):
    # language None deactivate smart indentation
    text = get_indent_fix(text_input, language=None)
    assert text == expected, test_text



if __name__ == "__main__":
    pytest.main()
