# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
#
"""Tests for editor calltips and hover hints tooltips."""

# Standard library imports
import sys

# Third party imports
from qtpy.QtCore import Qt, QPoint
from qtpy.QtGui import QTextCursor
import pytest

# Constants
PY2 = sys.version[0] == '2'
TEST_SIG = 'some_function(foo={}, hello=None)'
TEST_DOCSTRING = "This is the test docstring."
TEST_TEXT = """'''Testing something'''
def {SIG}:
    '''{DOC}'''


some_function""".format(SIG=TEST_SIG, DOC=TEST_DOCSTRING)


@pytest.mark.slow
@pytest.mark.second
def test_hide_calltip(lsp_codeeditor, qtbot):
    """Test that calltips are hidden when a matching ')' is found."""
    code_editor, _ = lsp_codeeditor

    text = 'a = [1,2,3]\n(max'
    # Set text to start
    code_editor.set_text(text)
    code_editor.go_to_line(2)
    code_editor.move_cursor(4)
    calltip = code_editor.calltip_widget
    assert not calltip.isVisible()

    with qtbot.waitSignal(code_editor.sig_signature_invoked, timeout=30000):
        qtbot.keyPress(code_editor, Qt.Key_ParenLeft, delay=3000)

    qtbot.waitUntil(lambda: calltip.isVisible(), timeout=3000)
    qtbot.keyPress(code_editor, Qt.Key_ParenRight, delay=1000)
    qtbot.keyPress(code_editor, Qt.Key_Space)
    qtbot.waitUntil(lambda: not calltip.isVisible(), timeout=3000)
    qtbot.keyPress(code_editor, Qt.Key_ParenRight, delay=1000)
    qtbot.keyPress(code_editor, Qt.Key_Enter, delay=1000)


@pytest.mark.slow
@pytest.mark.second
@pytest.mark.parametrize('params', [
            # Parameter, Expected Output
            ('dict', 'dict'),
            ('type', 'type'),
            ('"".format', '-> str'),
            (TEST_TEXT, TEST_SIG)
        ]
    )
def test_get_calltips(qtbot, lsp_codeeditor, params):
    """Test that the editor is returning hints."""
    code_editor, _ = lsp_codeeditor

    param, expected_output_text = params

    # Set text in editor
    code_editor.set_text(param)

    # Move cursor to end of line
    code_editor.moveCursor(QTextCursor.End)

    code_editor.calltip_widget.hide()
    with qtbot.waitSignal(code_editor.sig_signature_invoked,
                          timeout=30000) as blocker:
        qtbot.keyPress(code_editor, Qt.Key_ParenLeft, delay=1000)

        # This is needed to leave time for the calltip to appear
        # and make the tests succeed
        qtbot.wait(2000)

        args = blocker.args
        print('args:', [args])
        output_text = args[0]['signatures']['label']
        assert expected_output_text in output_text
        code_editor.calltip_widget.hide()


@pytest.mark.slow
@pytest.mark.second
@pytest.mark.parametrize('params', [
            # Parameter, Expected Output
            ('dict', '' if PY2 else 'dict'),
            ('type', 'type'),
            ('"".format', '-> str'),
            ('import math', 'module'),
            (TEST_TEXT, TEST_DOCSTRING)
        ]
    )
def test_get_hints(qtbot, lsp_codeeditor, params):
    """Test that the editor is returning hover hints."""
    code_editor, _ = lsp_codeeditor
    param, expected_output_text = params

    # Set text in editor
    code_editor.set_text(param)

    # Moe cursor to end of line
    code_editor.moveCursor(QTextCursor.End)

    # Get cursor coordinates
    x, y = code_editor.get_coordinates('cursor')
    # The `- 5` is to put the mouse on top of the word
    point = code_editor.calculate_real_position(QPoint(x - 5, y))

    code_editor.tooltip_widget.hide()
    with qtbot.waitSignal(code_editor.sig_display_object_info,
                          timeout=30000) as blocker:
        cursor = code_editor.cursorForPosition(point)
        line, col = cursor.blockNumber(), cursor.columnNumber()
        code_editor.request_hover(line, col)

        # This is needed to leave time for the tooltip to appear
        # and make the tests succeed
        qtbot.wait(2000)

        args = blocker.args
        print('args:', [args])
        output_text = args[0]
        assert expected_output_text in output_text
        code_editor.tooltip_widget.hide()
