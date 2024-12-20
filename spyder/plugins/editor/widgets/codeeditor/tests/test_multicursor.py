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
    point = QPoint(x, y)

    modifiers = Qt.KeyboardModifier.NoModifier
    if ctrl:
        modifiers |= Qt.KeyboardModifier.ControlModifier
    if alt:
        modifiers |= Qt.KeyboardModifier.AltModifier
    if shift:
        modifiers |= Qt.KeyboardModifier.ShiftModifier
    qtbot.mouseClick(codeeditor.viewport(),
                     Qt.MouseButton.LeftButton,
                     modifiers,
                     pos=point)


def test_add_cursor(codeeditor, qtbot):
    # enabled by default arg on CodeEditor.setup_editor (which is called in the
    #    pytest fixture creation in conftest.py)
    assert codeeditor.multi_cursor_enabled
    assert codeeditor.cursorWidth() == 0  # required for multi-cursor rendering
    codeeditor.set_text("0123456789")
    click_at(codeeditor, qtbot, 6, ctrl=True, alt=True)
    # A cursor was added
    assert bool(codeeditor.extra_cursors)
    qtbot.keyClick(codeeditor, "a")
    # Text was inserted correctly from two cursors
    assert codeeditor.toPlainText() == "a012345a6789"

    # regular click to set main cursor and clear extra cursors
    click_at(codeeditor, qtbot, 6)
    assert not bool(codeeditor.extra_cursors)
    qtbot.keyClick(codeeditor, "b")
    assert codeeditor.toPlainText() == "a01234b5a6789"
    # don't add another cursor on top of main cursor
    click_at(codeeditor, qtbot, 7, ctrl=True, alt=True)
    assert not bool(codeeditor.extra_cursors)

    # test removing cursors
    click_at(codeeditor, qtbot, 2, ctrl=True, alt=True)
    # remove main cursor
    click_at(codeeditor, qtbot, 2, ctrl=True, alt=True)
    assert codeeditor.textCursor().position() == 7


def test_column_add_cursor(codeeditor, qtbot):
    codeeditor.set_text("0123456789\n0123456789\n0123456789\n0123456789\n")
    cursor = codeeditor.textCursor()
    cursor.movePosition(QTextCursor.MoveOperation.Down,
                        QTextCursor.MoveMode.MoveAnchor,
                        3)
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
    cursor.movePosition(QTextCursor.MoveOperation.Down,
                        QTextCursor.MoveMode.MoveAnchor,
                        3)  # column 0 row 4
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
#    extra cursor movement (skip past hidden blocks)
#    typing on a folded line (should be read-only)
#    delete & backspace (& delete line shortcut) should delete folded section
#    move/duplicate line up/down should unfold current and previous/next lines


# def test_drag_and_drop(codeeditor, qtbot):
#     # test drag & drop cursor rendering
#     codeeditor.set_text("0123456789\nabcdefghij\n")
#     cursor = codeeditor.textCursor()
#     cursor.movePosition(cursor.MoveOperation.NextBlock,
#                         cursor.MoveMode.KeepAnchor)

#     assert codeeditor._drag_cursor is None
#     point = QPoint(*codeeditor.get_coordinates(5))
#     qtbot.mousePress(codeeditor.viewport(),
#                      Qt.MouseButton.LeftButton,
#                      pos=point)

#     point = QPoint(*codeeditor.get_coordinates(22))
#     # TODO not working: this doesn't generate a DragEnter event or DragMove
#     #    events. Why?
#     qtbot.mouseMove(codeeditor.viewport(),
#                     pos=point)
#     assert codeeditor._drag_cursor is not None
#     qtbot.mouseRelease(codeeditor.viewport(),
#                        Qt.MouseButton.LeftButton,
#                        pos=point)
#     assert codeeditor._drag_cursor is None
#     assert codeeditor.toPlainText() == "abcdefghij\n0123456789\n"

