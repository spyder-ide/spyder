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


ControlModifier = Qt.KeyboardModifier.ControlModifier
AltModifier = Qt.KeyboardModifier.AltModifier
ShiftModifier = Qt.KeyboardModifier.ShiftModifier


def click_at(codeeditor, qtbot, position, ctrl=False, alt=False, shift=False):
    """
    Convienience function to generate a mouseClick at a given text position
    with the specified modifiers held.
    """

    x, y = codeeditor.get_coordinates(position)
    point = QPoint(x, y)

    modifiers = Qt.KeyboardModifier.NoModifier
    if ctrl:
        modifiers |= ControlModifier
    if alt:
        modifiers |= AltModifier
    if shift:
        modifiers |= ShiftModifier

    qtbot.mouseClick(
        codeeditor.viewport(),
        Qt.MouseButton.LeftButton,
        modifiers,
        pos=point
    )


def call_shortcut(codeeditor, name):
    """
    Convienience function to call a QShortcut without having to simulate the
    key sequence (which may be different for each platform?)
    """
    context = codeeditor.CONF_SECTION.lower()
    plugin_name = None
    qshortcut = codeeditor._shortcuts[(context, name, plugin_name)]
    qshortcut.activated.emit()


@pytest.mark.order(1)
def test_add_cursor(codeeditor, qtbot):
    """Test adding and removing extra cursors with crtl-alt click"""

    # Enabled by default arg on CodeEditor.setup_editor (which is called in the
    # pytest fixture creation in conftest.py)
    assert codeeditor.multi_cursor_enabled  # This is assumed for other tests
    assert codeeditor.cursorWidth() == 0  # Required for multi-cursor rendering
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

    # Don't add another cursor on top of main cursor
    click_at(codeeditor, qtbot, 7, ctrl=True, alt=True)
    assert not bool(codeeditor.extra_cursors)

    # Test removing cursors
    click_at(codeeditor, qtbot, 2, ctrl=True, alt=True)

    # Remove main cursor
    click_at(codeeditor, qtbot, 2, ctrl=True, alt=True)
    assert codeeditor.textCursor().position() == 7


def test_column_add_cursor(codeeditor, qtbot):
    """Test adding a column of extra cursors with ctrl-alt-shift click"""

    codeeditor.set_text("0123456789\n0123456789\n0123456789\n0123456789\n")
    cursor = codeeditor.textCursor()

    # Move main cursor to bottom left
    cursor.movePosition(
        QTextCursor.MoveOperation.Down,
        QTextCursor.MoveMode.MoveAnchor,
        3
    )
    codeeditor.setTextCursor(cursor)

    # Column cursor click at top row 6th column
    click_at(codeeditor, qtbot, 6, ctrl=True, alt=True, shift=True)

    assert codeeditor.extra_cursors
    assert len(codeeditor.all_cursors) == 4
    for cursor in codeeditor.all_cursors:
        assert cursor.selectedText() == "012345"


def test_settings_toggle(codeeditor, qtbot):
    """Test toggling multicursor support in settings"""

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
    """Ensure text decorations are created to paint extra cursor selections."""

    codeeditor.set_text("0123456789\n0123456789\n0123456789\n0123456789\n")
    cursor = codeeditor.textCursor()
    cursor.movePosition(
        QTextCursor.MoveOperation.Down,
        QTextCursor.MoveMode.MoveAnchor,
        3
    )
    codeeditor.setTextCursor(cursor)
    click_at(codeeditor, qtbot, 6, ctrl=True, alt=True, shift=True)
    selections = codeeditor.get_extra_selections("extra_cursor_selections")
    assert len(selections) == 3


def test_multi_cursor_verticalMovementX(codeeditor, qtbot):
    """Ensure cursors keep their column position when moving up and down."""
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
    """
    Multi-cursor rendering requires overwrite mode be handled manually as there
    is no way to hide the primary textCursor with overwriteMode, and there is
    no way to sync the blinking of extra cursors with native rendering.

    Test overwrite mode (insert key)
    """

    codeeditor.set_text("0123456789\n0123456789\n")
    click_at(codeeditor, qtbot, 4)
    qtbot.keyClick(codeeditor, Qt.Key.Key_Insert)

    # Overwrite mode is tracked manually, ensure the Qt property is False
    assert not codeeditor.overwriteMode()
    assert codeeditor.overwrite_mode

    # Test overwrite mode functionality for single cursor
    qtbot.keyClick(codeeditor, Qt.Key.Key_A)
    assert codeeditor.toPlainText() == "0123a56789\n0123456789\n"

    # Test overwrite mode for multiple cursors
    click_at(codeeditor, qtbot, 16, ctrl=True, alt=True)
    qtbot.keyClick(codeeditor, Qt.Key.Key_B)
    assert codeeditor.toPlainText() == "0123ab6789\n01234b6789\n"

    # Test returning to insert mode
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

