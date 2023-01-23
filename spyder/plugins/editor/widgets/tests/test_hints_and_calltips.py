# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
#
"""Tests for editor calltips and hover hints tooltips."""

# Standard library imports
import os
import sys

# Third party imports
from qtpy.QtCore import Qt, QPoint
from qtpy.QtGui import QTextCursor
import pytest

# Local imports
from spyder.plugins.editor.extensions.closebrackets import (
        CloseBracketsExtension)

# Constants
TEST_SIG = 'some_function(foo={}, hello=None)'
TEST_DOCSTRING = "This is the test docstring."
TEST_TEXT = """'''Testing something'''
def {SIG}:
    '''{DOC}'''


some_function""".format(SIG=TEST_SIG, DOC=TEST_DOCSTRING)


@pytest.mark.order(2)
def test_hide_calltip(completions_codeeditor, qtbot):
    """Test that calltips are hidden when a matching ')' is found."""
    code_editor, _ = completions_codeeditor
    code_editor.show()
    code_editor.raise_()
    code_editor.setFocus()

    text = 'a = "sometext {}"\nprint(a.format'
    # Set text to start
    code_editor.set_text(text)
    code_editor.go_to_line(2)
    code_editor.move_cursor(14)
    calltip = code_editor.calltip_widget
    assert not calltip.isVisible()

    with qtbot.waitSignal(code_editor.sig_signature_invoked, timeout=30000):
        qtbot.keyClicks(code_editor, '(', delay=3000)

    qtbot.waitUntil(lambda: calltip.isVisible(), timeout=3000)
    qtbot.keyClicks(code_editor, '"hello"')
    qtbot.keyClicks(code_editor, ')', delay=330)
    assert calltip.isVisible()
    qtbot.keyClicks(code_editor, ')', delay=330)
    qtbot.waitUntil(lambda: not calltip.isVisible(), timeout=3000)
    qtbot.keyClick(code_editor, Qt.Key_Enter, delay=330)
    assert not calltip.isVisible()


@pytest.mark.order(2)
@pytest.mark.parametrize('params', [
            # Parameter, Expected Output
            ('dict', 'dict'),
            ('type', 'type'),
            ('"".format', '-> str'),
            (TEST_TEXT, TEST_SIG)
        ]
    )
def test_get_calltips(qtbot, completions_codeeditor, params):
    """Test that the editor is returning hints."""
    code_editor, _ = completions_codeeditor

    param, expected_output_text = params

    # Set text in editor
    code_editor.set_text(param)

    # Move cursor to end of line
    code_editor.moveCursor(QTextCursor.End)

    code_editor.calltip_widget.hide()

    # Test with brackets autocompletion enable/disable
    bracket_extension = code_editor.editor_extensions.get(
        CloseBracketsExtension)

    # Bracket autocompletion enabled
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

    # Bracket autocompletion disabled
    bracket_extension.enable = False
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

    # Set bracket autocomplete to default value
    bracket_extension.enable = True


@pytest.mark.order(2)
@pytest.mark.skipif(not os.name == 'nt', reason='Only works on Windows')
@pytest.mark.parametrize('params', [
        # Parameter, Expected Output
        ('"".format', '-> str'),
        ('import math', 'module'),
        (TEST_TEXT, TEST_DOCSTRING)
    ]
)
def test_get_hints(qtbot, completions_codeeditor, params, capsys):
    """Test that the editor is returning hover hints."""
    code_editor, _ = completions_codeeditor
    param, expected_output_text = params

    # Move mouse to another position to be sure the hover is displayed when
    # the cursor is put on top of the tested word.
    qtbot.mouseMove(code_editor, QPoint(400, 400))

    # Set text in editor
    code_editor.set_text(param)

    # Get cursor coordinates
    code_editor.moveCursor(QTextCursor.End)
    qtbot.keyPress(code_editor, Qt.Key_Left)

    # Wait a bit in case the window manager repositions the window.
    qtbot.wait(1000)

    # Position cursor on top of word we want the hover for.
    x, y = code_editor.get_coordinates('cursor')
    point = code_editor.calculate_real_position(QPoint(x, y))

    # Get hover and compare
    with qtbot.waitSignal(code_editor.sig_display_object_info,
                          timeout=30000) as blocker:
        qtbot.mouseMove(code_editor, point)
        qtbot.mouseClick(code_editor, Qt.LeftButton, pos=point)
        qtbot.waitUntil(lambda: code_editor.tooltip_widget.isVisible(),
                        timeout=10000)

        args = blocker.args
        print('args:', [args])
        output_text = args[0]
        assert expected_output_text in output_text
        code_editor.tooltip_widget.hide()

        # This checks that code_editor.log_lsp_handle_errors was not called
        captured = capsys.readouterr()
        assert captured.err == ''


@pytest.mark.order(2)
@pytest.mark.skipif(sys.platform == 'darwin', reason='Fails on Mac')
@pytest.mark.parametrize('text', [
        'def test():\n    pass\n\ntest',
        '# a comment',
        '"a string"',
    ]
)
def test_get_hints_not_triggered(qtbot, completions_codeeditor, text):
    """Test that the editor is not returning hover hints for empty docs."""
    code_editor, _ = completions_codeeditor

    # Set text in editor
    code_editor.set_text(text)

    # Move mouse to another position.
    qtbot.mouseMove(code_editor, QPoint(400, 400))

    # Get cursor coordinates
    code_editor.moveCursor(QTextCursor.End)

    for _ in range(3):
        qtbot.keyPress(code_editor, Qt.Key_Left)

    # Wait a bit in case the window manager repositions the window.
    qtbot.wait(1000)

    # Position cursor on top of word we want the hover for.
    x, y = code_editor.get_coordinates('cursor')
    point = code_editor.calculate_real_position(QPoint(x, y))

    # Check that no hover was generated.
    with qtbot.waitSignal(code_editor.completions_response_signal,
                          timeout=30000):
        qtbot.mouseMove(code_editor, point)
        qtbot.mouseClick(code_editor, Qt.LeftButton, pos=point)
        qtbot.wait(1000)
        assert not code_editor.tooltip_widget.isVisible()
