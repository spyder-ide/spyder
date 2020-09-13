# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
#

"""Tests for editor extra selections (decorations)."""

# Third party imports
from unittest.mock import patch
import os.path as osp

import pytest
from qtpy.QtGui import QFont, QTextCursor, QTextFormat

# Local imports
from spyder.plugins.editor.widgets.codeeditor import (
    CodeEditor, UPDATE_DECORATIONS_TIMEOUT)


HERE = osp.dirname(osp.realpath(__file__))
PARENT = osp.dirname(HERE)


# --- Fixtures
# -----------------------------------------------------------------------------
@pytest.fixture
def construct_editor(qtbot):
    """Construct editor for testing extra selections."""
    editor = CodeEditor(parent=None)
    editor.setup_editor(
        language='Python',
        color_scheme='spyder/dark',
        font=QFont("Monospace", 10),
    )
    editor.resize(640, 480)
    editor.show()
    qtbot.addWidget(editor)
    return editor


def test_extra_selections(construct_editor, qtbot):
    """Test extra selections."""
    editor = construct_editor

    text = ("def some_function():\n"
            "    some_variable = 1\n"
            "    some_variable += 2\n"
            "    return some_variable\n"
            "# %%")
    editor.set_text(text)

    # Move cursor over 'some_variable'
    editor.go_to_line(2)
    cursor = editor.textCursor()
    cursor.movePosition(QTextCursor.Right, n=5)
    editor.setTextCursor(cursor)

    # Assert number of extra selections is the one we expect
    qtbot.wait(3000)
    assert len(editor.extraSelections()) == 5

    selections = editor.extraSelections()
    selected_texts = [sel.cursor.selectedText() for sel in selections]

    # Assert that selection 0 is current cell
    assert selections[0].format.background() == editor.currentcell_color

    # Assert that selection 1 is current_line
    assert selections[1].format.property(QTextFormat.FullWidthSelection)
    assert selections[1].format.background() == editor.currentline_color

    # Assert that selections 2, 3, 4 are some_variable
    assert set(selected_texts[2:5]) == set(['some_variable'])


def test_update_decorations_when_scrolling(qtbot):
    """
    Test how many calls we're doing to update decorations when
    scrolling.
    """
    # NOTE: Here we need to use `patch` from unittest.mock, instead of the
    # mocker fixture, to have the same results when running the test
    # alone and with the other tests in this file.

    patched_object = ('spyder.plugins.editor.utils.decoration.'
                      'TextDecorationsManager._update')

    with patch(patched_object) as _update:
        # NOTE: We can't use a fixture to build a CodeEditor instance here
        # because the testing results are not consistent.
        editor = CodeEditor(parent=None)
        editor.setup_editor(
            language='Python',
            color_scheme='spyder/dark',
            font=QFont("Monospace", 10),
        )
        editor.resize(640, 480)
        editor.show()
        qtbot.addWidget(editor)

        # If there's no waiting after CodeEditor is created, there shouldn't
        # be a call to _update.
        assert _update.call_count == 0

        with open(osp.join(PARENT, 'codeeditor.py'), 'r') as f:
            text = f.read()
        editor.set_text(text)

        # If there's no waiting after setting text, there shouldn't be a
        # call to _update either.
        assert _update.call_count == 0

        # Simulate scrolling
        scrollbar = editor.verticalScrollBar()
        for i in range(6):
            scrollbar.setValue(i * 70)
            qtbot.wait(100)

        # A new call is done here due to __cursor_position_changed being
        # called, which in turn calls highlight_current_cell and
        # highlight_current_line
        assert _update.call_count == 1

        # Wait for decorations to update
        qtbot.wait(UPDATE_DECORATIONS_TIMEOUT + 100)

        # Assert a new call to _update was done
        assert _update.call_count == 2

        # Simulate grabbing and moving the scrollbar with the mouse
        scrollbar = editor.verticalScrollBar()
        value = scrollbar.value()
        for i in range(400):
            scrollbar.setValue(value + 1)
            value = scrollbar.value()

        # No calls should be done after this.
        assert _update.call_count == 2

        # Wait for decorations to update
        qtbot.wait(UPDATE_DECORATIONS_TIMEOUT + 100)

        # Assert a new call to _update was done
        assert _update.call_count == 3


if __name__ == "__main__":
    pytest.main()
