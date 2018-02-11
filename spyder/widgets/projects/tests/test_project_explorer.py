# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
#

"""
Tests for explorer.py
"""
# Standard imports
import os
import os.path as osp
import shutil

# Test library imports
import pytest

# Local imports
from spyder.widgets.projects.explorer import ProjectExplorerTest

@pytest.fixture
def setup_projects_explorer(qtbot, directory=None):
    """Set up ProjectExplorerWidgetTest."""
    project_explorer = ProjectExplorerTest(directory=directory)
    qtbot.addWidget(project_explorer)
    return project_explorer


def test_change_directory_in_project_explorer(qtbot, tmpdir):
    """Test changing a file from directory in the Project explorer."""
    # Create a temp project directory
    project_dir = str(tmpdir.mkdir('project'))
    project_dir_tmp = osp.join(project_dir, 'tmpá')
    project_file = osp.join(project_dir, 'script.py')

    # Create an empty file in the project dir
    os.mkdir(project_dir_tmp)
    open(project_file, 'w').close()

    # Create project
    projects = setup_projects_explorer(qtbot, directory=project_dir)

    # Move Python file
    projects.treewidget.move(fnames=[osp.join(project_dir, 'script.py')],
                             directory=project_dir_tmp)

    # Assert content was moved
    assert osp.isfile(osp.join(project_dir_tmp, 'script.py'))

    # Close project
    projects.close_project()


def test_project_explorer(qtbot):
    """Run project explorer."""
    project_explorer = setup_projects_explorer(qtbot)
    project_explorer.resize(250, 480)
    project_explorer.show()
    assert project_explorer


if __name__ == "__main__":
    pytest.main()
