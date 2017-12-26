# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License


# Standard library imports
import os

# Third party imports
from qtpy.QtCore import QPoint, Qt
from qtpy.QtGui import QFont

import pytest

# Local imports
from spyder.widgets.sourcecode.codeeditor import CodeEditor
from qtpy import PYQT4


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def editor_bot(qtbot):
    widget = CodeEditor(None)
    widget.setup_editor(linenumbers=True,
                        markers=True,
                        show_blanks=True,
                        scrollflagarea=True,
                        font=QFont("Courier New", 10),
                        color_scheme='Zenburn',
                        language='Python')
    # qtbot.addWidget(widget)
    return qtbot, widget


# ---------------------------------------------------------------------------
# Examples to Test Against
# ---------------------------------------------------------------------------
long_code = """Line1
Line2
Line3
Line4
Line5
Line6
Line7
Line8
Line9
Line10
Line11
Line12
Line13
Line14
Line15
Line16
Line17
Line18
Line19
Line20
"""

short_code = """line1: Occurences
line2: Breakpoints
line3: TODOs
line4: Code Analysis: warning
line5: Code Analysis: error
line6: Found Results
"""


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_enabled(editor_bot):
    """"Test that enabling and disabling the srollflagarea panel make
    it visible or invisible depending on the case."""
    qtbot, editor = editor_bot
    sfa = editor.scrollflagarea
    editor.show()
    editor.set_text(short_code)

    assert sfa.isVisible()
    sfa.set_enabled(False)
    assert not sfa.isVisible()


def test_flag_painting(editor_bot):
    """"Test that there is no error when painting all flag types on the
    scrollbar area when the editor vertical scrollbar is visible and not
    visible. There is seven different flags: breakpoints, todos, warnings,
    errors, found_results, and occurences"""
    qtbot, editor = editor_bot
    sfa = editor.scrollflagarea

    editor.resize(450, 300)
    editor.show()

    # Set a short text in the editor and assert that the slider is not visible.
    editor.set_text(short_code)
    qtbot.waitUntil(lambda: not sfa.slider)

    # Trigger the painting of all flag types.
    editor.add_remove_breakpoint(line_number=2)
    editor.process_todo([[True, 3]])
    editor.process_code_analysis([['E227 warning', 4], ['syntax error', 5]])
    editor.highlight_found_results('line6')
    with qtbot.waitSignal(editor.sig_flags_changed, raising=True,
                          timeout=5000):
        cursor = editor.textCursor()
        cursor.setPosition(2)
        editor.setTextCursor(cursor)

    # Set a long text in the editor and assert that the slider is visible.
    editor.set_text(long_code)
    qtbot.waitUntil(lambda: sfa.slider)

    # Trigger the painting of all flag types.
    editor.add_remove_breakpoint(line_number=2)
    editor.process_todo([[True, 3]])
    editor.process_code_analysis([['E227 warning', 4], ['syntax error', 5]])
    editor.highlight_found_results('line6')
    with qtbot.waitSignal(editor.sig_flags_changed, raising=True,
                          timeout=5000):
        cursor = editor.textCursor()
        cursor.setPosition(2)
        editor.setTextCursor(cursor)


def test_range_indicator_visible_on_hover_only(editor_bot):
    """Test that the slider range indicator is visible only when hovering
    over the scrollflag area when the editor vertical scrollbar is visible.
    The scrollflag area should remain hidden at all times when the editor
    vertical scrollbar is not visible."""
    qtbot, editor = editor_bot
    sfa = editor.scrollflagarea

    editor.resize(450, 300)
    editor.show()

    # Set a short text in the editor and assert that the slider is not visible.
    editor.set_text(short_code)
    qtbot.waitUntil(lambda: not sfa.slider)

    # Move the mouse cursor to the center of the scrollflagarea and assert
    # that the slider range indicator remains hidden. The slider range
    # indicator should remains hidden at all times when the vertical scrollbar
    # of the editor is not visible.
    x = sfa.width()/2
    y = sfa.height()/2
    qtbot.mouseMove(sfa, pos=QPoint(x, y), delay=-1)

    assert sfa._range_indicator_is_visible is False

    # Set a long text in the editor and assert that the slider is visible.
    editor.set_text(long_code)
    qtbot.waitUntil(lambda: sfa.slider)

    # Move the mouse cursor to the center of the scrollflagarea and assert
    # that the slider range indicator is now shown. When the vertical scrollbar
    # of the editor is visible, the slider range indicator should be visible
    # only when the mouse cursor hover above the scrollflagarea.
    x = sfa.width()/2
    y = sfa.height()/2
    qtbot.mouseMove(sfa, pos=QPoint(x, y), delay=-1)

    assert sfa._range_indicator_is_visible is True

    # Move the mouse cursor outside of the scrollflagarea and assert that the
    # slider range indicator becomes hidden.
    x = editor.width()/2
    y = editor.height()/2
    qtbot.mouseMove(editor, pos=QPoint(x, y), delay=-1)
    qtbot.waitUntil(lambda: not sfa._range_indicator_is_visible)


