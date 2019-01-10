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
from spyder.utils.misc import get_common_path
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
def project_explorer_with_files(qtbot, tmpdir):
    """Setup Project Explorer widget."""
    cb = QApplication.clipboard()
    project_dir = to_text_string(tmpdir.mkdir('project'))
    project_explorer = ProjectExplorerTest2(directory=project_dir)
    qtbot.addWidget(project_explorer)
    return project_explorer, cb


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


def create_folder_files(file_paths, project_dir):
    """Function to create folders and files to be used in test functions."""
    list_paths = []
    for item in file_paths:
        #  ignore empty string
        if item:
            #  create folders
            if osp.splitext(item)[1]:
                if osp.split(item)[0]:
                    dirs, fname = osp.split(item)
                    os.makedirs(dirs, exist_ok=True)
                    dirpath = osp.join(project_dir, dirs)
                    item_path = osp.join(dirpath, fname)
                else:
                    item_path = osp.join(project_dir, item)
            else:
                dirpath = osp.join(project_dir, item)
                os.makedirs(dirpath, exist_ok=True)
                item_path = dirpath
            #  create files with some texts
            if item_path.endswith('script.py'):
                with open(item_path, 'w') as fh:
                    fh.write('Python')
            elif item_path.endswith('script1.py'):
                with open(item_path, 'w') as fh:
                    fh.write('Spyder4')
            elif item_path.endswith('script2.py'):
                with open(item_path, 'w') as fh:
                    fh.write('Jan-2019')
            #  append item path names to the list
            list_paths.append(item_path)
    return list_paths


@pytest.mark.parametrize('path_method', ['absolute', 'relative'])
@pytest.mark.parametrize('file_paths',
                         [['script.py'],
                          ['script.py', 'script1.py', 'testdir/script2.py'],
                          ['', 'testdir']])
def test_copy_path(project_explorer_with_files, path_method, file_paths):
    """Test copy absolute and relative paths."""
    project, cb = project_explorer_with_files
    project_dir = project.directory
    file_paths = create_folder_files(file_paths, project_dir)
    home_directory = project.explorer.treewidget.fsmodel.rootPath()
    #  copy selected items [fnames]
    project.explorer.treewidget.copy_path(fnames=file_paths,
                                          method=path_method)
    #  get the copied items from clipboard
    cb_output = cb.text(mode=cb.Clipboard)
    #  create true path names simulating what copy_path function does
    file_paths = [_fn.replace(os.sep, '/') for _fn in file_paths]
    if len(file_paths) > 1:
        if path_method == 'absolute':
            true_path = ''.join('"' + _fn + '",' + '\n' for _fn in
                                file_paths)
        elif path_method == 'relative':
            true_path = ''.join('"' + osp.relpath(_fn, home_directory).
                                replace(os.sep, '/') + '",' +
                                '\n' for _fn in file_paths)
        true_path = true_path[:-2]
    else:
        if path_method == 'absolute':
            true_path = file_paths[0]
        elif path_method == 'relative':
            true_path = (osp.relpath(file_paths[0], home_directory).
                         replace(os.sep, '/'))
    #  compare true results with clipboard data
    assert true_path == cb_output


@pytest.mark.parametrize('file_paths',
                         [['script.py'],
                          ['script.py', 'script1.py', 'testdir/script2.py'],
                          ['', 'testdir']])
def test_copy_file(project_explorer_with_files, file_paths):
    """Test copy file(s)/folders(s) to clipboard."""
    project, cb = project_explorer_with_files
    project_dir = project.directory
    file_paths = create_folder_files(file_paths, project_dir)
    project.explorer.treewidget.copy_file_clipboard(fnames=file_paths)
    cb_data = cb.mimeData().urls()
    for url in cb_data:
        file_name = url.toLocalFile()
        try:
            assert osp.isdir(file_name)
        except AssertionError:
            assert osp.isfile(file_name)
        if file_name.endswith('script.py'):
            with open(file_name, 'r') as fh:
                text_data = fh.read()
            assert text_data == 'Python'
        if file_name.endswith('script1.py'):
            with open(file_name, 'r') as fh:
                text_data = fh.read()
            assert text_data == 'Spyder4'
        if file_name.endswith('script2.py'):
            with open(file_name, 'r') as fh:
                text_data = fh.read()
            assert text_data == 'Jan-2019'


@pytest.mark.parametrize('file_paths',
                         [['script.py'],
                          ['script.py', 'script1.py', 'testdir/script2.py'],
                          ['', 'testdir']])
def test_save_file(project_explorer_with_files, file_paths):
    """Test save file(s)/folders(s) from clipboard."""
    project = project_explorer_with_files[0]
    project_dir = project.directory
    file_paths = create_folder_files(file_paths, project_dir)
    #  copy items
    project.explorer.treewidget.copy_file_clipboard(fnames=file_paths)
    #  paste items at the selected fnames common directory
    # project.explorer.treewidget.save_file_clipboard(fnames=file_paths)
    # common_path = get_common_path(file_paths)
    # if len(file_paths) == 1:
    #     #  'script1.py' is already exists in the common path
    #     assert osp.exists(osp.join(common_path, 'script2.py'))
    #     with open(osp.join(common_path, 'script2.py'), 'r') as fh:
    #         text_data = fh.read()
    #     assert text_data == 'Python'
#     if len(file_paths) == 3:
#         #  'script2.py' is created before
#         assert osp.exists(osp.join(common_path, 'script3.py'))
#         with open(osp.join(common_path, 'script3.py'), 'r') as fh:
#             text_data = fh.read()
#         assert text_data == 'Python'
#         #  script4.py is a copy of original 'script1.py'
#         assert osp.exists(osp.join(common_path, 'script4.py'))
#         with open(osp.join(common_path, 'script4.py'), 'r') as fh:
#             text_data = fh.read()
#         assert text_data == 'Spyder4'
#         assert osp.exists(osp.join(common_path, 'script5.py'))
#         with open(osp.join(common_path, 'script5.py'), 'r') as fh:
#             text_data = fh.read()
#         assert text_data == 'Jan-2019'
#     if len(file_paths) == 2:
#         assert osp.exists(osp.join(common_path, 'testdir1'))


if __name__ == "__main__":
    pytest.main()
