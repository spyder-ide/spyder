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

# Third Party imports
from qtpy.QtCore import Qt

# Local imports
from spyder.plugins.projects.widgets.explorer import ProjectExplorerTest
from spyder.py3compat import to_text_string
from spyder.utils import programs


@pytest.fixture
def project_explorer(qtbot, request, tmpdir):
    """Setup Project Explorer widget."""
    directory = request.node.get_marker('change_directory')
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


@pytest.mark.change_directory
def test_project_vcs_color(project_explorer, qtbot):
    """Test that files are colored according to their commit state."""
    # Create project
    project_explorer.show()
    project_dir = project_explorer.directory
    test_dir = os.getcwd()
    os.chdir(str(project_dir))

    # Create files for the repository
    files = []
    for n in range(5):
        files.append(osp.join(project_dir, 'file%i.py' % n))
        if n > 0:
            open(files[n], 'w').close()

    # Init the repo and set some files to different states
    gitcmds = [['init', '.'],
               ['config', '--local', 'user.email', '"john@doe.com"'],
               ['add', 'file2.py', 'file4.py'],
               ['commit', '-m', 'test']]
    for g_cmd in gitcmds:
        p = programs.run_program('git', g_cmd, cwd=project_dir)
        p.communicate()
    # change file 3 and add the changes
    f = open(files[2], 'a')
    f.writelines('text')
    f.close()
    p = programs.run_program('git', ['add', 'file3.py'], cwd=project_dir)
    p.communicate()
    # Write file1 into .gitignore
    gitign = open(osp.join(project_dir, '.gitignore'), 'a')
    gitign.writelines('file1.py')
    gitign.close()

    # Check that the files have their according colors
    tree = project_explorer.explorer.treewidget
    pcolors = tree.fsmodel.color_array
    # Conflict is not tested
    pcolors.remove(pcolors[4])

    # Check if the correct colors are set
    tree.expandAll()
    tree.fsmodel.set_vcs_state(project_dir)
    qtbot.waitForWindowShown(project_explorer.explorer)
    tree.fsmodel.on_project_loaded()
    with qtbot.waitSignal(tree.fsmodel.layoutChanged, raising=False):
        open(files[0], 'w').close()
    ind0 = tree.fsmodel.index(tree.fsmodel.rootPath()).child(0, 0)
    for n in range(5):
        assert tree.fsmodel.index(n, 0, ind0).data(Qt.TextColorRole).name() \
            == pcolors[n].name()
    os.chdir(test_dir)


if __name__ == "__main__":
    pytest.main()
