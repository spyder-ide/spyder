# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
#
"""Tests for workingdirectory plugin."""

# Standard library imports
import os.path as osp
import sys
from unittest.mock import Mock

# Third-party imports
import pytest
from qtpy.QtWidgets import QMainWindow

# Local imports
from spyder.app.cli_options import get_options
from spyder.config.base import get_home_dir
from spyder.config.manager import CONF
from spyder.plugins.workingdirectory.plugin import WorkingDirectory


NEW_DIR = 'new_workingdir'


class MainWindow(QMainWindow):

    def __init__(self):
        # This avoids using the cli options passed to pytest
        sys_argv = [sys.argv[0]]
        self._cli_options = get_options(sys_argv)[0]
        super().__init__()

    def get_plugin(self, plugin, error=True):
        return Mock()


@pytest.fixture
def setup_workingdirectory(qtbot, request, tmpdir):
    """Setup working directory plugin."""
    CONF.reset_to_defaults()
    use_startup_wdir = request.node.get_closest_marker('use_startup_wdir')
    use_cli_wdir = request.node.get_closest_marker('use_cli_wdir')

    # Setting default options
    CONF.set('workingdir', 'startup/use_project_or_home_directory', True)
    CONF.set('workingdir', 'startup/use_fixed_directory', False)

    # Create main window and new directory
    main_window = MainWindow()

    if use_startup_wdir:
        new_wdir = tmpdir.mkdir(NEW_DIR + '_startup')
        CONF.set('workingdir', 'startup/use_project_or_home_directory', False)
        CONF.set('workingdir', 'startup/use_fixed_directory', True)
        CONF.set('workingdir', 'startup/fixed_directory', str(new_wdir))
    elif use_cli_wdir:
        new_wdir = tmpdir.mkdir(NEW_DIR + '_cli')
        main_window._cli_options.working_directory = str(new_wdir)

    workingdirectory = WorkingDirectory(main_window, configuration=CONF)
    workingdirectory.on_initialize()
    workingdirectory.close = lambda: True

    return workingdirectory


def test_basic_initialization(setup_workingdirectory):
    """Test Working Directory plugin initialization."""
    workingdirectory = setup_workingdirectory

    # Assert that workingdirectory exists
    assert workingdirectory is not None


def test_get_workingdir(setup_workingdirectory):
    """Test the method that defines the working directory at home."""
    workingdirectory = setup_workingdirectory
    # Start the working directory on the home directory
    act_wdir = workingdirectory.get_workdir()
    assert act_wdir == get_home_dir()


@pytest.mark.use_startup_wdir
def test_get_workingdir_startup(setup_workingdirectory):
    """
    Test the method that sets the working directory according to the one
    selected in preferences.
    """
    workingdirectory = setup_workingdirectory

    # Get the current working directory
    cwd = workingdirectory.get_workdir()
    folders = osp.split(cwd)

    # Asert working directory is the expected one
    assert folders[-1] == NEW_DIR + '_startup'
    CONF.reset_to_defaults()


@pytest.mark.use_cli_wdir
def test_get_workingdir_cli(setup_workingdirectory):
    """
    Test that the plugin sets the working directory passed by users on the
    command line with the --workdir option.
    """
    workingdirectory = setup_workingdirectory

    # Get the current working directory
    cwd = workingdirectory.get_container().history[-1]
    folders = osp.split(cwd)

    # Asert working directory is the expected one
    assert folders[-1] == NEW_DIR + '_cli'
    CONF.reset_to_defaults()


if __name__ == "__main__":
    pytest.main()
