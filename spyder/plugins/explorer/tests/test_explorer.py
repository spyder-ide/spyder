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

# Local imports
from spyder.plugins.explorer.widgets import (FileExplorerTest,
                                             ProjectExplorerTest, QMessageBox)
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


@pytest.fixture(params=[['script.py', 'dir1/dir2/dir3/dir4/dir5/dir6/dir7'],
                        ['script.py', 'script1.py', 'testdir/script2.py'],
                        ['subdir/innerdir/dir3/text.txt',
                         'dir1/dir2/dir3/dir4', 'dir1/dir2/dir3/file.txt',
                         'dir1/dir2/dir3/dir4/dir5',
                         'dir1/dir2/dir3/dir4/dir5/text.txt',
                         'dir1/dir2/dir3/dir4/dir5/dir6/dir7/python.py']])
def create_folders_files(tmpdir, request):
    """A project directory with dirs and files for testing."""
    project_dir = to_text_string(tmpdir.mkdir('project'))
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
    return list_paths, project_dir


@pytest.fixture(params=[FileExplorerTest, ProjectExplorerTest2])
def explorer_with_files(qtbot, create_folders_files, request):
    """Setup Project/File Explorer widget."""
    list_paths, project_dir = create_folders_files
    project_explorer_orig = request.param(directory=project_dir)
    qtbot.addWidget(project_explorer_orig)
    return project_explorer_orig, list_paths


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


def test_delete_files_folders(explorer_with_files, mocker):
    """Test delete file(s)/folders(s)."""
    project, file_paths = explorer_with_files
    mocker.patch.object(QMessageBox, 'warning', return_value=QMessageBox.Yes)
    project.explorer.treewidget.delete(fnames=file_paths)
    for item in file_paths:
        assert not osp.exists(item)


if __name__ == "__main__":
    pytest.main()
