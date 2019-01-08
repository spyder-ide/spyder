# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
#
"""Tests for autosaveerror.py"""

# Third party imports
from qtpy.QtWidgets import QPushButton

# Local imports
from spyder.plugins.editor.widgets.autosaveerror import AutosaveErrorDialog


def test_autosave_error_message_box(qtbot, mocker):
    """Test that AutosaveErrorDialog exec's at first, but that after the
    'do not show anymore' checkbox is clicked, it does not exec anymore."""
    mock_exec = mocker.patch.object(AutosaveErrorDialog, 'exec_')
    box = AutosaveErrorDialog('action', 'error')
    box.exec_if_enabled()
    assert mock_exec.call_count == 1
    box.dismiss_box.click()
    ok_button = box.findChild(QPushButton)
    ok_button.click()
    box2 = AutosaveErrorDialog('action', 'error')
    box2.exec_if_enabled()
    assert mock_exec.call_count == 1
