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


def test_focused_plugin(application_plugin):
    """
    Test that focused_plugin is initially None and that it is set after
    receiving sig_focused_plugin_changed.
    """
    assert application_plugin.focused_plugin is None
    mock_plugin = Mock()
    application_plugin.sig_focused_plugin_changed.emit(mock_plugin)
    assert application_plugin.focused_plugin == mock_plugin


@pytest.mark.parametrize(
    'action_name, editor_function_name',
    [
        ('new_action', 'new'),
        ('open_last_closed_action', 'open_last_closed'),
        ('save_action', 'save'),
        ('save_all_action', 'save_all'),
        ('save_as_action', 'save_as'),
        ('save_copy_as_action', 'save_copy_as'),
        ('revert_action', 'revert_file'),
        ('close_file_action', 'close_file'),
        ('close_all_action', 'close_all_files'),
    ],
)
def test_file_actions(application_plugin, action_name, editor_function_name):
    """
    Test that triggering file actions calls the corresponding function in the
    Editor plugin.
    """
    container = application_plugin.get_container()
    action = getattr(container, action_name)
    action.trigger()

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


def test_enable_save_action(application_plugin):
    """
    Test that enable_save_action does indeed enable or disable the "Save"
    action.
    """
    container = application_plugin.get_container()
    application_plugin.enable_save_action(True)
    assert container.save_action.isEnabled() == True

    application_plugin.enable_save_action(False)
    assert container.save_action.isEnabled() == False


def test_enable_save_all_action(application_plugin):
    """
    Test that enable_save_all_action does indeed enable or disable the
    "Save All" action.
    """
    container = application_plugin.get_container()
    application_plugin.enable_save_all_action(True)
    assert container.save_all_action.isEnabled() == True

    application_plugin.enable_save_all_action(False)
    assert container.save_all_action.isEnabled() == False
