# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""
Tests for ApplicationContainer.
"""

# Standard library imports
from unittest.mock import patch


def test_add_recent_file(application_plugin):
    """
    Test that add_recent_file adds the given file to the front of recent_files
    and ensures that the list has no duplicates.
    """
    container = application_plugin.get_container()
    assert container.recent_files == []

    container.add_recent_file('file1')
    assert container.recent_files == ['file1']

    container.add_recent_file('file2')
    assert container.recent_files == ['file2', 'file1']

    container.add_recent_file('file1')
    assert container.recent_files == ['file1', 'file2']


def test_clear_recent_files(application_plugin):
    """
    Test that clear_recent_files clears the list in recent_files.
    """
    container = application_plugin.get_container()
    container.add_recent_file('file1')
    assert container.recent_files == ['file1']

    container.clear_recent_files()
    assert container.recent_files == []


def test_update_recent_files_menu(application_plugin):
    """
    Test that update_recent_files_menu() puts the files in recent_files in
    the recent_files_menu (skipping those that do not exist), followed by a
    separator and then other items.
    """

    def mock_isfile(filename):
        return filename in ['file1', 'file2']

    container = application_plugin.get_container()
    container.add_recent_file('file1')
    container.add_recent_file('file2')
    container.add_recent_file('non-existing-file')
    with patch('spyder.plugins.application.container.osp.isfile', mock_isfile):
        container.update_recent_files_menu()

    menu = container.recent_files_menu
    menuitems = [action.text() for action in menu.actions()]
    expected = [
        'file2',
        'file1',
        '',
        'Maximum number of recent files...',
        'Clear this list',
        '',
    ]
    assert menuitems == expected


def test_change_max_recent_files(application_plugin):
    """
    Test that change_max_recent_files changes the value of max_recent_files
    in the config to the number given by the user.
    """
    container = application_plugin.get_container()
    old_value = container.get_conf('max_recent_files')
    with patch(
        'spyder.plugins.application.container.QInputDialog.getInt',
        return_value=(old_value + 1, True),
    ):
        container.change_max_recent_files()

    assert container.get_conf('max_recent_files') == old_value + 1

    container.set_conf('max_recent_files', old_value)
