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
from qtpy.QtCore import Qt, QPoint, QTimer
from qtpy.QtGui import QDesktopServices, QTextCursor
from qtpy.QtWidgets import QMessageBox
import pytest

# Local imports
from spyder.plugins.editor.widgets.tests.test_codeeditor import editorbot

# Constants
HERE = os.path.abspath(__file__)
TEST_FOLDER = os.path.abspath(os.path.dirname(__file__))
_, TEMPFILE_PATH = tempfile.mkstemp()
TEST_FILES = [os.path.join(TEST_FOLDER, f) for f in
              os.listdir(TEST_FOLDER) if f.endswith('.py')]
TEST_FILE_ABS = TEST_FILES[0].replace(' ', '%20')
TEST_FILE_REL = 'conftest.py'


@pytest.mark.parametrize('params', [
            # Parameter, expected output 1, full file path, expected output 2
            # ----------------------------------------------------------------
            # Files that exist with absolute paths
            ('file://{}\n'.format(TEMPFILE_PATH), 'file://' + TEMPFILE_PATH,
             TEMPFILE_PATH, 'file://' + TEMPFILE_PATH),
            ('"file://{}"\n'.format(TEST_FILE_ABS), 'file://' + TEST_FILE_ABS,
             TEST_FILE_ABS, 'file://' + TEST_FILE_ABS),
            # Files that exist with relative paths
            ('"file://./{}"\n'.format(TEST_FILE_REL),
             'file://./' + TEST_FILE_REL,
             os.path.join(TEST_FOLDER, TEST_FILE_REL),
             'file://./' + TEST_FILE_REL),
            # Files that do not exist
            ('"file:///not%20there"', 'file:///not%20there',
             '/not%20there', 'file:///not%20there'),
            ('"file:///not_there"', 'file:///not_there', '/not_there',
             'file:///not_there'),
            # Urls
            ('" https://google.com"\n', 'https://google.com', None,
             'https://google.com'),
            ('# https://google.com"\n', 'https://google.com', None,
             'https://google.com'),
            # Mail to
            ('" mailto:some@email.com"\n', 'mailto:some@email.com', None,
             'mailto:some@email.com'),
            ('# mailto:some@email.com\n', 'mailto:some@email.com', None,
             'mailto:some@email.com'),
            ('some@email.com\n', 'some@email.com', None,
             'mailto:some@email.com'),
            ('# some@email.com\n', 'some@email.com', None,
             'mailto:some@email.com'),
            # Issues
            ('# gl:gitlab-org/gitlab-ce#62529\n',
             'gl:gitlab-org/gitlab-ce#62529', None,
             'https://gitlab.com/gitlab-org/gitlab-ce/issues/62529'),
            ('# bb:birkenfeld/pygments-main#1516\n',
             'bb:birkenfeld/pygments-main#1516', None,
             'https://bitbucket.org/birkenfeld/pygments-main/issues/1516'),
            ('# gh:spyder-ide/spyder#123\n', 'gh:spyder-ide/spyder#123', None,
             'https://github.com/spyder-ide/spyder/issues/123'),
            ('# gh:spyder-ide/spyder#123\n', 'gh:spyder-ide/spyder#123', None,
             'https://github.com/spyder-ide/spyder/issues/123'),
            ('# gh-123\n', 'gh-123', HERE,
             'https://github.com/spyder-ide/spyder/issues/123'),
        ]
    )
def test_goto_uri(qtbot, editorbot, mocker, params):
    """Test that the uri search is working correctly."""
    _, code_editor = editorbot
    code_editor.show()
    mocker.patch.object(QDesktopServices, 'openUrl')

    param, expected_output_1, full_file_path, expected_output_2 = params
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
        print([param, expected_output_1])
        print([args])
        output_1 = args[0]

        # Tests spyder-ide/spyder#9614.
        output_2 = code_editor.go_to_uri_from_cursor(expected_output_1)

        assert expected_output_1 in output_1
        assert expected_output_2 == output_2


def test_goto_uri_message_box(qtbot, editorbot, mocker):
    """
    Test that a message box is displayed when the shorthand issue notation is
    used (gh-123) indicating the user that the file is not under a repository
    """
    _, code_editor = editorbot
    code_editor.filename = TEMPFILE_PATH
    code_editor._last_hover_pattern_key = 'issue'

    def interact():
        msgbox = code_editor.findChild(QMessageBox)
        assert msgbox
        qtbot.keyClick(msgbox, Qt.Key_Return)

    timer = QTimer()
    timer.setSingleShot(True)
    timer.setInterval(500)
    timer.timeout.connect(interact)
    timer.start()

    code_editor.go_to_uri_from_cursor('gh-123')

    code_editor.filename = None
    code_editor._last_hover_pattern_key = None
    code_editor._last_hover_pattern_text = None
