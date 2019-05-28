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
from qtpy.QtCore import Qt, QPoint, QEvent
from qtpy.QtGui import QMouseEvent
from qtpy.QtWidgets import QApplication
from qtpy.QtWidgets import QMessageBox

# Local imports
from spyder.plugins.explorer.widgets import (FileExplorerTest,
                                             ProjectExplorerTest)
from spyder.plugins.projects.widgets.explorer import ProjectExplorerTest as ProjectExplorerTest2


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


def test_copy_file(explorer_with_files):
    """Test copy file(s)/folders(s) to clipboard."""
    project, __, file_paths, __, cb = explorer_with_files
    project.explorer.treewidget.copy_file_clipboard(fnames=file_paths)
    cb_data = cb.mimeData().urls()
    assert len(cb_data) == len(file_paths)
    for url, expected_path in zip(cb_data, file_paths):
        file_name = url.toLocalFile()
        assert osp.normpath(file_name) == osp.normpath(expected_path)
        try:
            assert osp.isdir(file_name)
        except AssertionError:
            assert osp.isfile(file_name)
            with open(file_name, 'r') as fh:
                text = fh.read()
            assert text == "File Path:\n" + str(file_name)


def test_save_file(explorer_with_files):
    """Test save file(s)/folders(s) from clipboard."""
    project, dest, file_paths, __, __ = explorer_with_files
    project.explorer.treewidget.copy_file_clipboard(fnames=file_paths)
    dest.explorer.treewidget.save_file_clipboard(fnames=[dest.directory])
    for item in file_paths:
        destination_item = osp.join(dest.directory, osp.basename(item))
        assert osp.exists(destination_item)
        if osp.isfile(destination_item):
            with open(destination_item, 'r') as fh:
                text = fh.read()
            assert text == "File Path:\n" + str(item).replace(os.sep, '/')


def test_delete_file(explorer_with_files, mocker):
    """Test delete file(s)/folders(s)."""
    project, __, __, top_folder, __ = explorer_with_files
    mocker.patch.object(QMessageBox, 'warning', return_value=QMessageBox.Yes)
    project.explorer.treewidget.delete(fnames=[top_folder])
    assert not osp.exists(top_folder)


def test_single_click_to_open(qtbot, file_explorer):
    """Test single and double click open option for the file explorer."""
    file_explorer.show()

    treewidget = file_explorer.explorer.treewidget
    model = treewidget.model()
    cwd = os.getcwd()
    qtbot.keyClick(treewidget, Qt.Key_Up)  # To focus and select the 1st item
    initial_index = treewidget.currentIndex()  # To keep a reference

    def run_test_helper(single_click, initial_index):
        # Reset the widget
        treewidget.setCurrentIndex(initial_index)
        file_explorer.label3.setText('')
        file_explorer.label1.setText('')

        for i in range(4):  # 4 items inside `/spyder/plugins/explorer/`
            qtbot.keyClick(treewidget, Qt.Key_Down)
            index = treewidget.currentIndex()
            path = model.data(index)
            if path:
                full_path = os.path.join(cwd, path)
                # Skip folder to avoid changing the view for single click case
                if os.path.isfile(full_path):
                    rect = treewidget.visualRect(index)
                    pos = rect.center()
                    qtbot.mouseClick(treewidget.viewport(), Qt.LeftButton, pos=pos)

                    if single_click:
                        assert full_path == file_explorer.label1.text()
                    else:
                        assert full_path != file_explorer.label1.text()

    # Test single click to open
    treewidget.set_single_click_to_open(True)
    assert 'True' in file_explorer.label3.text()
    run_test_helper(single_click=True, initial_index=initial_index)

    # Test double click to open
    treewidget.set_single_click_to_open(False)
    assert 'False' in file_explorer.label3.text()
    run_test_helper(single_click=False, initial_index=initial_index)


if __name__ == "__main__":
    pytest.main()
