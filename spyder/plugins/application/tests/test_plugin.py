# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""
Tests for the Application plugin.
"""

# Standard library imports
import os.path as osp
from unittest.mock import MagicMock, Mock, patch, ANY

# Third party imports
import pytest

# Local imports
from spyder.api.plugins import Plugins, SpyderDockablePlugin
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


@pytest.mark.parametrize('can_search', [True, False])
@pytest.mark.parametrize(
    'action_name, editor_function_name, plugin_function_name',
    [
        ('find_action', 'find', 'find'),
        ('find_next_action', 'find_next', 'find_next'),
        ('find_previous_action', 'find_previous', 'find_previous'),
        ('replace_action', 'replace', 'replace'),
    ],
)
def test_search_actions(
    application_plugin, action_name, editor_function_name,
    plugin_function_name, can_search
):
    """
    Test that triggering search actions calls the corresponding function in the
    Editor plugin.
    """
    mock_plugin = Mock(CAN_HANDLE_SEARCH_ACTIONS=can_search)
    application_plugin.sig_focused_plugin_changed.emit(mock_plugin)

    container = application_plugin.get_container()
    action = getattr(container, action_name)
    action.trigger()

    if can_search:
        editor_function = getattr(mock_plugin, plugin_function_name)
        editor_function.assert_called()
    else:
        application_plugin.get_plugin.assert_called_with(Plugins.Editor)
        editor_plugin = application_plugin.get_plugin.return_value
        editor_function = getattr(editor_plugin, editor_function_name)
        editor_function.assert_called()


def test_enable_search_action(application_plugin):
    """
    Test that enable_search_action enables or disabled the specified search
    action on the plugin, and that switching plugins updates whether actions
    are enabled according to previous calls to enable_search_action.
    """
    container = application_plugin.get_container()
    mock_plugin1 = Mock(CAN_HANDLE_EDIT_ACTIONS=True)
    mock_plugin2 = Mock()

    # Initially, actions are enabled
    application_plugin.sig_focused_plugin_changed.emit(mock_plugin1)
    assert container.find_action.isEnabled() is True

    # Disabling the Find Text action in the active plugin works
    application_plugin.enable_search_action(
        ApplicationActions.FindText, False, mock_plugin1.NAME
    )
    assert container.find_action.isEnabled() is False

    # After changing to another plugin, the Find Text action is enabled again
    application_plugin.sig_focused_plugin_changed.emit(mock_plugin2)
    assert container.find_action.isEnabled() is True

    # Disabling the Find Text action in the second plugin (which has focus)
    # works
    application_plugin.enable_search_action(
        ApplicationActions.FindText, False, mock_plugin2.NAME
    )
    assert container.find_action.isEnabled() is False

    # Enabling the Find Text action in the first plugin has no immediate effect
    application_plugin.enable_search_action(
        ApplicationActions.FindText, True, mock_plugin1.NAME
    )
    assert container.find_action.isEnabled() is False

    # When changing to the first plugin, the Find Text action is enabled
    application_plugin.sig_focused_plugin_changed.emit(mock_plugin1)
    assert container.find_action.isEnabled() == True


@pytest.mark.parametrize('can_edit', [True, False])
@pytest.mark.parametrize(
    'action_name, editor_function_name, plugin_function_name',
    [
        ('undo_action', 'undo', 'undo'),
        ('redo_action', 'redo', 'redo'),
        ('cut_action', 'cut', 'cut'),
        ('copy_action', 'copy', 'copy'),
        ('paste_action', 'paste', 'paste'),
        ('select_all_action', 'select_all', 'select_all'),
    ],
)
def test_edit_actions(
    application_plugin, action_name, editor_function_name,
    plugin_function_name, can_edit
):
    """
    Test that triggering edit actions calls the corresponding function in the
    Editor plugin.
    """
    mock_plugin = Mock(CAN_HANDLE_EDIT_ACTIONS=can_edit)
    application_plugin.sig_focused_plugin_changed.emit(mock_plugin)

    container = application_plugin.get_container()
    action = getattr(container, action_name)
    action.trigger()

    if can_edit:
        editor_function = getattr(mock_plugin, plugin_function_name)
        editor_function.assert_called()
    else:
        application_plugin.get_plugin.assert_called_with(Plugins.Editor)
        editor_plugin = application_plugin.get_plugin.return_value
        editor_function = getattr(editor_plugin, editor_function_name)
        editor_function.assert_called()


def test_enable_edit_action(application_plugin):
    """
    Test that enable_edit_action enables or disabled the specified edit action
    on the plugin, and that switching plugins updates whether actions are
    enabled according to previous calls to enable_edit_action.
    """
    container = application_plugin.get_container()
    mock_plugin1 = Mock(CAN_HANDLE_EDIT_ACTIONS=True)
    mock_plugin2 = Mock()

    # Initially, actions are enabled
    application_plugin.sig_focused_plugin_changed.emit(mock_plugin1)
    assert container.undo_action.isEnabled() is True

    # Disabling the Save action in the active plugin works
    application_plugin.enable_edit_action(
        ApplicationActions.Undo, False, mock_plugin1.NAME
    )
    assert container.undo_action.isEnabled() is False

    # After changing to another plugin, the Save action is enabled again
    application_plugin.sig_focused_plugin_changed.emit(mock_plugin2)
    assert container.undo_action.isEnabled() is True

    # Disabling the Save action in the second plugin (which has focus) works
    application_plugin.enable_edit_action(
        ApplicationActions.Undo, False, mock_plugin2.NAME
    )
    assert container.undo_action.isEnabled() is False

    # Enabling the Save action in the first plugin has no immediate effect
    application_plugin.enable_edit_action(
        ApplicationActions.Undo, True, mock_plugin1.NAME
    )
    assert container.undo_action.isEnabled() is False

    # When changing to the first plugin, the Save action is enabled
    application_plugin.sig_focused_plugin_changed.emit(mock_plugin1)
    assert container.undo_action.isEnabled() == True


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


def test_open_file_action(application_plugin):
    """
    Test that triggering the "Open file" action creates a QFileDialog.
    Assume that there are two plugins, the editor plugin and another plugin
    that says it can handle .xyz files. Check that if the user selects one
    file with no extension and one with an .xyz extension, then the load()
    function in the Editor plugin is called with the first file and the
    open_file() function in the other plugin is called with the second file.
    """
    mock_QFileDialog = Mock()
    mock_QFileDialog.return_value.selectedFiles.return_value = [
        '/home/file1',
        '/home/file2.xyz',
    ]

    xyz_plugin = Mock(spec=SpyderDockablePlugin, FILE_EXTENSIONS=['.xyz'])

    editor_plugin = Mock()
    editor_plugin.get_current_filename.return_value = 'current-file'

    def my_get_plugin(name):
        return {'xyz': xyz_plugin, Plugins.Editor: editor_plugin}[name]

    mock_registry = MagicMock()
    mock_registry.__iter__.side_effect = lambda: iter(['xyz', Plugins.Editor])
    mock_registry.get_plugin.side_effect = my_get_plugin

    application_plugin.get_plugin.side_effect = my_get_plugin

    # Note: container.open_file_using_dialog() behaves differently under pytest
    with patch('spyder.plugins.application.container.QFileDialog', mock_QFileDialog):
        with patch('spyder.plugins.application.plugin.PLUGIN_REGISTRY', mock_registry):
            container = application_plugin.get_container()
            container.open_action.trigger()

    mock_QFileDialog.assert_called()
    editor_plugin.load.assert_called_with(osp.normpath('/home/file1'))
    xyz_plugin.open_file.assert_called_with(osp.normpath('/home/file2.xyz'))


@pytest.mark.parametrize('plugin_filename', ['plugin', None])
def test_open_file_using_dialog(application_plugin, plugin_filename):
    """
    That that open_file_using_dialog asks the currently focused plugin for the
    current file name, and that if the result is None the Editor plugin is
    asked as a fallback.
    """
    mock_plugin = Mock()
    mock_plugin.get_current_filename.return_value = plugin_filename

    mock_editor = Mock()
    mock_editor.get_current_filename.return_value = 'editor'

    application_plugin.focused_plugin = mock_plugin
    application_plugin.get_plugin.return_value = mock_editor

    container = application_plugin.get_container()
    with patch.object(container, 'open_file_using_dialog') as mock:
        application_plugin.open_file_using_dialog()

    if plugin_filename:
        mock.assert_called_with(plugin_filename, ANY)
    else:
        application_plugin.get_plugin.assert_called_with(Plugins.Editor)
        mock.assert_called_with('editor', ANY)


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
        ApplicationActions.SaveFile, False, mock_plugin1.NAME
    )
    assert container.save_action.isEnabled() is False

    # After changing to another plugin, the Save action is enabled again
    application_plugin.sig_focused_plugin_changed.emit(mock_plugin2)
    assert container.save_action.isEnabled() is True

    # Disabling the Save action in the second plugin (which has focus) works
    application_plugin.enable_file_action(
        ApplicationActions.SaveFile, False, mock_plugin2.NAME
    )
    assert container.save_action.isEnabled() is False

    # Enabling the Save action in the first plugin has no immediate effect
    application_plugin.enable_file_action(
        ApplicationActions.SaveFile, True, mock_plugin1.NAME
    )
    assert container.save_action.isEnabled() is False

    # When changing to the first plugin, the Save action is enabled
    application_plugin.sig_focused_plugin_changed.emit(mock_plugin1)
    assert container.save_action.isEnabled() == True
