# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
#
"""Tests for autosave.py"""

# Standard library imports
import ast

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


def test_get_files_to_recover_with_empty_autosave_dir(mocker, tmpdir):
    """Test get_files_to_recover() when autosave dir contains no files."""
    mocker.patch('spyder.plugins.editor.utils.autosave.get_conf_path',
                 return_value=str(tmpdir))
    addon = AutosaveForPlugin(None)

    result = addon.get_files_to_recover()

    assert result == ([], [])


@pytest.mark.parametrize('running', [True, False])
def test_get_files_to_recover_with_one_pid_file(mocker, tmpdir, running):
    """Test get_files_to_recover() if autosave dir contains one pid file with
    one autosave file. Depending on the value of running, """
    mocker.patch('spyder.plugins.editor.utils.autosave.get_conf_path',
                 return_value=str(tmpdir))
    mock_is_spyder_process = mocker.patch(
            'spyder.plugins.editor.utils.autosave.is_spyder_process',
            return_value=running)
    pidfile = tmpdir.join('pid42.txt')
    autosavefile = tmpdir.join('foo.py')
    pidfile.write('{"original": ' + repr(str(autosavefile)) + '}')
    autosavefile.write('bar = 1')
    addon = AutosaveForPlugin(None)

    result = addon.get_files_to_recover()

    expected_files = [('original', str(autosavefile))] if not running else []
    expected = (expected_files, [str(pidfile)])
    assert result == expected
    mock_is_spyder_process.assert_called_with(42)


def test_get_files_to_recover_with_non_pid_file(mocker, tmpdir):
    """Test get_files_to_recover() if autosave dir contains no pid file, but
    one Python file."""
    mocker.patch('spyder.plugins.editor.utils.autosave.get_conf_path',
                 return_value=str(tmpdir))
    pythonfile = tmpdir.join('foo.py')
    pythonfile.write('bar = 1')
    addon = AutosaveForPlugin(None)

    result = addon.get_files_to_recover()

    expected = ([(None, str(pythonfile))], [])
    assert result == expected


def test_get_files_to_recover_without_autosave_dir(mocker):
    """Test that get_files_to_recover() does not break if there is no autosave
    directory."""
    mocker.patch('spyder.plugins.editor.utils.autosave.get_conf_path',
                 return_value='non-existing-directory')
    addon = AutosaveForPlugin(None)

    result = addon.get_files_to_recover()

    assert result == ([], [])


@pytest.mark.parametrize('error_on_remove', [False, True])
def test_try_recover(mocker, tmpdir, error_on_remove):
    """Test that try_recover_from_autosave() displays a RecoveryDialog, that
    it stores the files that the user wants to open as reported by the dialog,
    and that it removes the pid file. If error_on_remove is set, then
    removing the pid file will raise an OSError; this should be ignored."""
    mock_RecoveryDialog = mocker.patch(
            'spyder.plugins.editor.utils.autosave.RecoveryDialog')
    mocker.patch('spyder.plugins.editor.utils.autosave.get_conf_path',
                 return_value=str(tmpdir))
    pidfile = tmpdir.join('pid42.txt')
    autosavefile = tmpdir.join('foo.py')
    pidfile.write('{"original": ' + repr(str(autosavefile)) + '}')
    autosavefile.write('bar = 1')
    addon = AutosaveForPlugin(None)
    if error_on_remove:
        mocker.patch('os.remove', side_effect=OSError)

    addon.try_recover_from_autosave()

    expected_mapping = [('original', str(autosavefile))]
    mock_RecoveryDialog.assert_called_with(expected_mapping, parent=None)
    expected_files_to_open = mock_RecoveryDialog().files_to_open[:]
    assert addon.recover_files_to_open == expected_files_to_open
    if not error_on_remove:
        assert not pidfile.check()


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


def test_save_autosave_mapping_with_nonempty_mapping(mocker, tmpdir):
    """Test that save_autosave_mapping() writes the current autosave mapping
    to the correct file if the mapping is not empty."""
    mocker.patch('os.getpid', return_value=42)
    mocker.patch('spyder.plugins.editor.utils.autosave.get_conf_path',
                 return_value=str(tmpdir))
    addon = AutosaveForStack(None)
    addon.name_mapping = {'orig': 'autosave'}

    addon.save_autosave_mapping()

    pidfile = tmpdir.join('pid42.txt')
    assert ast.literal_eval(pidfile.read()) == addon.name_mapping


@pytest.mark.parametrize('pidfile_exists', [False, True])
def test_save_autosave_mapping_with_empty_mapping(mocker, tmpdir,
                                                  pidfile_exists):
    """Test that save_autosave_mapping() does not write the pidfile if the
    mapping is empty, and that is removes the pidfile if it exists."""
    mocker.patch('os.getpid', return_value=42)
    mocker.patch('spyder.plugins.editor.utils.autosave.get_conf_path',
                 return_value=str(tmpdir))
    addon = AutosaveForStack(None)
    addon.name_mapping = {}
    pidfile = tmpdir.join('pid42.txt')
    if pidfile_exists:
        pidfile.write('This is an ex-parrot!')

    addon.save_autosave_mapping()

    assert not pidfile.check()


@pytest.mark.parametrize('exception', [False, True])
def test_autosave_remove_autosave_file(mocker, exception):
    """Test that AutosaveForStack.remove_autosave_file removes the autosave
    file, that an error dialog is displayed if an exception is raised,
    and that the autosave file is removed from `name_mapping` and
    `file_hashes`."""
    mock_remove = mocker.patch('os.remove')
    if exception:
        mock_remove.side_effect = OSError()
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
    mock_remove.assert_any_call('autosave')
    assert mock_dialog.called == exception


def test_autosave_file_renamed(mocker, tmpdir):
    """Test that AutosaveForStack.file_renamed removes the old autosave file,
    creates a new one, and updates `name_mapping` and `file_hashes`."""
    mock_remove = mocker.patch('os.remove')
    mocker.patch('spyder.plugins.editor.utils.autosave.get_conf_path',
                 return_value=str(tmpdir))
    mock_editor = mocker.Mock()
    mock_fileinfo = mocker.Mock(editor=mock_editor, filename='new_foo.py',
                                newly_created=False)
    mock_document = mocker.Mock()
    mock_fileinfo.editor.document.return_value = mock_document
    mock_stack = mocker.Mock(data=[mock_fileinfo])
    mock_stack.has_filename.return_value = 0
    mock_stack.compute_hash.return_value = 3
    addon = AutosaveForStack(mock_stack)
    old_autosavefile = str(tmpdir.join('old_foo.py'))
    new_autosavefile = str(tmpdir.join('new_foo.py'))
    addon.name_mapping = {'old_foo.py': old_autosavefile}
    addon.file_hashes = {'old_foo.py': 1, old_autosavefile: 42}

    addon.file_renamed('old_foo.py', 'new_foo.py')

    mock_remove.assert_any_call(old_autosavefile)
    mock_stack._write_to_file.assert_called_with(
        mock_fileinfo, new_autosavefile)
    assert addon.name_mapping == {'new_foo.py': new_autosavefile}
    assert addon.file_hashes == {'new_foo.py': 1, new_autosavefile: 3}


if __name__ == "__main__":
    pytest.main()
