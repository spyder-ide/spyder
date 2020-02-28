# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
#
"""Tests for workingdirectory plugin."""

# Test library imports
import pytest
import os
import os.path as osp

# Local imports
from spyder.plugins.workingdirectory.plugin import WorkingDirectory
from spyder.config.base import get_home_dir
from spyder.config.manager import CONF

NEW_DIR = 'new_workingdir'


@pytest.fixture
def setup_workingdirectory(qtbot, request):
    """Setup working directory plugin."""
    CONF.reset_to_defaults()
    use_startup_wdir = request.node.get_closest_marker('use_startup_wdir')
    if use_startup_wdir:
        new_wdir = osp.join(os.getcwd(), NEW_DIR)
        if not osp.exists(new_wdir):
            os.mkdir(new_wdir)
        CONF.set('workingdir', 'startup/use_fixed_directory', True)
        CONF.set('workingdir', 'startup/fixed_directory', new_wdir)
    else:
        CONF.set('workingdir', 'startup/use_fixed_directory', False)
        CONF.set('workingdir', 'console/use_fixed_directory', False)
        CONF.set('workingdir', 'startup/fixed_directory', get_home_dir())

    workingdirectory = WorkingDirectory(None)
    qtbot.addWidget(workingdirectory)
    workingdirectory.show()

    return workingdirectory, qtbot


def test_basic_initialization(setup_workingdirectory):
    """Test Working Directory plugin initialization."""
    workingdirectory, qtbot = setup_workingdirectory

    # Assert that workingdirectory exists
    assert workingdirectory is not None


def test_get_workingdir(setup_workingdirectory):
    """Test the method that defines the working directory at home."""
    workingdirectory, qtbot = setup_workingdirectory
    # Start the working directory on the home directory
    act_wdir = workingdirectory.get_workdir()
    assert act_wdir == get_home_dir()


@pytest.mark.use_startup_wdir
def test_get_workingdir_startup(setup_workingdirectory):
    """Test the method that defines the working directory at home."""
    workingdirectory, qtbot = setup_workingdirectory
    # Start the working directory on the home directory
    act_wdir = workingdirectory.get_workdir()
    folders = osp.split(act_wdir)
    assert folders[-1] == NEW_DIR
    CONF.reset_to_defaults()


if __name__ == "__main__":
    pytest.main()