@pytest.mark.skipif(PYQT4, reason="It segfaults frequently")
def test_range_indicator_alt_modifier_response(editor_bot):
    """Test that the slider range indicator is visible while the alt key is
    held down while the cursor is over the editor, but outside of the
    scrollflag area. In addition, while the alt key is held down, mouse
    click events in the editor should be forwarded to the scrollfag area and
    should set the value of the editor vertical scrollbar."""
    qtbot, editor = editor_bot
    sfa = editor.scrollflagarea
    sfa._unit_testing = True
    vsb = editor.verticalScrollBar()

    editor.resize(600, 300)
    editor.show()

    # Set a long text in the editor and assert that the slider is visible.
    editor.set_text(long_code)
    qtbot.waitUntil(lambda: sfa.slider)

    # Set the cursor position to the center of the editor.
    w = editor.width()
    h = editor.height()
    qtbot.mousePress(editor, Qt.LeftButton, pos=QPoint(w/2, h/2))

    # Hold the alt key and assert that the slider range indicator is visible.
    # Because it is not possible to simulate the action of holding the alt
    # key down in pytest-qt, this is done through a flag in the ScrollFlagArea
    # that is set to True when pressing the alt key and to false when releasing
    # it. This flag is only used for testing purpose.
    qtbot.keyPress(editor, Qt.Key_Alt)
    qtbot.waitUntil(lambda: sfa._range_indicator_is_visible)

    # While the alt key is pressed, click with the mouse in the middle of the
    # editor's height and assert that the editor vertical scrollbar has moved
    # to its middle range position.
    with qtbot.waitSignal(editor.sig_alt_left_mouse_pressed, raising=True):
        qtbot.mousePress(editor.viewport(), Qt.LeftButton,
                         pos=QPoint(w/2, h/2), modifier=Qt.AltModifier)
    assert vsb.value() == (vsb.minimum()+vsb.maximum())//2

    # While the alt key is pressed, click with the mouse at the top of the
    # editor's height and assert that the editor vertical scrollbar has moved
    # to its minimum position.
    with qtbot.waitSignal(editor.sig_alt_left_mouse_pressed, raising=True):
        qtbot.mousePress(editor.viewport(), Qt.LeftButton,
                         pos=QPoint(w/2, 1), modifier=Qt.AltModifier)
    assert vsb.value() == vsb.minimum()

    # While the alt key is pressed, click with the mouse at the bottom of the
    # editor's height and assert that the editor vertical scrollbar has moved
    # to its maximum position.
    with qtbot.waitSignal(editor.sig_alt_left_mouse_pressed, raising=True):
        qtbot.mousePress(editor.viewport(), Qt.LeftButton,
                         pos=QPoint(w/2, h-1), modifier=Qt.AltModifier)
    assert vsb.value() == vsb.maximum()

    # Release the alt key and assert that the slider range indicator is
    # not visible.
    qtbot.keyRelease(editor, Qt.Key_Alt)
    qtbot.waitUntil(lambda: not sfa._range_indicator_is_visible, timeout=3000)


if __name__ == "__main__":                                   # pragma: no cover
    pytest.main([os.path.basename(__file__)])
    # pytest.main()
