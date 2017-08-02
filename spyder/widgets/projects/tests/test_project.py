# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
#
"""
Tests for __init__.py
"""

# Test library imports
import pytest
import os.path as osp

# Local imports
from spyder.widgets.projects import EmptyProject

from spyder.widgets.projects.config import (CODESTYLE, WORKSPACE, ENCODING,
                                            VCS)


@pytest.fixture(scope='session')
def project_test(tmpdir_factory):
    """
    Fixture for create a temporary project (mdw).

    Returns:
        str: Path of temporary project dir.
    """
    p = tmpdir_factory.mktemp("test_project")
    path = str(p)
    project = EmptyProject(path)
    return path, project


def test_empty_project(project_test):
    path, project = project_test
    assert project.root_path == path

    # Assert Project onfigs
    conf_files = project.get_conf_files()
    for dir_ in [CODESTYLE, WORKSPACE, ENCODING, VCS]:
        assert dir_ in conf_files
        project_config = conf_files[dir_]

        # assert configurations files
        assert osp.exists(project_config.filename())


if __name__ == "__main__":
    pytest.main()
