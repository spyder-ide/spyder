# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
#
"""Tests for editor extra selections (decorations)."""

# Third party imports
import pytest
from qtpy.QtGui import QTextCursor, QTextFormat

# Local imports
from spyder.utils.qthelpers import qapplication
from spyder.widgets.sourcecode.codeeditor import CodeEditor


# --- Fixtures
# -----------------------------------------------------------------------------
def construct_editor(*args, **kwargs):
    """Construct editor with some text for testing extra selections."""
    app = qapplication()
    editor = CodeEditor(parent=None)
    kwargs['language'] = 'Python'
    editor.setup_editor(*args, **kwargs)

    text = ("def some_function():\n"
            "    some_variable = 1\n"
            "    some_variable += 2\n"
            "    return some_variable\n"
            "# %%")
    editor.set_text(text)
    return editor


def test_extra_selections(qtbot):
    """Test extra selections."""
    editor = construct_editor()

    # Move cursor over 'some_variable'
    editor.go_to_line(2)
    cursor = editor.textCursor()
    cursor.movePosition(QTextCursor.Right, n=5)
    editor.setTextCursor(cursor)

    qtbot.waitUntil(lambda: len(editor.extraSelections()) >= 6, timeout=2000)
    print(len(editor.extraSelections()))
    selections = editor.extraSelections()
    selected_texts = [sel.cursor.selectedText() for sel in selections]

    # Assert that selection 0 is current cell
    assert selections[0].format.background() == editor.currentcell_color

    # Assert that selection 1 is current_line
    assert selections[1].format.property(QTextFormat.FullWidthSelection)
    assert selections[1].format.background() == editor.currentline_color

    # Assert that selections 2, 3, 4 are some_variable
    assert set(selected_texts[2:5]) == set(['some_variable'])


if __name__ == "__main__":
    pytest.main()
