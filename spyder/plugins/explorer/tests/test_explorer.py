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

# Third party imports
from qtpy.QtWidgets import QApplication

# Local imports
from spyder.plugins.explorer.widgets import (FileExplorerTest,
                                             ProjectExplorerTest)
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
def project_explorer_withfiles(qtbot):
    """Setup Project Explorer widget."""
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


project_dir = getcwd_or_home()
if not osp.exists(project_dir):
    os.mkdir(project_dir)
project_file1 = osp.join(project_dir, 'project_explorer_withfiles_script.py')
with open(project_file1, 'w') as fh:
    fh.write('Spyder4 will be released this year')
project_file2 = osp.join(project_dir, 'project_explorer_withfiles_pyscript.py')
with open(project_file2, 'w') as fh:
    fh.write('Spyder4')
subdir = osp.join(project_dir, 'project_explorer_withfiles_subdir')
if not osp.exists(subdir):
    os.mkdir(subdir)
project_file3 = osp.join(subdir, 'project_explorer_withfiles_Columbia.txt')
with open(project_file3, 'w') as fh:
    fh.write('South America')
file_list = [project_file1, project_file2, subdir]
cb = QApplication.clipboard()


@pytest.mark.change_directory
@pytest.mark.parametrize('path_method', ['absolute', 'relative'])
@pytest.mark.parametrize('file_paths', [[project_file1],
                                        [project_file1, project_file2, subdir],
                                        [project_file1, project_file3]])
def test_copy_path(project_explorer_withfiles, path_method, file_paths):
    """Test copy absolute and relative paths."""
    project = project_explorer_withfiles
    project.explorer.treewidget.copy_path(fnames=file_paths,
                                          method=path_method)
    cb_output = cb.text(mode=cb.Clipboard)
    file_paths = [_fn.replace(os.sep, "/") for _fn in file_paths]
    if len(file_paths) > 1:
        if path_method == 'absolute':
            true_path = ''.join('"' + _fn + '",' + '\n' for _fn in file_paths)
        elif path_method == 'relative':
            true_path = ''.join('"' + osp.relpath(_fn, getcwd_or_home()).
                                replace(os.sep, "/") + '",' +
                                '\n' for _fn in file_paths)
        true_path = true_path[:-2]
    else:
        if path_method == 'absolute':
            true_path = file_paths[0]
        elif path_method == 'relative':
            true_path = (osp.relpath(file_paths[0], getcwd_or_home()).
                         replace(os.sep, "/"))
    assert true_path == cb_output


@pytest.mark.change_directory
@pytest.mark.parametrize('file_paths', [[project_file1],
                                        [project_file1, project_file2, subdir],
                                        [project_file1, project_file3]])
def test_copy_file(project_explorer_withfiles, file_paths):
    """Test copy file(s)/folders(s) to clipboard."""
    project = project_explorer_withfiles
    project.explorer.treewidget.copy_file_clipboard(fnames=file_paths)
    cb_data = cb.mimeData().urls()
    for url in cb_data:
        file_name = url.toLocalFile()
        assert osp.isdir(file_name) or osp.isfile(file_name)
        if file_paths == [project_file1]:
            with open(file_name, 'r') as fh:
                text_data = fh.read()
            assert text_data == 'Spyder4 will be released this year'
        if file_paths == [project_file1, project_file3][1]:
            with open(file_name, 'r') as fh:
                text_data = fh.read()
            assert text_data == 'South America'
        if file_paths == [project_file1, project_file2, subdir][2]:
            assert osp.isdir(file_name)


@pytest.mark.change_directory
@pytest.mark.parametrize('file_paths', [[subdir], [subdir, project_file3]])
def test_save_file(project_explorer_withfiles, file_paths):
    """Test save file(s)/folders(s) from clipboard."""
    project = project_explorer_withfiles
    project.explorer.treewidget.copy_file_clipboard(fnames=[project_file2])
    project.explorer.treewidget.save_file_clipboard(fnames=file_paths)
    assert osp.exists(osp.join(subdir, project_file2))
    with open(osp.join(subdir, project_file2), 'r') as fh:
        text_data = fh.read()
    assert text_data == 'Spyder4'
    project.explorer.treewidget.copy_file_clipboard(fnames=[subdir])
    project.explorer.treewidget.save_file_clipboard(fnames=[subdir,
                                                            project_file3])
    assert osp.exists(subdir + '1')
    for afile in [project_file3, osp.join(subdir, project_file2)]:
        assert osp.basename(afile) in os.listdir(subdir + '1')
        if afile == project_file3:
            with open(osp.join(project_file3), 'r') as fh:
                text_data = fh.read()
            assert text_data == 'South America'


def test_remove_files():
    subdir1 = subdir + '1'
    subdir2 = subdir + '2'
    project_file2_1 = osp.splitext(project_file2)[0] + '1.py'
    file_list.extend([subdir1, subdir2, project_file2_1])
    for file_name in file_list:
        if osp.isdir(file_name):
            shutil.rmtree(file_name)
        else:
            os.remove(file_name)
        assert not osp.exists(file_name)


if __name__ == "__main__":
    pytest.main()
