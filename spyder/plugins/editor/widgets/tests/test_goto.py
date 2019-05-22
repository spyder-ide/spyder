# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
#
"""Tests for editor URI and mailto go to handling."""

# Standard library imports
import os
import tempfile

# Third party imports
from qtpy.QtCore import Qt, QPoint
from qtpy.QtGui import QTextCursor
import pytest

# Constants
TEST_FOLDER = os.path.abspath(os.path.dirname(__file__))
_, TEMPFILE_PATH = tempfile.mkstemp()
TEST_FILE_TEXT = '"file://{}"\n'.format(TEMPFILE_PATH)


@pytest.mark.parametrize('params', [
            # Parameter, Expected output
            # --------------------------
            # Urls
            ('" https://google.com"\n', 'https://google.com'),  # String
            ('# https://google.com"\n', 'https://google.com'),  # Comment
            # Files that exist
            (TEST_FILE_TEXT, TEMPFILE_PATH),  # File without spaces
            # Mail to
            ('" mailto:goanpeca@gmail.com"\n', 'mailto:goanpeca@gmail.com'),
            ('# mailto:goanpeca@gmail.com\n', 'mailto:goanpeca@gmail.com'),
        ]
    )
def test_goto_uri(qtbot, code_editor_bot, params):
    """Test that the uri search is working correctly."""
    code_editor, _ = code_editor_bot
    code_editor.show()

    param, expected_output_text = params

    # Set text in editor
    code_editor.set_text(param)

    # Get cursor coordinates
    code_editor.moveCursor(QTextCursor.Start)
    x, y = code_editor.get_coordinates('cursor')

    # The `+ 23` is to put the mouse on top of the word
    point = code_editor.calculate_real_position(QPoint(x + 23, y))

    # Move cursor to end of line
    code_editor.moveCursor(QTextCursor.End)

    # Move mouse cursor on top of test word
    qtbot.mouseMove(code_editor, point, delay=500)

    with qtbot.waitSignal(code_editor.sig_uri_found, timeout=3000) as blocker:
        qtbot.keyPress(code_editor, Qt.Key_Control, delay=500)
        args = blocker.args
        print(param, expected_output_text)
        print([args])
        output_text = args[0]
        assert expected_output_text in output_text
