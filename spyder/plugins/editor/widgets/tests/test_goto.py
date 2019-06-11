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

# Local imports
from spyder.plugins.editor.widgets.tests.test_codeeditor import editorbot

# Constants
TEST_FOLDER = os.path.abspath(os.path.dirname(__file__))
_, TEMPFILE_PATH = tempfile.mkstemp()
TEST_FILE_ABS = [os.path.join(TEST_FOLDER, f) for f in
                 os.listdir(TEST_FOLDER) if f.endswith('.py')][0]
TEST_FILE_REL = [f for f in os.listdir(TEST_FOLDER) if f.endswith('.py')][0]


@pytest.mark.parametrize('params', [
            # Parameter, Expected output, Full file path (or None if not file)
            # ----------------------------------------------------------------
            # Files that exist with absolute paths
            ('"file://{}/"\n'.format(TEMPFILE_PATH), TEMPFILE_PATH,
             TEMPFILE_PATH),
            ('"file://{}/"\n'.format(TEST_FILE_ABS), TEST_FILE_ABS,
             TEST_FILE_ABS),
            # Files that exist with relative paths
            ('"file://./{}/"\n'.format(TEST_FILE_REL), TEST_FILE_REL,
             os.path.join(TEST_FOLDER, TEST_FILE_REL)),
            # Files that do not exist
            ('"file:///not there/"', 'file:///not there/', '/not there/'),
            ('"file:///not_there/"', 'file:///not_there/', '/not_there/'),
            # Urls
            ('" https://google.com"\n', 'https://google.com', None),
            ('# https://google.com"\n', 'https://google.com', None),
            # Mail to
            ('" mailto:some@email.com"\n', 'mailto:some@email.com', None),
            ('# mailto:some@email.com\n', 'mailto:some@email.com', None),
            # Issues
            ('# gl:gitlab-org/gitlab-ce#62529\n',
             'gl:gitlab-org/gitlab-ce#62529', None),
            ('# bb:birkenfeld/pygments-main#1516\n',
             'bb:birkenfeld/pygments-main#1516', None),
            ('# gh:spyder-ide/spyder#123\n',
             'gh:spyder-ide/spyder#123', None),
            ('# gh:spyder-ide/spyder#123\n',
             'gh:spyder-ide/spyder#123', None),
        ]
    )
def test_goto_uri(qtbot, editorbot, params):
    """Test that the uri search is working correctly."""
    _, code_editor = editorbot
    code_editor.show()

    param, expected_output_text, full_file_path = params
    if full_file_path:
        code_editor.filename = full_file_path

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