def test_smart_text(codeeditor, qtbot):
    # test smart backspace, whitespace insertion, colon insertion, and
    #    parenthesis/quote matching
    codeeditor.set_text("def test1\n"
                        "def test2\n")
    click_at(codeeditor, qtbot, 9)
    click_at(codeeditor, qtbot, 19, ctrl=True, alt=True)
    qtbot.keyClick(codeeditor, Qt.Key.Key_ParenLeft)
    # closing paren was inserted?
    assert codeeditor.toPlainText() == ("def test1()\n"
                                        "def test2()\n")
    qtbot.keyClick(codeeditor, Qt.Key.Key_ParenRight)
    # typing close paren advances cursor without adding extra paren?
    assert codeeditor.toPlainText() == ("def test1()\n"
                                        "def test2()\n")
    qtbot.keyClick(codeeditor, Qt.Key.Key_Return)
    # auto colon and indent?
    assert codeeditor.toPlainText() == ("def test1():\n"
                                        "    \n"
                                        "def test2():\n"
                                        "    \n")
    # add some extraneous whitespace
    qtbot.keyClick(codeeditor, Qt.Key.Key_Tab)
    qtbot.keyClick(codeeditor, Qt.Key.Key_Tab)
    assert codeeditor.toPlainText() == ("def test1():\n"
                                        "            \n"
                                        "def test2():\n"
                                        "            \n")
    qtbot.keyClick(codeeditor, Qt.Key.Key_Backspace)
    # smart backspace to correct indent?
    assert codeeditor.toPlainText() == ("def test1():\n"
                                        "    \n"
                                        "def test2():\n"
                                        "    \n")
    for cursor in codeeditor.all_cursors:
        cursor.insertText("return")
    assert codeeditor.toPlainText() == ("def test1():\n"
                                        "    return\n"
                                        "def test2():\n"
                                        "    return\n")
    codeeditor.set_close_quotes_enabled(True)
    qtbot.keyClick(codeeditor, Qt.Key.Key_Space)
    qtbot.keyClick(codeeditor, Qt.Key.Key_Apostrophe)
    # automatic quote
    assert codeeditor.toPlainText() == ("def test1():\n"
                                        "    return ''\n"
                                        "def test2():\n"
                                        "    return ''\n")
    qtbot.keyClick(codeeditor, Qt.Key.Key_Apostrophe)
    # automatic close quote
    assert codeeditor.toPlainText() == ("def test1():\n"
                                        "    return ''\n"
                                        "def test2():\n"
                                        "    return ''\n")
    qtbot.keyClick(codeeditor, Qt.Key.Key_Return)
    # automatic dedent?
    assert codeeditor.toPlainText() == ("def test1():\n"
                                        "    return ''\n"
                                        "\n"
                                        "def test2():\n"
                                        "    return ''\n"
                                        "\n")


# ---- shortcuts

# def test_disable_code_completion(completions_codeeditor, qtbot):
#     code_editor, _ = completions_codeeditor
#     code_editor.set_text("def test1():\n"
#                          "    return\n")
#     completion = code_editor.completion_widget
#     delay = 50
#     code_editor.toggle_code_snippets(False)

#     code_editor.moveCursor(QTextCursor.MoveOperation.End)
#     qtbot.keyClicks(code_editor, "tes", delay=delay)
#     qtbot.wait(2000)  # keyboard idle + wait for completion time
#     assert not completion.isHidden()
#     # TODO doesn't hide completions, why?
#     qtbot.keyClick(code_editor, Qt.Key.Key_Escape)
#     # TODO doesn't hide completions, why?
#     click_at(code_editor, qtbot, 0)
#     qtbot.wait(1000)
#     click_at(code_editor, qtbot, 27, ctrl=True, alt=True)
#     qtbot.keyClicks(code_editor, "t", delay=delay)
#     qtbot.wait(1000)  # keyboard idle + wait for completion time
#     # XXX fails because first completions box is never hidden.
#     assert completion.isHidden()
#     # TODO test ctrl-space shortcut too


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
