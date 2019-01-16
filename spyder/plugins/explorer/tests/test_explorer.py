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


@pytest.fixture(params=[['script.py'],
                        ['script.py', 'script1.py', 'testdir/script2.py'],
                        ['subdir/innerdir/text.txt', 'testdir']])
def create_folders_files(tmpdir, request):
    """A project directory with dirs and files for testing."""
    project_dir = to_text_string(tmpdir.mkdir('project'))
    destination_dir = to_text_string(tmpdir.mkdir('destination'))
    list_paths = []
    for item in request.param:
        if osp.splitext(item)[1]:
            if osp.split(item)[0]:
                dirs, fname = osp.split(item)
                dirpath = osp.join(project_dir, dirs)
                if not osp.exists(dirpath):
                    os.makedirs(dirpath)
                    item_path = osp.join(dirpath, fname)
            else:
                item_path = osp.join(project_dir, item)
        else:
            dirpath = osp.join(project_dir, item)
            if not osp.exists(dirpath):
                os.makedirs(dirpath)
                item_path = dirpath
        if not osp.isdir(item_path):
            with open(item_path, 'w') as fh:
                fh.write("File Path:\n" + str(item_path) + '\n')
        list_paths.append(item_path)
    return list_paths, project_dir, destination_dir


@pytest.fixture(params=[FileExplorerTest, ProjectExplorerTest2])
def explorer_with_files(qtbot, create_folders_files, request):
    """Setup Project/File Explorer widget."""
    cb = QApplication.clipboard()
    list_paths, project_dir, destination_dir = create_folders_files
    project_explorer_orig = request.param(directory=project_dir)
    project_explorer_dest = request.param(directory=destination_dir)
    qtbot.addWidget(project_explorer_orig)
    qtbot.addWidget(project_explorer_dest)
    return project_explorer_orig, project_explorer_dest, list_paths, cb


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
    project, _, file_paths, cb = explorer_with_files
    project.explorer.treewidget.copy_path(fnames=file_paths,
                                          method=path_method)
    cb_output = cb.text(mode=cb.Clipboard)
    path_list = [path.strip(',').strip('"') for path in cb_output.splitlines()]
    for path in path_list:
        assert osp.exists(path)


def test_copy_file(explorer_with_files):
    """Test copy file(s)/folders(s) to clipboard."""
    project, _, file_paths, cb = explorer_with_files
    project.explorer.treewidget.copy_file_clipboard(fnames=file_paths)
    cb_data = cb.mimeData().urls()
    for url, expected_path in zip(cb_data, file_paths):
        file_name = url.toLocalFile()
        assert file_name == expected_path.replace(os.sep, '/')
        try:
            assert osp.isdir(file_name)
        except AssertionError:
            assert osp.isfile(file_name)
            with open(file_name, 'r') as fh:
                text = fh.read().replace('\\', '/')
            assert text == "File Path:\n" + str(file_name) + '\n'


def test_save_file(explorer_with_files):
    """Test save file(s)/folders(s) from clipboard."""
    project, dest, file_paths, _ = explorer_with_files
    project.explorer.treewidget.copy_file_clipboard(fnames=file_paths)
    dest.explorer.treewidget.save_file_clipboard(fnames=[dest.directory])
    for item in file_paths:
        destination_item = osp.join(dest.directory, osp.basename(item))
        assert osp.exists(destination_item)
        if osp.isfile(destination_item):
            with open(destination_item, 'r') as fh:
                text = fh.read()
            assert text == "File Path:\n" + str(item) + '\n'


if __name__ == "__main__":
    pytest.main()
