# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
#

"""
Tests for the indentation feature
"""

# Third party imports
import pytest
from qtpy.QtGui import QTextCursor

# Local imports
from spyder.py3compat import to_text_string
from spyder.widgets.sourcecode.codeeditor import CodeEditor


# --- Helper methods
# -----------------------------------------------------------------------------
def make_indent(editor, single_line=True, start_line=1):
    """Indent and return code."""
    editor.go_to_line(start_line)
    if not single_line:
        editor.moveCursor(QTextCursor.End, mode=QTextCursor.KeepAnchor)
    editor.indent()
    text = editor.toPlainText()
    return to_text_string(text)


# --- Fixtures
# -----------------------------------------------------------------------------
@pytest.fixture
def code_editor_indent_bot(qtbot):
    """
    Setup CodeEditor with some text useful for folding related tests.
    """
    editor = CodeEditor(parent=None)
    indent_chars = " " * 2
    tab_stop_width_spaces = 4
    language = "Python"
    editor.setup_editor(language=language, indent_chars=indent_chars,
                        tab_stop_width_spaces=tab_stop_width_spaces)

    return editor, qtbot


# --- Tests
# -----------------------------------------------------------------------------
def test_single_line_indent(code_editor_indent_bot):
    """Test indentation in a single line."""
    editor, qtbot = code_editor_indent_bot
    text = ("class a():\n"
            "self.b = 1\n"
            "print(self.b)\n"
            "\n"
            )
    editor.set_text(text)
    # Indent line without spaces
    text = make_indent(editor, start_line=2)
    assert text == ("class a():\n"
                    "  self.b = 1\n"
                    "print(self.b)\n"
                    "\n"
                    )


def test_selection_indent(code_editor_indent_bot):
    """Test indentation with selection of more than one line."""
    editor, qtbot = code_editor_indent_bot
    text = ("class a():\n"
            "self.b = 1\n"
            "print(self.b)\n"
            "\n"
            )
    editor.set_text(text)
    # Toggle manually commented code
    text = make_indent(editor, single_line=False, start_line=2)
    assert text == ("class a():\n"
                    "  self.b = 1\n"
                    "  print(self.b)\n"
                    "  \n"
                    )


def test_fix_indentation(code_editor_indent_bot):
    """Test fix_indentation() method."""
    editor, qtbot = code_editor_indent_bot
    # Contains tabs.
    original = ("\t\n"
                "class a():\t\n"
                "\tself.b = 1\n"
                "\tprint(self.b)\n"
                "\n"
                )
    # Fix indentation replaces tabs with 4 spaces and not indent_chars spaces.
    fixed = ("    \n"
             "class a():    \n"
             "    self.b = 1\n"
             "    print(self.b)\n"
             "\n"
             )
    editor.set_text(original)
    editor.fix_indentation()
    assert to_text_string(editor.toPlainText()) == fixed
    assert editor.document().isModified()
    # Test that undo/redo works - issue 1754.
    editor.undo()
    assert to_text_string(editor.toPlainText()) == original
    assert not editor.document().isModified()
    editor.redo()
    assert to_text_string(editor.toPlainText()) == fixed
    assert editor.document().isModified()


if __name__ == "__main__":
    pytest.main()
