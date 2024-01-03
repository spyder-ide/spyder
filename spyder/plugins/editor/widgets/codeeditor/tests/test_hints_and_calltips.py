# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
#

"""Tests for editor calltips, hovers and hints."""

# Standard library imports
import os
import sys

# Third party imports
from qtpy.QtCore import Qt, QPoint
from qtpy.QtGui import QTextCursor
import pytest

# Local imports
from spyder.config.base import running_in_ci, running_in_ci_with_conda
from spyder.plugins.editor.extensions.closebrackets import (
    CloseBracketsExtension
)

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

    # Position cursor on top of the word we want the hover for.
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


@pytest.mark.order(2)
@pytest.mark.skipif(
    (
        sys.platform == "darwin"
        or (
            sys.platform.startswith("linux") and not running_in_ci_with_conda()
        )
    ),
    reason="Fails on Linux with pip packages and Mac",
)
@pytest.mark.parametrize(
    "params",
    [
        ("an_int = 10", "This is an integer"),
        ("a_dict = {1: 2}", "This is a dictionary"),
        ('a_string = "foo"', "This is a string"),
    ],
)
def test_get_hints_for_builtins(qtbot, completions_codeeditor, params):
    """Test that the editor is showing the right hover hints for builtins."""
    code_editor, _ = completions_codeeditor
    text, expected = params

    # Set text in editor
    code_editor.set_text(text)

    # Move mouse to another position.
    qtbot.mouseMove(code_editor, QPoint(400, 400))

    # Move cursor at the beginning of the last line
    code_editor.moveCursor(QTextCursor.End)
    code_editor.moveCursor(QTextCursor.StartOfLine)

    for _ in range(3):
        qtbot.keyPress(code_editor, Qt.Key_Right)

    # Wait a bit in case the window manager repositions the window.
    qtbot.wait(1000)

    # Position cursor on top of the word we want the hover for.
    x, y = code_editor.get_coordinates('cursor')
    point = code_editor.calculate_real_position(QPoint(x, y))

    # Check the generated hover.
    with qtbot.waitSignal(
        code_editor.sig_display_object_info, timeout=30000
    ):
        # Give focus to the editor
        qtbot.mouseClick(code_editor, Qt.LeftButton, pos=point)

        # These two mouse moves are necessary to ensure the hover is shown.
        qtbot.mouseMove(code_editor, point)
        qtbot.mouseMove(
            code_editor,
            QPoint(point.x() + 2, point.y() + 2),
            delay=100
        )

        # Check hover is shown and contains the expected text
        qtbot.waitUntil(code_editor.tooltip_widget.isVisible, timeout=10000)
        assert expected in code_editor.tooltip_widget.text()


@pytest.mark.order(2)
@pytest.mark.skipif(
    (
        sys.platform == "darwin"
        or (
            sys.platform.startswith("linux") and not running_in_ci_with_conda()
        )
    ),
    reason="Fails on Linux with pip packages and Mac",
)
@pytest.mark.parametrize(
    "params",
    [
        ("import pandas as pd\npd.DataFrame", "bottom"),
        ("\n" * 15 + "import pandas as pd\npd.DataFrame", "top"),
    ],
)
def test_hints_vertical_position(qtbot, completions_codeeditor, params):
    """
    Test that we show hovers at the top or bottom of the text according to
    its length and text positioning in the editor.
    """
    code_editor, _ = completions_codeeditor
    text, expected = params

    # Set text in editor
    code_editor.set_text(text)

    # Move mouse to another position.
    qtbot.mouseMove(code_editor, QPoint(400, 400))

    # Move cursor at the beginning of the last line
    code_editor.moveCursor(QTextCursor.End)
    code_editor.moveCursor(QTextCursor.StartOfLine)

    for _ in range(4):
        qtbot.keyPress(code_editor, Qt.Key_Right)

    # Wait a bit in case the window manager repositions the window.
    qtbot.wait(1000)

    # Position cursor on top of the word we want the hover for.
    x, y = code_editor.get_coordinates('cursor')
    point = code_editor.calculate_real_position(QPoint(x, y))

    # Check the generated hover.
    with qtbot.waitSignal(
        code_editor.sig_display_object_info, timeout=30000
    ):
        # Give focus to the editor
        qtbot.mouseClick(code_editor, Qt.LeftButton, pos=point)

        # These two mouse moves are necessary to ensure the hover is shown.
        qtbot.mouseMove(code_editor, point)
        qtbot.mouseMove(
            code_editor,
            QPoint(point.x() + 2, point.y() + 2),
            delay=100
        )

        qtbot.waitUntil(code_editor.tooltip_widget.isVisible, timeout=10000)

        # Check hover is shown in the right position
        global_point = code_editor._calculate_position(at_point=point)
        if expected == "top":
            assert code_editor.tooltip_widget.pos().y() < global_point.y()
        else:
            assert code_editor.tooltip_widget.pos().y() > global_point.y()


