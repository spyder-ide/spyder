# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
#

"""Tests for editor decorations."""

# Third party imports
import os.path as osp
import random
from unittest.mock import patch

from flaky import flaky
import pytest
from qtpy.QtCore import Qt
from qtpy.QtGui import QFont, QTextCursor

# Local imports
from spyder.plugins.editor.widgets.codeeditor import CodeEditor


HERE = osp.dirname(osp.realpath(__file__))
PARENT = osp.dirname(HERE)


def test_decorations(codeeditor, qtbot):
    """Test decorations."""
    editor = codeeditor

    # Set random size
    editor.resize(640, random.randint(200, 500))

    # Set cell of different length.
    base_function = (
        "def some_function():\n"
        "    some_variable = 1\n"
        "    some_variable += 2\n"
        "    return some_variable\n\n"
    )

    text = ''
    for __ in range(100):
        base_text = base_function * random.randint(2, 8) + "# %%\n"
        text = text + base_text

    editor.set_text(text)

    # Move cursor over 'some_variable'
    editor.go_to_line(2)
    cursor = editor.textCursor()
    cursor.movePosition(QTextCursor.Right, n=5)
    editor.setTextCursor(cursor)

    # Assert number of decorations is the one we expect.
    qtbot.wait(3000)
    decorations = editor.decorations._sorted_decorations()

    assert len(decorations) == 2 + text.count('some_variable')

    # Assert that selection 0 is current cell
    assert decorations[0].kind == 'current_cell'

    # Assert that selection 1 is current_line
    assert decorations[1].kind == 'current_line'

    # Assert the other decorations are occurrences
    assert all([d.kind == 'occurrences' for d in decorations[2:5]])

    # Assert all other decorations are some_variable
    selected_texts = [d.cursor.selectedText() for d in decorations]
    assert set(selected_texts[2:]) == set(['some_variable'])

    # Assert painted extra selections are much smaller.
    first, last = editor.get_buffer_block_numbers()
    max_decorations = last - first
    assert len(editor.extraSelections()) < max_decorations

    # Clear decorations to be sure they are painted again below.
    editor.decorations.clear()
    editor.decorations._update()
    assert editor.decorations._sorted_decorations() == []

    # Move to a random place in the file and wait until decorations are
    # updated.
    line_number = random.randint(100, editor.blockCount())
    editor.go_to_line(line_number)
    qtbot.wait(editor.UPDATE_DECORATIONS_TIMEOUT + 100)

    # Assert a new cell is painted
    decorations = editor.decorations._sorted_decorations()
    assert decorations[0].kind == 'current_cell'


@flaky(max_runs=10)
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

        with open(osp.join(PARENT, 'codeeditor.py'), 'r', encoding='utf-8') as f:
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
        qtbot.wait(editor.UPDATE_DECORATIONS_TIMEOUT + 100)

        # Assert a new call to _update was done
        assert _update.call_count == 2

        # Simulate grabbing and moving the scrollbar with the mouse
        scrollbar = editor.verticalScrollBar()
        value = scrollbar.value()
        for __ in range(400):
            scrollbar.setValue(value + 1)
            value = scrollbar.value()

        # No calls should be done after this.
        assert _update.call_count == 2

        # Wait for decorations to update
        qtbot.wait(editor.UPDATE_DECORATIONS_TIMEOUT + 100)

        # Assert a new call to _update was done
        assert _update.call_count == 3

        # Move to the last visible line
        _, last = editor.get_visible_block_numbers()
        editor.go_to_line(last)

        # Simulate continuously pressing the down arrow key.
        for __ in range(200):
            qtbot.keyPress(editor, Qt.Key_Down)

        # Only one call to _update should be done, after releasing the key.
        qtbot.wait(editor.UPDATE_DECORATIONS_TIMEOUT + 100)
        assert _update.call_count == 4

        # Simulate continuously pressing the up arrow key.
        for __ in range(200):
            qtbot.keyPress(editor, Qt.Key_Up)

        # Only one call to _update should be done, after releasing the key.
        qtbot.wait(editor.UPDATE_DECORATIONS_TIMEOUT + 100)
        assert _update.call_count == 5


if __name__ == "__main__":
    pytest.main()
