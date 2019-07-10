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
from spyder.config.main import CONF


@pytest.fixture
def setup_workingdirectory(qtbot):
    """Setup working directory plugin."""
    workingdirectory = WorkingDirectory(None)
    qtbot.addWidget(workingdirectory)
    workingdirectory.show()

    return workingdirectory, qtbot

@pytest.fixture
def setup_workingdirectory_startup(qtbot):
    new_wdir = 'new_workingdir/'
    if not osp.exists(new_wdir):
        os.mkdir(new_wdir)
    """Setup working directory plugin."""
    CONF.set('workingdir', 'startup/use_fixed_directory', True)
    CONF.set('workingdir', 'startup/fixed_directory', new_wdir)
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


def test_get_workingdir_startup(setup_workingdirectory_startup):
    """Test the method that defines the working directory at home."""
    workingdirectory, qtbot = setup_workingdirectory_startup
    # Start the working directory on the home directory
    act_wdir = workingdirectory.get_workdir()
    print(act_wdir)
    assert act_wdir == 'new_workingdir/'


if __name__ == "__main__":
    pytest.main()
