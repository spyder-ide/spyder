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

# Third party imports
import pytest
from qtpy.QtWidgets import QApplication
from qtpy.QtWidgets import QMessageBox

# Local imports
from spyder.plugins.explorer.widgets import (FileExplorerTest,
                                             ProjectExplorerTest)
from spyder.py3compat import to_text_string
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


@pytest.fixture(params=[['script.py', 'dir1/dir2/dir3/dir4'],
                        ['script.py', 'script1.py', 'testdir/dir1/script2.py'],
                        ['subdir/innerdir/dir3/text.txt', 'dir1/dir2/dir3',
                         'dir1/dir2/dir3/file.txt',
                         'dir1/dir2/dir3/dir4/python.py']])
def create_folders_files(tmpdir, request):
    """A project directory with dirs and files for testing."""
    project_dir = to_text_string(tmpdir.mkdir('project'))
    destination_dir = to_text_string(tmpdir.mkdir('destination'))
    top_folder = osp.join(project_dir, 'top_folder_in_proj')
    if not osp.exists(top_folder):
        os.mkdir(top_folder)
    list_paths = []
    for item in request.param:
        if osp.splitext(item)[1]:
            if osp.split(item)[0]:
                dirs, fname = osp.split(item)
                dirpath = osp.join(top_folder, dirs)
                if not osp.exists(dirpath):
                    os.makedirs(dirpath)
                    item_path = osp.join(dirpath, fname)
            else:
                item_path = osp.join(top_folder, item)
        else:
            dirpath = osp.join(top_folder, item)
            if not osp.exists(dirpath):
                os.makedirs(dirpath)
                item_path = dirpath
        if not osp.isdir(item_path):
            with open(item_path, 'w') as fh:
                fh.write("File Path:\n" + str(item_path).replace(os.sep, '/'))
        list_paths.append(item_path)
    return list_paths, project_dir, destination_dir, top_folder


@pytest.fixture(params=[FileExplorerTest, ProjectExplorerTest2])
def explorer_with_files(qtbot, create_folders_files, request):
    """Setup Project/File Explorer widget."""
    cb = QApplication.clipboard()
    paths, project_dir, destination_dir, top_folder = create_folders_files
    explorer_orig = request.param(directory=project_dir)
    explorer_dest = request.param(directory=destination_dir)
    qtbot.addWidget(explorer_orig)
    qtbot.addWidget(explorer_dest)
    return explorer_orig, explorer_dest, paths, top_folder, cb


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
def test_copy_path(explorer_with_files, path_method):
    """Test copy absolute and relative paths."""
    project, __, file_paths, __, cb = explorer_with_files
    explorer_directory = project.explorer.treewidget.fsmodel.rootPath()
    copied_from = project.explorer.treewidget.parent_widget.__class__.__name__
    project.explorer.treewidget.copy_path(fnames=file_paths,
                                          method=path_method)
    cb_output = cb.text(mode=cb.Clipboard)
    path_list = [path.strip(',"') for path in cb_output.splitlines()]
    assert len(path_list) == len(file_paths)
    for path, expected_path in zip(path_list, file_paths):
        if path_method == 'relative':
            expected_path = osp.relpath(expected_path, explorer_directory)
            if copied_from == 'ProjectExplorerWidget':
                expected_path = os.sep.join(expected_path.strip(os.sep).
                                            split(os.sep)[1:])
        assert osp.normpath(path) == osp.normpath(expected_path)


def test_delete_files_folders(explorer_with_files, mocker):
    """Test delete file(s)/folders(s)."""
    project, __, top_folder = explorer_with_files
    mocker.patch.object(QMessageBox, 'warning', return_value=QMessageBox.Yes)
    project.explorer.treewidget.delete(fnames=[top_folder])
    assert not osp.exists(top_folder)


if __name__ == "__main__":
    pytest.main()
