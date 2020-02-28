# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
#

"""
Tests for cli_options.py
"""
import pytest
from spyder.app import cli_options


def test_get_options():
    getopt = cli_options.get_options

    options, args = getopt([])
    assert not options.new_instance
    assert not options.reset_to_defaults
    assert not options.reset_config_files
    assert not options.optimize
    assert not options.paths
    assert options.working_directory is None
    assert not options.hide_console
    assert not options.show_console
    assert not options.multithreaded
    assert not options.profile
    assert options.window_title is None
    assert options.project is None
    assert options.opengl_implementation is None
    assert options.files == []
    assert args == []

    options, args = getopt(['--new-instance'])
    assert options.new_instance

    options, args = getopt(['--defaults', '--reset'])
    assert options.reset_to_defaults
    assert options.reset_config_files

    options, args = getopt(['--optimize', '--workdir', 'test dir'])
    assert options.optimize
    assert options.working_directory == 'test dir'

    options, args = getopt('--window-title MyWindow'.split())
    assert options.window_title == 'MyWindow'

    options, args = getopt('-p myproject test_file.py another_file.py'.split())
    assert options.project == 'myproject'
    assert options.files == ['test_file.py', 'another_file.py']
    assert args == ['test_file.py', 'another_file.py']

    with pytest.raises(SystemExit):
        options, args = getopt(['--version'])

    # Requires string.
    with pytest.raises(SystemExit):
        options, args = getopt(['-w'])

    # Requires string.
    with pytest.raises(SystemExit):
        options, args = getopt(['-p'])

    options, args = getopt('--opengl software'.split())
    assert options.opengl_implementation == 'software'


if __name__ == "__main__":
    pytest.main()
