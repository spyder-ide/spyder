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

# Test library imports
import pytest

# Local imports
from spyder.plugins.projects.widgets.explorer import ProjectExplorerTest
from spyder.py3compat import to_text_string


@pytest.fixture
def project_explorer(qtbot, request, tmpdir):
    """Setup Project Explorer widget."""
    directory = request.node.get_closest_marker('change_directory')
    if directory:
        project_dir = to_text_string(tmpdir.mkdir('project'))
    else:
        project_dir = None
    project_explorer = ProjectExplorerTest(directory=project_dir)
    qtbot.addWidget(project_explorer)
    return project_explorer


@pytest.mark.change_directory
def test_change_directory_in_project_explorer(project_explorer, qtbot):
    """Test changing a file from directory in the Project explorer."""
    # Create project
    project = project_explorer
    project_dir = project.directory

    # Create a temp project directory and file
    project_dir_tmp = osp.join(project_dir, u'測試')
    project_file = osp.join(project_dir, 'script.py')

    # Create an empty file in the project dir
    os.mkdir(project_dir_tmp)
    open(project_file, 'w').close()

    # Move Python file
    project.explorer.treewidget.move(
                            fnames=[osp.join(project_dir, 'script.py')],
                            directory=project_dir_tmp)

    # Assert content was moved
    assert osp.isfile(osp.join(project_dir_tmp, 'script.py'))


def test_project_explorer(project_explorer, qtbot):
    """Run project explorer."""
    project = project_explorer
    project.resize(250, 480)
    project.show()
    assert project


if __name__ == "__main__":
    pytest.main()
