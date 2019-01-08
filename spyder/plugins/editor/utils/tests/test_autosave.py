# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
#
"""Tests for autosave.py"""

# Third party imports
import pytest
from qtpy.QtWidgets import QPushButton

# Local imports
from spyder.plugins.editor.utils.autosave import (AutosaveForStack,
                                                  AutosaveForPlugin,
                                                  AutosaveErrorMessageBox)


def test_autosave_component_set_interval(qtbot, mocker):
    """Test that setting the interval does indeed change it and calls
    do_autosave if enabled."""
    mocker.patch.object(AutosaveForPlugin, 'do_autosave')
    addon = AutosaveForPlugin(None)
    addon.do_autosave.assert_not_called()
    addon.interval = 10000
    assert addon.interval == 10000
    addon.do_autosave.assert_not_called()
    addon.enabled = True
    addon.interval = 20000
    assert addon.do_autosave.called


@pytest.mark.parametrize('enabled', [False, True])
def test_autosave_component_timer_if_enabled(qtbot, mocker, enabled):
    """Test that AutosaveForPlugin calls do_autosave() on timer if enabled."""
    mocker.patch.object(AutosaveForPlugin, 'do_autosave')
    addon = AutosaveForPlugin(None)
    addon.do_autosave.assert_not_called()
    addon.interval = 100
    addon.enabled = enabled
    qtbot.wait(500)
    if enabled:
        assert addon.do_autosave.called
    else:
        addon.do_autosave.assert_not_called()


@pytest.mark.parametrize('exception', [False, True])
def test_autosave_remove_autosave_file(mocker, exception):
    """Test that AutosaveForStack.remove_autosave_file removes the autosave
    file and that it ignores any exceptions raised when removing the file."""
    mock_remove = mocker.patch('os.remove')
    if exception:
        mock_remove.side_effect = EnvironmentError()
    mock_stack = mocker.Mock()
    fileinfo = mocker.Mock()
    fileinfo.filename = 'orig'
    addon = AutosaveForStack(mock_stack)
    addon.name_mapping = {'orig': 'autosave'}
    addon.remove_autosave_file(fileinfo)
    mock_remove.assert_called_with('autosave')


def test_autosave_error_message_box(qtbot, mocker):
    """Test that AutosaveErrorMessageBox exec's at first, but that after the
    'do not show anymore' checkbox is clicked, it does not exec anymore."""
    mock_exec = mocker.patch.object(AutosaveErrorMessageBox, 'exec_')
    box = AutosaveErrorMessageBox('action', 'error')
    box.exec_if_enabled()
    assert mock_exec.call_count == 1
    box.dismiss_box.click()
    ok_button = box.findChild(QPushButton)
    ok_button.click()
    box2 = AutosaveErrorMessageBox('action', 'error')
    box2.exec_if_enabled()
    assert mock_exec.call_count == 1
