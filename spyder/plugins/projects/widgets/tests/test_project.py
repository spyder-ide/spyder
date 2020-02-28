# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
#
"""
Tests for __init__.py.
"""

# Standard library imports
import os
import os.path as osp

# Third party imports
import pytest

# Local imports
from spyder.plugins.projects.projecttypes import EmptyProject
from spyder.plugins.projects.utils.config import (CODESTYLE, ENCODING,
                                                  VCS, WORKSPACE)


@pytest.fixture(scope='session')
def project_test(tmpdir_factory):
    """
    Fixture for create a temporary project.

    Returns:
        project_dir: fixture of temporary project dir.
        project: EmptyProject object.
    """
    project_dir = tmpdir_factory.mktemp("test_project")
    project = EmptyProject(str(project_dir))
    return project_dir, project


def test_empty_project(project_test, qtbot):
    """Test creation of an Empy project, and its configuration files."""
    project_dir, project = project_test
    assert project.root_path == str(project_dir)

    # Assert Project configs
    qtbot.wait(3000)
    for filename in [WORKSPACE, CODESTYLE, ENCODING, VCS]:
        config_path = os.path.join(project.root_path, '.spyproject',
                                   'config')
        files = os.listdir(config_path)
        assert filename + '.ini' in files


def test_set_load_recent_files(project_test):
    """Test saving and loading files from the configuration.

    Saving/loading should preserved the order, and remove duplicates.
    """
    project_dir, project = project_test

    # Create some files for testing
    files_paths = []
    for f in ['a.py', 'b.py', 'c.py']:
        file_ = project_dir.join(f)
        file_.write('# Some dummy content')
        files_paths.append(str(file_))

    # setting and loading
    project.set_recent_files(files_paths[:])
    assert project.get_recent_files() == files_paths

    # adding a duplicate elemnent
    files_paths_duplicate = files_paths + [files_paths[0]]
    assert len(files_paths_duplicate) == len(files_paths) + 1

    project.set_recent_files(files_paths_duplicate[:])
    assert project.get_recent_files() == files_paths


if __name__ == "__main__":
    pytest.main()
