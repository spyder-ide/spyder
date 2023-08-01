# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
#

"""
Tests for the comment features
"""

# Third party imports
import pytest
from qtpy.QtGui import QTextCursor


# --- Helper methods
# -----------------------------------------------------------------------------
def toggle_comment(editor, single_line=True, start_line=1):
    """Toggle comment and return code."""
    editor.go_to_line(start_line)
    if single_line:
        editor.toggle_comment()
    else:
        editor.moveCursor(QTextCursor.End, mode=QTextCursor.KeepAnchor)
        editor.toggle_comment()
    text = editor.toPlainText()
    return str(text)


# --- Tests
# -----------------------------------------------------------------------------
def test_single_line_comment(codeeditor):
    """Test toggle comment in a single line."""
    editor = codeeditor
    text = ("#class a():\n"
            "#    self.b = 1\n"
            " #   print(self.b)\n"
            "#    \n"
            )
    editor.set_text(text)
    # Toggle comment without spaces from the prefix and manually inserted
    text = toggle_comment(editor)
    assert text == ("class a():\n"
                    "#    self.b = 1\n"
                    " #   print(self.b)\n"
                    "#    \n"
                    )
    # Toggle comment with space insertion
    text = toggle_comment(editor)
    assert text == ("# class a():\n"
                    "#    self.b = 1\n"
                    " #   print(self.b)\n"
                    "#    \n"
                    )
    # Toggle comment deleting the insert space
    text = toggle_comment(editor)
    assert text == ("class a():\n"
                    "#    self.b = 1\n"
                    " #   print(self.b)\n"
                    "#    \n"
                    )
    # Toggle comment with space at the right of prefix but manually inserted
    text = toggle_comment(editor, start_line=2)
    assert text == ("class a():\n"
                    "    self.b = 1\n"
                    " #   print(self.b)\n"
                    "#    \n"
                    )
    # Toggle comment with space insertion
    text = toggle_comment(editor, start_line=2)
    assert text == ("class a():\n"
                    "    # self.b = 1\n"
                    " #   print(self.b)\n"
                    "#    \n"
                    )
    # Toggle comment deleting inserted space
    text = toggle_comment(editor, start_line=2)
    assert text == ("class a():\n"
                    "    self.b = 1\n"
                    " #   print(self.b)\n"
                    "#    \n"
                    )
    # Toggle comment with space at the right and left of prefix
    # but manually inserted
    text = toggle_comment(editor, start_line=3)
    assert text == ("class a():\n"
                    "    self.b = 1\n"
                    "    print(self.b)\n"
                    "#    \n"
                    )


def test_selection_comment(codeeditor):
    """Test toggle comments with selection of more tha one line."""
    editor = codeeditor
    text = ("#class a():\n"
            "#    self.b = 1\n"
            " #   print(self.b)\n"
            "#    \n"
            )
    editor.set_text(text)
    # Toggle manually commented code
    text = toggle_comment(editor, single_line=False)
    assert text == ("class a():\n"
                    "    self.b = 1\n"
                    "    print(self.b)\n"
                    "    \n"
                    )
    # Toggle comment inserting prefix and space
    text = toggle_comment(editor, single_line=False)
    assert text == ("# class a():\n"
                    "#     self.b = 1\n"
                    "#     print(self.b)\n"
                    "    \n"
                    )
    # Toggle comment deleting inserted prefix and space
    text = toggle_comment(editor, single_line=False)
    assert text == ("class a():\n"
                    "    self.b = 1\n"
                    "    print(self.b)\n"
                    "    \n"
                    )
    # Test compatibility with Spyder 3 commenting structure
    text = ("#class a():\n"
            "#    self.b = 1\n"
            "#    print(self.b)\n"
            "#    \n"
            )
    editor.set_text(text)
    # Toggle comment deleting inserted prefix (without space)
    text = toggle_comment(editor, single_line=False)
    assert text == ("class a():\n"
                    "    self.b = 1\n"
                    "    print(self.b)\n"
                    "    \n"
                    )


if __name__ == "__main__":
    pytest.main()
