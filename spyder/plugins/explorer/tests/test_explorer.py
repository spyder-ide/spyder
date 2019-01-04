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

# Third party imports
import pytest
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
def project_explorer_withfiles(qtbot, request, tmpdir):
    """Setup Project Explorer widget."""
    directory = request.node.get_marker('change_directory')
    if directory:
        project_dir = to_text_string(tmpdir.mkdir('project'))
    else:
        project_dir = None
    project_explorer = ProjectExplorerTest2(directory=project_dir)
    qtbot.addWidget(project_explorer)
    return project_explorer


@pytest.fixture
def create_test_files_folders(project_explorer_withfiles):
    project = project_explorer_withfiles
    project_dir = project.directory
    project_folder = osp.join(project_dir, u'測試')
    if not osp.exists(project_folder):
        os.mkdir(project_folder)
    project_file1 = osp.join(project_folder, 'script.py')
    with open(project_file1, 'w') as fh:
        fh.write('Spyder4 will be released this year')
    project_file2 = osp.join(project_folder, 'pyscript.py')
    with open(project_file2, 'w') as fh:
        fh.write('Spyder4')
    subdir = osp.join(project_folder, 'subdir')
    if not osp.exists(subdir):
        os.mkdir(subdir)
    project_file3 = osp.join(subdir, 'Columbia.txt')
    with open(project_file3, 'w') as fh:
        fh.write('South America')
    file_list = [[project_file1], [project_file1, project_file2, subdir],
                 [project_file1, project_file3]]
    cb = QApplication.clipboard()
    yield file_list, cb
    if osp.exists(project_folder):
        shutil.rmtree(project_folder)

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
def test_copy_path(project_explorer_withfiles, create_test_files_folders, path_method):
    """Test copy absolute and relative paths."""
    project = project_explorer_withfiles
    file_list, cb = create_test_files_folders
    for file_paths in file_list:
        project.explorer.treewidget.copy_path(fnames=file_paths,
                                              method=path_method)
        cb_output = cb.text(mode=cb.Clipboard)
        file_paths = [_fn.replace(os.sep, '/') for _fn in file_paths]
        if len(file_paths) > 1:
            if path_method == 'absolute':
                true_path = ''.join('"' + _fn + '",' + '\n' for _fn in
                                    file_paths)
            elif path_method == 'relative':
                true_path = ''.join('"' + osp.relpath(_fn, getcwd_or_home()).
                                    replace(os.sep, '/') + '",' +
                                    '\n' for _fn in file_paths)
            true_path = true_path[:-2]
        else:
            if path_method == 'absolute':
                true_path = file_paths[0]
            elif path_method == 'relative':
                true_path = (osp.relpath(file_paths[0], getcwd_or_home()).
                             replace(os.sep, "/"))
        assert true_path == cb_output


def test_copy_file(project_explorer_withfiles, create_test_files_folders):
    """Test copy file(s)/folders(s) to clipboard."""
    project = project_explorer_withfiles
    file_list, cb = create_test_files_folders
    for file_paths in file_list:
        project.explorer.treewidget.copy_file_clipboard(fnames=file_paths)
        cb_data = cb.mimeData().urls()
        for url in cb_data:
            file_name = url.toLocalFile()
            assert osp.isdir(file_name) or osp.isfile(file_name)
            if file_paths == file_list[0]:
                with open(file_name, 'r') as fh:
                    text_data = fh.read()
                assert text_data == 'Spyder4 will be released this year'
            if file_paths == file_list[2][1]:
                with open(file_name, 'r') as fh:
                    text_data = fh.read()
                assert text_data == 'South America'
            if file_paths == file_list[1][2]:
                assert osp.isdir(file_name)


def test_save_file(project_explorer_withfiles, create_test_files_folders):
    """Test save file(s)/folders(s) from clipboard."""
    project = project_explorer_withfiles
    file_list = create_test_files_folders[0]
    file_list2 = [file_list[1][2], [file_list[1][2], file_list[2][1]]]
    for file_paths in file_list2:
        project.explorer.treewidget.copy_file_clipboard(
                fnames=[file_list[1][1]])
        project.explorer.treewidget.save_file_clipboard(fnames=file_paths)
        assert osp.exists(osp.join(file_list[1][2], file_list[1][1]))
        with open(osp.join(file_list[1][2], file_list[1][1]), 'r') as fh:
            text_data = fh.read()
        assert text_data == 'Spyder4'
        project.explorer.treewidget.copy_file_clipboard(
                fnames=[file_list[1][2]])
        project.explorer.treewidget.save_file_clipboard(
                fnames=[file_list[1][2], file_list[2][1]])
        assert osp.exists(file_list[1][2] + '1')
        for afile in [file_list[2][1],
                      osp.join(file_list[1][2], file_list[1][1])]:
            assert osp.basename(afile) in os.listdir(file_list[1][2] + '1')
            if afile == file_list[2][1]:
                with open(osp.join(file_list[2][1]), 'r') as fh:
                    text_data = fh.read()
                assert text_data == 'South America'


if __name__ == "__main__":
    pytest.main()
