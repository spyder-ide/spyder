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
    qtbot.addWidget(widget)
    return qtbot, widget


# ---------------------------------------------------------------------------
# Examples to Test Against
# ---------------------------------------------------------------------------
long_code = """Line 1
Line 2
Line 3
Line 4
Line 5
Line 6
Line 7
Line 8
Line 9
Line 10
Line 11
Line 12
Line 13
Line 14
Line 15
Line 16
Line 17
Line 18
Line 19
Line 20
"""

short_code = """line1: Occurences
line2: Breakpoints
line3: TODOs
line4: Code Analysis
line5: Found Results
"""


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_enabled(editor_bot):
    qtbot, editor = editor_bot
    sfa = editor.scrollflagarea
    editor.show()
    editor.set_text(short_code)

    assert sfa.isVisible()
    sfa.set_enabled(False)
    assert not sfa.isVisible()


def test_flag_painting(editor_bot):
    qtbot, editor = editor_bot
    sfa = editor.scrollflagarea

    editor.resize(450, 300)
    editor.show()

    # Check that the slider is not visible.
    editor.set_text(short_code)
    qtbot.waitUntil(lambda: not sfa.slider)

    # Trigger the painting of all flag types.
    editor.add_remove_breakpoint(line_number=2)
    editor.process_todo([[True, 3]])
    editor.process_code_analysis([['dummy text', 4]])
    editor.highlight_found_results('line5')
    with qtbot.waitSignal(editor.sig_flags_changed, raising=True,
                          timeout=5000):
        cursor = editor.textCursor()
        cursor.setPosition(2)
        editor.setTextCursor(cursor)

    # Check that the slider is not visible.
    editor.set_text(long_code)
    qtbot.waitUntil(lambda: sfa.slider)

    # Trigger the painting of all flag types.
    editor.add_remove_breakpoint(line_number=2)
    editor.process_todo([[True, 3]])
    editor.process_code_analysis([['dummy text', 4]])
    editor.highlight_found_results('line5')
    with qtbot.waitSignal(editor.sig_flags_changed, raising=True,
                          timeout=5000):
        cursor = editor.textCursor()
        cursor.setPosition(2)
        editor.setTextCursor(cursor)


def test_range_indicator_visible_on_hover_only(editor_bot):
    qtbot, editor = editor_bot
    sfa = editor.scrollflagarea

    editor.resize(450, 300)
    editor.show()

    # Check that the slider is not visible.
    editor.set_text(short_code)
    qtbot.waitUntil(lambda: not sfa.slider)

    x = sfa.width()/2
    y = sfa.height()/2
    qtbot.mouseMove(sfa, pos=QPoint(x, y), delay=-1)

    assert sfa._range_indicator_is_visible is False

    editor.set_text(long_code)
    qtbot.waitUntil(lambda: sfa.slider)

    x = sfa.width()/2
    y = sfa.height()/2
    qtbot.mouseMove(sfa, pos=QPoint(x, y), delay=-1)

    assert sfa._range_indicator_is_visible is True

    x = editor.width()/2
    y = editor.height()/2
    qtbot.mouseMove(editor, pos=QPoint(x, y), delay=-1)
    qtbot.waitUntil(lambda: not sfa._range_indicator_is_visible)


def test_range_indicator_alt_modifier_response(editor_bot):
    qtbot, editor = editor_bot
    sfa = editor.scrollflagarea
    sfa._unit_testing = True
    vsb = editor.verticalScrollBar()

    editor.show()
    editor.set_text(long_code)

    # Resize the editor and check that the slider is visible.
    editor.resize(600, 300)
    qtbot.waitUntil(lambda: sfa.slider)

    w = editor.width()
    h = editor.height()
    qtbot.mousePress(editor, Qt.LeftButton, pos=QPoint(w/2, h/2))

    qtbot.keyPress(editor, Qt.Key_Alt)
    qtbot.waitUntil(lambda: sfa._range_indicator_is_visible)

    with qtbot.waitSignal(editor.sig_alt_left_mouse_pressed, raising=True):
        qtbot.mousePress(editor.viewport(), Qt.LeftButton,
                         pos=QPoint(w/2, h/2), modifier=Qt.AltModifier)
    assert vsb.value() == (vsb.minimum()+vsb.maximum())//2

    with qtbot.waitSignal(editor.sig_alt_left_mouse_pressed, raising=True):
        qtbot.mousePress(editor.viewport(), Qt.LeftButton,
                         pos=QPoint(w/2, 1), modifier=Qt.AltModifier)
    assert vsb.value() == vsb.minimum()

    with qtbot.waitSignal(editor.sig_alt_left_mouse_pressed, raising=True):
        qtbot.mousePress(editor.viewport(), Qt.LeftButton,
                         pos=QPoint(w/2, h-1), modifier=Qt.AltModifier)
    assert vsb.value() == vsb.maximum()

    qtbot.keyRelease(editor, Qt.Key_Alt)
    qtbot.waitUntil(lambda: not sfa._range_indicator_is_visible, timeout=3000)


if __name__ == "__main__":                                   # pragma: no cover
    pytest.main([os.path.basename(__file__)])
    # pytest.main()