# fmt: off
# Disable formatting so that Black/Ruff don't incorrectly format the multiline
# strings below.
def test_smart_text(codeeditor, qtbot):
    """
    Test smart text features: Smart backspace, whitespace insertion, colon
    insertion, parenthesis and quote matching.
    """

    # Closing paren was inserted?
    codeeditor.set_text("def test1\ndef test2\n")
    click_at(codeeditor, qtbot, 9)
    click_at(codeeditor, qtbot, 19, ctrl=True, alt=True)
    qtbot.keyClick(codeeditor, Qt.Key.Key_ParenLeft)
    assert codeeditor.toPlainText() == ("def test1()\ndef test2()\n")

    # Typing close paren advances cursor without adding extra paren?
    qtbot.keyClick(codeeditor, Qt.Key.Key_ParenRight)
    assert codeeditor.toPlainText() == ("def test1()\ndef test2()\n")

    # Auto colon and indent?
    qtbot.keyClick(codeeditor, Qt.Key.Key_Return)
    assert codeeditor.toPlainText() == (
        "def test1():\n"
        "    \n"
        "def test2():\n"
        "    \n"
    )

    # Add some extraneous whitespace
    qtbot.keyClick(codeeditor, Qt.Key.Key_Tab)
    qtbot.keyClick(codeeditor, Qt.Key.Key_Tab)
    assert codeeditor.toPlainText() == (
        "def test1():\n"
        "            \n"
        "def test2():\n"
        "            \n"
    )

    # Smart backspace to correct indent?
    qtbot.keyClick(codeeditor, Qt.Key.Key_Backspace)
    assert codeeditor.toPlainText() == (
        "def test1():\n"
        "    \n"
        "def test2():\n"
        "    \n"
    )

    for cursor in codeeditor.all_cursors:
        cursor.insertText("return")
    assert codeeditor.toPlainText() == (
        "def test1():\n"
        "    return\n"
        "def test2():\n"
        "    return\n"
    )

    # Automatic quote
    codeeditor.set_close_quotes_enabled(True)
    qtbot.keyClick(codeeditor, Qt.Key.Key_Space)
    qtbot.keyClick(codeeditor, Qt.Key.Key_Apostrophe)
    assert codeeditor.toPlainText() == (
        "def test1():\n"
        "    return ''\n"
        "def test2():\n"
        "    return ''\n"
    )

    # Automatic close quote
    qtbot.keyClick(codeeditor, Qt.Key.Key_Apostrophe)
    assert codeeditor.toPlainText() == (
        "def test1():\n"
        "    return ''\n"
        "def test2():\n"
        "    return ''\n"
    )

    # Automatic dedent?
    qtbot.keyClick(codeeditor, Qt.Key.Key_Return)
    assert codeeditor.toPlainText() == (
        "def test1():\n"
        "    return ''\n"
        "\n"
        "def test2():\n"
        "    return ''\n"
        "\n"
    )

# fmt: on

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

def test_move_line(codeeditor, qtbot):
    """Test multi-cursor move line up and down shortcut"""

    codeeditor.set_text("\n".join("123456"))
    click_at(codeeditor, qtbot, 4, ctrl=True, alt=True)

    call_shortcut(codeeditor, "move line down")
    call_shortcut(codeeditor, "move line down")
    assert codeeditor.toPlainText() == "\n".join("241536")

    call_shortcut(codeeditor, "move line up")
    assert codeeditor.toPlainText() == "\n".join("214356")


def test_duplicate_line(codeeditor, qtbot):
    """Test multi-cursor duplicate line up and down shortcut"""

    codeeditor.set_text("\n".join("123456"))
    click_at(codeeditor, qtbot, 4, ctrl=True, alt=True)

    call_shortcut(codeeditor, "duplicate line down")
    assert codeeditor.toPlainText() == "\n".join("11233456")
    assert codeeditor.textCursor().position() == 8
    assert codeeditor.extra_cursors[0].position() == 2

    call_shortcut(codeeditor, "duplicate line up")
    assert codeeditor.toPlainText() == "\n".join("1112333456")
    assert codeeditor.textCursor().position() == 10
    assert codeeditor.extra_cursors[0].position() == 2


def test_delete_line(codeeditor, qtbot):
    """Test delete line shortcut"""

    codeeditor.set_text("\n".join("123456"))
    click_at(codeeditor, qtbot, 4, ctrl=True, alt=True)
    call_shortcut(codeeditor, "delete line")
    assert codeeditor.toPlainText() == "\n".join("2456")


def test_goto_new_line(codeeditor, qtbot):
    """Test 'go to new line' shortcut"""

    codeeditor.set_text("\n".join("123456"))
    click_at(codeeditor, qtbot, 4, ctrl=True, alt=True)
    call_shortcut(codeeditor, "go to new line")
    assert codeeditor.toPlainText() == "1\n\n2\n3\n\n4\n5\n6"


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
