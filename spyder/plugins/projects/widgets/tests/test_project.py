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
from spyder.plugins.projects.api import EmptyProject
from spyder.plugins.projects.utils.config import (CODESTYLE, WORKSPACE,
                                                  ENCODING, VCS)


@pytest.fixture(scope='session')
def project_test(tmpdir_factory):
    """
    Fixture for create a temporary project.

    Returns:
        project_dir: fixture of temporary project dir.
        project: EmptyProject object.
    """
    project_dir = tmpdir_factory.mktemp("test_project")
    os.makedirs(osp.join(str(project_dir), '.spyproject', 'config'))
    project = EmptyProject(str(project_dir))
    return project_dir, project


def test_empty_project(project_test, qtbot):
    """Test creation of an Empy project, and its configuration files."""
    project_dir, project = project_test
    assert project.root_path == str(project_dir)

    print(project.root_path, os.listdir(osp.join(project.root_path,
                                        '.spyproject', 'config')))

    # Assert Project configs
    conf_files = project.get_conf_files()

    qtbot.wait(3000)
    for filename in [CODESTYLE, ENCODING, VCS]:
        assert filename in conf_files
        project_config = conf_files[filename]

        # assert configurations files
        fpath = project_config.get_config_fpath()
        print([fpath])
        assert osp.isfile(fpath)


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
