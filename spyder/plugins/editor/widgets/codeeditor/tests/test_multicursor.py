# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
#

# Standard library imports

# Third party imports
import pytest
from qtpy.QtCore import Qt, QPoint
from qtpy.QtGui import QTextCursor

# Local imports


def test_add_cursor(codeeditor, qtbot):
    # enabled by default arg on CodeEditor.setup_editor (which is called in the
    #    pytest fixture creation in conftest.py)
    assert codeeditor.multi_cursor_enabled
    codeeditor.set_text("0123456789")
    qtbot.wait(100)
    x, y = codeeditor.get_coordinates(6)
    point = codeeditor.calculate_real_position(QPoint(x, y))
    point = QPoint(x, y)

    qtbot.mouseClick(codeeditor.viewport(),
                     Qt.MouseButton.LeftButton,
                     (Qt.KeyboardModifier.ControlModifier |
                      Qt.KeyboardModifier.AltModifier),
                     pos=point,
                     delay=100)
    # A cursor was added
    assert bool(codeeditor.extra_cursors)
    qtbot.keyClick(codeeditor, "a")
    # Text was inserted correctly from two cursors
    assert codeeditor.toPlainText() == "a012345a6789"

def test_column_add_cursor(codeeditor, qtbot):
    codeeditor.set_text("0123456789\n0123456789\n0123456789\n0123456789\n")
    cursor = codeeditor.textCursor()
    cursor.movePosition(QTextCursor.MoveOperation.Down,
                        QTextCursor.MoveMode.MoveAnchor,
                        3)
    codeeditor.setTextCursor(cursor)
    x, y = codeeditor.get_coordinates(6)
    point = codeeditor.calculate_real_position(QPoint(x, y))
    point = QPoint(x, y)
    qtbot.mouseClick(codeeditor.viewport(),
                     Qt.MouseButton.LeftButton,
                     (Qt.KeyboardModifier.ControlModifier |
                      Qt.KeyboardModifier.AltModifier |
                      Qt.KeyboardModifier.ShiftModifier),
                     pos=point,
                     delay=100)
    assert bool(codeeditor.extra_cursors)
    assert len(codeeditor.all_cursors) == 4
    for cursor in codeeditor.all_cursors:
        assert cursor.selectedText() == "012345"

if __name__ == '__main__':
    pytest.main(['test_multicursor.py'])
