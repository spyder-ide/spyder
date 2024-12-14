# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""
Tests for the Application plugin.
"""

# Standard library imports
from unittest.mock import Mock, patch

# Third party imports
import pytest

# Local imports
from spyder.api.plugins import Plugins
from spyder.plugins.application.api import ApplicationActions


def test_focused_plugin(application_plugin):
    """
    Test that focused_plugin is initially None and that it is set after
    receiving sig_focused_plugin_changed.
    """
    assert application_plugin.focused_plugin is None
    mock_plugin = Mock()
    application_plugin.sig_focused_plugin_changed.emit(mock_plugin)
    assert application_plugin.focused_plugin == mock_plugin


@pytest.mark.parametrize('can_file', [True, False])
@pytest.mark.parametrize(
    'action_name, editor_function_name, plugin_function_name',
    [
        ('new_action', 'new', 'create_new_file'),
        ('open_last_closed_action', 'open_last_closed', 'open_last_closed_file'),
        ('save_action', 'save', 'save_file'),
        ('save_all_action', 'save_all', 'save_all'),
        ('save_as_action', 'save_as', 'save_file_as'),
        ('save_copy_as_action', 'save_copy_as', 'save_copy_as'),
        ('revert_action', 'revert_file', 'revert_file'),
        ('close_file_action', 'close_file', 'close_file'),
        ('close_all_action', 'close_all_files', 'close_all'),
    ],
)
def test_file_actions(
    application_plugin, action_name, editor_function_name,
    plugin_function_name, can_file
):
    """
    Test that triggering file actions calls the corresponding function in the
    Editor plugin.
    """
    mock_plugin = Mock(CAN_HANDLE_FILE_ACTIONS=can_file)
    application_plugin.sig_focused_plugin_changed.emit(mock_plugin)

    container = application_plugin.get_container()
    action = getattr(container, action_name)
    action.trigger()

    if can_file:
        editor_function = getattr(mock_plugin, plugin_function_name)
        editor_function.assert_called()
    else:
        application_plugin.get_plugin.assert_called_with(Plugins.Editor)
        editor_plugin = application_plugin.get_plugin.return_value
        editor_function = getattr(editor_plugin, editor_function_name)
        editor_function.assert_called()


def test_open_file(application_plugin):
    """
    Test that triggering the "Open file" action calls the load() function in
    the Editor plugin with the file names selected in the QFileDialog.
    """
    container = application_plugin.get_container()
    mock_QFileDialog = Mock(name='mock QFileDialog')
    mock_QFileDialog.return_value.selectedFiles.return_value = [
        '/home/file1',
        '/home/file2',
    ]

    # Note: container.open_file_using_dialog() behaves differently under pytest
    with patch('spyder.plugins.application.container.QFileDialog', mock_QFileDialog):
        container.open_action.trigger()

    application_plugin.get_plugin.assert_called_with(Plugins.Editor)
    editor_plugin = application_plugin.get_plugin.return_value
    editor_plugin.load.assert_any_call('/home/file1')
    editor_plugin.load.assert_any_call('/home/file2')


def test_enable_file_action(application_plugin):
    """
    Test that enable_file_action enables or disabled the specified file action
    on the plugin, and that switching plugins updates whether actions are
    enabled according to previous calls to enable_file_action.
    """
    container = application_plugin.get_container()
    mock_plugin1 = Mock(CAN_HANDLE_FILE_ACTIONS=True)
    mock_plugin2 = Mock()

    # Initially, actions are enabled
    application_plugin.sig_focused_plugin_changed.emit(mock_plugin1)
    assert container.save_action.isEnabled() is True

    # Disabling the Save action in the active plugin works
    application_plugin.enable_file_action(
        ApplicationActions.SaveFile, False, mock_plugin1
    )
    assert container.save_action.isEnabled() is False

    # After changing to another plugin, the Save action is enabled again
    application_plugin.sig_focused_plugin_changed.emit(mock_plugin2)
    assert container.save_action.isEnabled() is True

    # Disabling the Save action in the second plugin (which has focus) works
    application_plugin.enable_file_action(
        ApplicationActions.SaveFile, False, mock_plugin2
    )
    assert container.save_action.isEnabled() is False

    # Enabling the Save action in the first plugin has no immediate effect
    application_plugin.enable_file_action(
        ApplicationActions.SaveFile, True, mock_plugin1
    )
    assert container.save_action.isEnabled() is False

    # When changing to the first plugin, the Save action is enabled
    application_plugin.sig_focused_plugin_changed.emit(mock_plugin1)
    assert container.save_action.isEnabled() == True
