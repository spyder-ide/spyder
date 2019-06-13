# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
#
"""Tests for autosave.py"""

# Third party imports
import pytest

# Local imports
from spyder.plugins.editor.utils.autosave import (AutosaveForStack,
                                                  AutosaveForPlugin)


def test_autosave_component_set_interval(mocker):
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


def test_autosave(mocker):
    """Test that AutosaveForStack.maybe_autosave writes the contents to the
    autosave file and updates the file_hashes."""
    mock_editor = mocker.Mock()
    mock_fileinfo = mocker.Mock(editor=mock_editor, filename='orig',
                                newly_created=False)
    mock_document = mocker.Mock()
    mock_fileinfo.editor.document.return_value = mock_document
    mock_stack = mocker.Mock(data=[mock_fileinfo])
    addon = AutosaveForStack(mock_stack)
    addon.name_mapping = {'orig': 'autosave'}
    addon.file_hashes = {'orig': 1, 'autosave': 2}
    mock_stack.compute_hash.return_value = 3

    addon.maybe_autosave(0)

    mock_stack._write_to_file.assert_called_with(mock_fileinfo, 'autosave')
    mock_stack.compute_hash.assert_called_with(mock_fileinfo)
    assert addon.file_hashes == {'orig': 1, 'autosave': 3}


@pytest.mark.parametrize('exception', [False, True])
def test_autosave_remove_autosave_file(mocker, exception):
    """Test that AutosaveForStack.remove_autosave_file removes the autosave
    file, that an error dialog is displayed if an exception is raised,
    and that the autosave file is removed from `name_mapping` and
    `file_hashes`."""
    mock_remove = mocker.patch('os.remove')
    if exception:
        mock_remove.side_effect = EnvironmentError()
    mock_dialog = mocker.patch(
        'spyder.plugins.editor.utils.autosave.AutosaveErrorDialog')
    mock_stack = mocker.Mock()
    fileinfo = mocker.Mock()
    fileinfo.filename = 'orig'
    addon = AutosaveForStack(mock_stack)
    addon.name_mapping = {'orig': 'autosave'}
    addon.file_hashes = {'autosave': 42}

    addon.remove_autosave_file(fileinfo.filename)
    assert addon.name_mapping == {}
    assert addon.file_hashes == {}
    mock_remove.assert_called_with('autosave')
    assert mock_dialog.called == exception


if __name__ == "__main__":
    pytest.main()
