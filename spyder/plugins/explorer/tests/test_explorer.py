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

# Third party imports
from qtpy.QtWidgets import QApplication

# Local imports
from spyder.plugins.explorer.widgets import (FileExplorerTest,
                                             ProjectExplorerTest)
from spyder.py3compat import to_text_string
from spyder.utils.misc import getcwd_or_home
from spyder.plugins.projects.widgets.explorer import ProjectExplorerTest as \
    ProjectExplorerTest2


@pytest.fixture
def file_explorer(qtbot):
    """Set up FileExplorerTest."""
    widget = FileExplorerTest()
    qtbot.addWidget(widget)
    return widget


@pytest.fixture
def project_explorer(qtbot):
    """Set up FileExplorerTest."""
    widget = ProjectExplorerTest()
    qtbot.addWidget(widget)
    return widget


@pytest.fixture
def copy_path_file(qtbot):
    """Setup Project Explorer widget."""
    # directory = request.node.get_marker('change_directory')
    # if directory:
    #     project_dir = to_text_string(tmpdir.mkdir('project'))
    # else:
    #     project_dir = None
    project_dir = getcwd_or_home()
    project_explorer = ProjectExplorerTest2(directory=project_dir)
    qtbot.addWidget(project_explorer)
    return project_explorer


def test_file_explorer(file_explorer):
    """Run FileExplorerTest."""
    file_explorer.resize(640, 480)
    file_explorer.show()
    assert file_explorer


def test_project_explorer(project_explorer):
    """Run ProjectExplorerTest."""
    project_explorer.resize(640, 480)
    project_explorer.show()
    assert project_explorer

# @pytest.mark.parametrize('path', ["absolute", "relative"])
def test_copy_path(copy_path_file):
    """Test copy/paste files and their absolute/relative paths."""
    project = copy_path_file
    project_dir = project.directory
    project_file1 = osp.join(project_dir, 'script.py')
    open(project_file1, 'w').close()
    with open(project_file1, 'w') as fh:
        fh.write('Spyder4 will be released this year')
    cb = QApplication.clipboard()
    #  test copy absolute path
    project.explorer.treewidget.copy_path(fnames=[project_file1],
                                          method='absolute')
    asb_path = cb.text(mode=cb.Clipboard)
    assert project_file1.replace(os.sep, '/') == asb_path

    #  test copy relative path
    project.explorer.treewidget.copy_path(fnames=[project_file1],
                                          method='relative')
    rel_path = cb.text(mode=cb.Clipboard)
    len_rel_path = len(rel_path)
    assert project_file1.replace(os.sep, '/')[-len_rel_path:] == rel_path
    assert (project_dir.replace(os.sep, '/') + '/' + osp.basename(rel_path)
            == project_file1.replace(os.sep, '/'))
    assert project_file1.replace(os.sep, '/').endswith(rel_path)

    #  test copy file to clipboard
    project.explorer.treewidget.copy_file_clipboard(fnames=[project_file1])
    clipboard_data = cb.mimeData().urls()[0].toLocalFile()
    assert project_file1.replace(os.sep, "/") == clipboard_data.replace(os.sep,
                                                                        '/')
    project_file2 = osp.join(project_dir, 'pyscript.py')
    with open(project_file2, 'w') as fh:
        fh.write('Spyder4')
    project.explorer.treewidget.copy_file_clipboard(fnames=[project_file2])
    clipboard_data = cb.mimeData().urls()[0].toLocalFile()
    with open(clipboard_data, 'r') as fh:
        text_data = fh.read()
    assert text_data == "Spyder4"

    #  test save file from clipboard
    project.explorer.treewidget.save_file_clipboard(fnames=[project_file1])
    assert osp.exists(osp.join(project_dir, 'pyscript1.py'))
    project.explorer.treewidget.save_file_clipboard(fnames=[project_file2])
    assert osp.exists(osp.join(project_dir, 'pyscript2.py'))
    with open(osp.join(project_dir, 'pyscript2.py'), 'r') as fh:
        text_data = fh.read()
    assert text_data == "Spyder4"
    folder = osp.join(project_dir, 'subdir')
    if not osp.exists(folder):
        os.mkdir(folder)
    project.explorer.treewidget.copy_file_clipboard(fnames=[project_file1])
    project.explorer.treewidget.save_file_clipboard(fnames=[folder])
    assert osp.isfile(osp.join(folder, 'script.py'))
    with open(osp.join(folder, 'script.py'), 'r') as fh:
        text_data = fh.read()
    assert text_data == 'Spyder4 will be released this year'

if __name__ == "__main__":
    pytest.main()