@pytest.mark.order(2)
@pytest.mark.skipif(
    running_in_ci() and not os.name == 'nt',
    reason="Only works on Windows"
)
def test_completion_hints(qtbot, completions_codeeditor):
    """Test that the editor is returning hover hints."""
    code_editor, _ = completions_codeeditor
    completion_widget = code_editor.completion_widget
    tooltip_widget = code_editor.tooltip_widget

    # Move mouse to another position to be sure the hover is displayed when
    # the cursor is put on top of the tested word.
    qtbot.mouseMove(code_editor, QPoint(400, 400))

    # Set text in editor
    code_editor.set_text("import pandas as pd\npd.")

    # Wait a bit in case the window manager repositions the window.
    qtbot.wait(1000)

    # Trigger a code completion
    with qtbot.waitSignal(
        code_editor.completions_response_signal,
        timeout=30000
    ):
        # Get completions
        code_editor.moveCursor(QTextCursor.End)
        qtbot.keyPress(code_editor, Qt.Key_Tab)

    # Check the hint is shown and placed where it should be
    qtbot.waitUntil(tooltip_widget.isVisible)
    assert tooltip_widget.is_hint()
    assert (
        (completion_widget.x() + completion_widget.width() - 1)
        == tooltip_widget.x()
    )
    assert completion_widget.y() == tooltip_widget.y()

    # Move mouse to be on top of the hint
    x, y = code_editor.get_coordinates('cursor')
    point = code_editor.calculate_real_position(QPoint(x, y))
    hint_point = QPoint(
        point.x() + completion_widget.width() + 60,
        point.y() + 60
    )
    qtbot.mouseMove(code_editor, hint_point, delay=100)

    # Do a click on top of the hint and check it doesn't hide.
    with qtbot.waitSignal(
        tooltip_widget.sig_completion_help_requested,
        timeout=30000
    ):
        qtbot.mouseClick(tooltip_widget, Qt.LeftButton, pos=hint_point)

    qtbot.wait(200)
    assert tooltip_widget.isVisible()

    # Move cursor out of the hint and check it's still visible
    qtbot.mouseMove(
        code_editor,
        QPoint(hint_point.x(), hint_point.y() + tooltip_widget.height() + 20),
        delay=100
    )

    qtbot.wait(200)
    assert tooltip_widget.isVisible()

    # Move cursor to the line number area and check hint is still visible
    code_editor.moveCursor(QTextCursor.StartOfLine)
    x, y = code_editor.get_coordinates('cursor')
    point_1 = code_editor.calculate_real_position(QPoint(x, y))

    qtbot.mouseMove(
        code_editor,
        QPoint(
            point_1.x() - code_editor.linenumberarea.width() // 2, point_1.y()
        ),
        delay=100,
    )

    qtbot.wait(200)
    assert tooltip_widget.isVisible()

    # Hide completion widget and check hint is hidden too.
    completion_widget.hide()
    qtbot.waitUntil(lambda: not tooltip_widget.isVisible(), timeout=500)
