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
    project_dir = osp.join(getcwd_or_home(),
                           'temp_dir_test_file_explorer_functions')
    if not osp.exists(project_dir):
        os.mkdir(project_dir)
    if not osp.exists(project_dir):
        os.mkdir(project_dir)
    project_file1 = osp.join(project_dir, 'script.py')
    with open(project_file1, 'w') as fh:
        fh.write('Spyder4 will be released this year')
    project_file2 = osp.join(project_dir, 'pyscript.py')
    with open(project_file2, 'w') as fh:
        fh.write('Spyder4')
    subdir = osp.join(project_dir, 'subdir')
    if not osp.exists(subdir):
        os.mkdir(subdir)
    project_file3 = osp.join(subdir, 'Columbia.txt')
    with open(project_file3, 'w') as fh:
        fh.write('South America')
    file_list = [[project_file1], [project_file1, project_file2, subdir],
                 [project_file1, project_file3]]
    cb = QApplication.clipboard()
    project_explorer = ProjectExplorerTest2(directory=project_dir)
    qtbot.addWidget(project_explorer)
    yield project_explorer, file_list, cb
    if osp.exists(project_dir):
        shutil.rmtree(project_dir)


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


@pytest.mark.parametrize('path_method', ['absolute', 'relative'])
def test_copy_path(project_explorer_withfiles, path_method):
    """Test copy absolute and relative paths."""
    project, file_list, cb = project_explorer_withfiles
    for file_paths in file_list:
        project.explorer.treewidget.copy_path(fnames=file_paths,
                                              method=path_method)
        cb_output = cb.text(mode=cb.Clipboard)
        file_paths = [_fn.replace(os.sep, "/") for _fn in file_paths]
        if len(file_paths) > 1:
            if path_method == 'absolute':
                true_path = ''.join('"' + _fn + '",' + '\n' for _fn in
                                    file_paths)
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


# def test_copy_file(project_explorer_withfiles):
#     """Test copy file(s)/folders(s) to clipboard."""
#     project = project_explorer_withfiles
#     project.explorer.treewidget.copy_file_clipboard(fnames=file_paths)
#     cb_data = cb.mimeData().urls()
#     for url in cb_data:
#         file_name = url.toLocalFile()
#         assert osp.isdir(file_name) or osp.isfile(file_name)
#         if file_paths == [project_file1]:
#             with open(file_name, 'r') as fh:
#                 text_data = fh.read()
#             assert text_data == 'Spyder4 will be released this year'
#         if file_paths == [project_file1, project_file3][1]:
#             with open(file_name, 'r') as fh:
#                 text_data = fh.read()
#             assert text_data == 'South America'
#         if file_paths == [project_file1, project_file2, subdir][2]:
#             assert osp.isdir(file_name)


# def test_save_file(project_explorer_withfiles):
#     """Test save file(s)/folders(s) from clipboard."""
#     project = project_explorer_withfiles
#     project.explorer.treewidget.copy_file_clipboard(fnames=[project_file2])
#     project.explorer.treewidget.save_file_clipboard(fnames=file_paths)
#     assert osp.exists(osp.join(subdir, project_file2))
#     with open(osp.join(subdir, project_file2), 'r') as fh:
#         text_data = fh.read()
#     assert text_data == 'Spyder4'
#     project.explorer.treewidget.copy_file_clipboard(fnames=[subdir])
#     project.explorer.treewidget.save_file_clipboard(fnames=[subdir,
#                                                             project_file3])
#     assert osp.exists(subdir + '1')
#     for afile in [project_file3, osp.join(subdir, project_file2)]:
#         assert osp.basename(afile) in os.listdir(subdir + '1')
#         if afile == project_file3:
#             with open(osp.join(project_file3), 'r') as fh:
#                 text_data = fh.read()
#             assert text_data == 'South America'


if __name__ == "__main__":
    pytest.main()
