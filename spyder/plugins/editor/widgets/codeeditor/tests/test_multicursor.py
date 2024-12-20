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


def click_at(codeeditor, qtbot, position, ctrl=False, alt=False, shift=False):
    x, y = codeeditor.get_coordinates(position)
    point = codeeditor.calculate_real_position(QPoint(x, y))
    point = QPoint(x, y)

    modifiers = Qt.KeyboardModifier.NoModifier
    if ctrl:
        modifiers |= Qt.KeyboardModifier.ControlModifier
    if alt:
        modifiers |= Qt.KeyboardModifier.AltModifier
    if shift:
        modifiers |= Qt.KeyboardModifier.ShiftModifier

    qtbot.mouseClick(
        codeeditor.viewport(),
        Qt.MouseButton.LeftButton,
        modifiers,
        pos=point
    )


def test_add_cursor(codeeditor, qtbot):
    # Enabled by default arg on CodeEditor.setup_editor (which is called in the
    # pytest fixture creation in conftest.py)
    assert codeeditor.multi_cursor_enabled
    assert codeeditor.cursorWidth() == 0  # required for multi-cursor rendering
    codeeditor.set_text("0123456789")
    click_at(codeeditor, qtbot, 6, ctrl=True, alt=True)

    # A cursor was added
    assert bool(codeeditor.extra_cursors)
    qtbot.keyClick(codeeditor, "a")

    # Text was inserted correctly from two cursors
    assert codeeditor.toPlainText() == "a012345a6789"

    # Regular click to set main cursor and clear extra cursors
    click_at(codeeditor, qtbot, 6)
    assert not bool(codeeditor.extra_cursors)
    qtbot.keyClick(codeeditor, "b")
    assert codeeditor.toPlainText() == "a01234b5a6789"


def test_column_add_cursor(codeeditor, qtbot):
    codeeditor.set_text("0123456789\n0123456789\n0123456789\n0123456789\n")
    cursor = codeeditor.textCursor()
    cursor.movePosition(
        QTextCursor.MoveOperation.Down,
        QTextCursor.MoveMode.MoveAnchor,
        3
    )
    codeeditor.setTextCursor(cursor)
    click_at(codeeditor, qtbot, 6, ctrl=True, alt=True, shift=True)

    assert bool(codeeditor.extra_cursors)
    assert len(codeeditor.all_cursors) == 4
    for cursor in codeeditor.all_cursors:
        assert cursor.selectedText() == "012345"


def test_settings_toggle(codeeditor, qtbot):
    assert codeeditor.multi_cursor_enabled
    assert codeeditor.cursorWidth() == 0  # required for multi-cursor rendering
    codeeditor.set_text("0123456789\n0123456789\n")
    click_at(codeeditor, qtbot, 6, ctrl=True, alt=True)

    # A cursor was added
    assert bool(codeeditor.extra_cursors)
    codeeditor.toggle_multi_cursor(False)

    # Extra cursors removed on settings toggle
    assert not bool(codeeditor.extra_cursors)
    click_at(codeeditor, qtbot, 3, ctrl=True, alt=True)

    # Extra cursors not added wnen settings "multi-cursor enabled" is False
    assert not bool(codeeditor.extra_cursors)
    click_at(codeeditor, qtbot, 13, ctrl=True, alt=True, shift=True)

    # Column cursors not added wnen settings "multi-cursor enabled" is False
    assert not bool(codeeditor.extra_cursors)


def test_extra_selections_decoration(codeeditor, qtbot):
    codeeditor.set_text("0123456789\n0123456789\n0123456789\n0123456789\n")
    cursor = codeeditor.textCursor()
    cursor.movePosition(
        QTextCursor.MoveOperation.Down,
        QTextCursor.MoveMode.MoveAnchor,
        3  # column 0 row 4
    )
    codeeditor.setTextCursor(cursor)
    click_at(codeeditor, qtbot, 6, ctrl=True, alt=True, shift=True)
    selections = codeeditor.get_extra_selections("extra_cursor_selections")
    assert len(selections) == 3


def test_multi_cursor_verticalMovementX(codeeditor, qtbot):
    # Ensure extra cursors (and primary cursor) keep column position when
    #    moving up and down
    codeeditor.set_text("012345678\n012345678\n\n012345678\n012345678\n")
    click_at(codeeditor, qtbot, 4)
    click_at(codeeditor, qtbot, 14, ctrl=True, alt=True)
    for _ in range(3):
        qtbot.keyClick(codeeditor, Qt.Key.Key_Down)
    assert codeeditor.extra_cursors[0].position() == 25
    assert codeeditor.textCursor().position() == 35
    for _ in range(3):
        qtbot.keyClick(codeeditor, Qt.Key.Key_Up)
    assert codeeditor.extra_cursors[0].position() == 4
    assert codeeditor.textCursor().position() == 14


def test_overwrite_mode(codeeditor, qtbot):
    # Multi-cursor rendering requires overwrite mode be handled manually as
    #    there is no way to hide the primary textCursor with overwriteMode, and
    #    there is no way to sync the blinking of extra cursors with native
    #    rendering.
    codeeditor.set_text("0123456789\n0123456789\n")
    click_at(codeeditor, qtbot, 4)
    qtbot.keyClick(codeeditor, Qt.Key.Key_Insert)
    assert not codeeditor.overwriteMode()
    assert codeeditor.overwrite_mode
    qtbot.keyClick(codeeditor, Qt.Key.Key_A)
    assert codeeditor.toPlainText() == "0123a56789\n0123456789\n"
    click_at(codeeditor, qtbot, 16, ctrl=True, alt=True)
    qtbot.keyClick(codeeditor, Qt.Key.Key_B)
    assert codeeditor.toPlainText() == "0123ab6789\n01234b6789\n"
    qtbot.keyClick(codeeditor, Qt.Key.Key_Insert)
    assert not codeeditor.overwriteMode()
    assert not codeeditor.overwrite_mode
    qtbot.keyClick(codeeditor, Qt.Key.Key_C)
    assert codeeditor.toPlainText() == "0123abc6789\n01234bc6789\n"

# TODO test folded code
    # extra cursor movement (skip past hidden blocks)
    # typing on a folded line (should be read-only)
    # delete & backspace (& delete line shortcut) should delete folded section
    # move/duplicate line up/down should unfold current and previous/next lines
# TODO test drag & drop cursor rendering
# TODO test backspace & smart backspace
# TODO test smart indent, colon insertion, matching () "" ''
# ---- shortcuts
# TODO test code_completion shourcut (ensure disabled)
# TODO test duplicate/move line up/down
# TODO test delete line
# TODO test goto new line
# TODO test goto line number / definition / next cell / previous cell
# TODO test toggle comment, blockcomment, unblockcomment
# TODO test transform to UPPER / lower case
# TODO test indent / unindent
# TODO test start/end of document
# TODO test start/end of line
# TODO test prev/next char/word
# TODO test next/prev warning
# TODO test killring
# TODO test undo/redo
# TODO test cut copy paste
# TODO test delete
# TODO test select all
# TODO test docstring
# TODO test autoformatting
# TODO test enter inline array/table
# TODO test inspect current object
# TODO test last edit location
# TODO test next/prev cursor position
# TODO test run Cell (and advance)
# TODO test run selection (and advance)(from line)(in debugger)


if __name__ == '__main__':
    pytest.main(['test_multicursor.py'])
