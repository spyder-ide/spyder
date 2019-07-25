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
import sys

# Third party imports
import pytest
from qtpy.QtCore import QEvent, QPoint, Qt, QTimer
from qtpy.QtGui import QMouseEvent
from qtpy.QtWidgets import QApplication, QMenu, QMessageBox

# Local imports
from spyder.plugins.explorer.widgets.explorer import (FileExplorerTest,
                                                      ProjectExplorerTest)
from spyder.plugins.projects.widgets.explorer import (
    ProjectExplorerTest as ProjectExplorerTest2)


@pytest.fixture
def file_explorer(qtbot):
    """Set up FileExplorerTest."""
    widget = FileExplorerTest()
    qtbot.addWidget(widget)
    return widget


@pytest.fixture
def file_explorer_associations(qtbot):
    """Set up FileExplorerTest."""
    if os.name == 'nt':
        ext = '.exe'
    elif sys.platform == 'darwin':
        ext = '.app'
    else:
        ext = '.desktop'

    associations = {
        '*.txt': [
            ('App 1', '/some/fake/some_app_1' + ext),
        ],
        '*.json,*.csv': [
            ('App 2', '/some/fake/some_app_2' + ext),
            ('App 1', '/some/fake/some_app_1' + ext),
        ],
    }
    widget = FileExplorerTest(file_associations=associations)
    widget.show()
    qtbot.addWidget(widget)
    return widget


@pytest.fixture
def project_explorer(qtbot):
    """Set up FileExplorerTest."""
    widget = ProjectExplorerTest()
    qtbot.addWidget(widget)
    return widget


def create_timer(func, interval=500):
    """Helper function to help interact with modal dialogs."""
    timer = QTimer()
    timer.setInterval(interval)
    timer.setSingleShot(True)
    timer.timeout.connect(func)
    timer.start()
    return timer


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

        for __ in range(4):  # 4 items inside `/spyder/plugins/explorer/`
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


def test_get_common_file_associations(qtbot, file_explorer_associations):
    widget = file_explorer_associations.explorer.treewidget
    associations = widget.get_common_file_associations(
        [
            '/some/path/file.txt',
            '/some/path/file1.json',
            '/some/path/file2.csv',
        ])
    if os.name == 'nt':
        ext = '.exe'
    elif sys.platform == 'darwin':
        ext = '.app'
    else:
        ext = '.desktop'
    assert associations[0][-1] == '/some/fake/some_app_1' + ext


def test_get_file_associations(qtbot, file_explorer_associations):
    widget = file_explorer_associations.explorer.treewidget
    associations = widget.get_file_associations('/some/path/file.txt')
    if os.name == 'nt':
        ext = '.exe'
    elif sys.platform == 'darwin':
        ext = '.app'
    else:
        ext = '.desktop'
    assert associations[0][-1] == '/some/fake/some_app_1' + ext


def test_create_file_manage_actions(qtbot, file_explorer_associations,
                                    tmp_path):
    widget = widget = file_explorer_associations.explorer.treewidget
    fpath = tmp_path / 'text.txt'
    fpath.write_text(u'hello!')
    fpath_2 = tmp_path / 'text.json'
    fpath_2.write_text(u'hello!')
    fpath_3 = tmp_path / 'text.md'
    fpath_3.write_text(u'hello!')

    # Single file with valid association
    actions = widget.create_file_manage_actions([str(fpath)])
    action_texts = [action.title().lower() for action in actions
                    if isinstance(action, QMenu)]
    assert 'open with' in action_texts

    # Two files with valid association
    actions = widget.create_file_manage_actions([str(fpath), str(fpath_2)])
    action_texts = [action.title().lower() for action in actions
                    if isinstance(action, QMenu)]
    assert 'open with' in action_texts

    # Single file with no association
    actions = widget.create_file_manage_actions([str(fpath_3)])
    action_texts = [action.title().lower() for action in actions
                    if isinstance(action, QMenu)]
    assert not action_texts


def test_clicked(qtbot, file_explorer_associations, tmp_path):
    widget = file_explorer_associations.explorer.treewidget
    some_dir = tmp_path / 'some_dir'
    some_dir.mkdir()
    fpath = some_dir / 'text.txt'
    fpath.write_text(u'hello!')
    widget.set_show_all(True)
    widget.chdir(str(some_dir))
    qtbot.wait(500)

    # Select first item
    qtbot.keyClick(widget, Qt.Key_Up)

    # Test click
    def interact():
        msgbox = widget.findChild(QMessageBox)
        assert msgbox
        qtbot.keyClick(msgbox, Qt.Key_Return)

    _ = create_timer(interact)
    qtbot.keyClick(widget, Qt.Key_Return)

    # Test no message box
    def interact_2():
        msgbox = widget.findChild(QMessageBox)
        assert not msgbox

    widget.set_file_associations({})
    _ = create_timer(interact_2)
    qtbot.keyClick(widget, Qt.Key_Return)


def test_check_launch_error_codes(qtbot, file_explorer_associations):
    widget = file_explorer_associations.explorer.treewidget

    # Check no problems
    return_codes = {'some-command': 0, 'some-other-command': 0}
    assert widget.check_launch_error_codes(return_codes)

    # Check problem
    def interact():
        msgbox = widget.findChild(QMessageBox)
        assert msgbox
        qtbot.keyClick(msgbox, Qt.Key_Return)

    return_codes = {'some-command': 1}
    _ = create_timer(interact)
    res = widget.check_launch_error_codes(return_codes)
    assert not res

    # Check problems
    def interact_2():
        msgbox = widget.findChild(QMessageBox)
        assert msgbox
        qtbot.keyClick(msgbox, Qt.Key_Return)

    return_codes = {'some-command': 1, 'some-other-command': 1}
    _ = create_timer(interact_2)
    res = widget.check_launch_error_codes(return_codes)
    assert not res


def test_open_association(qtbot, file_explorer_associations, tmp_path):
    widget = file_explorer_associations.explorer.treewidget
    some_dir = tmp_path / 'some_dir'
    some_dir.mkdir()
    fpath = some_dir / 'text.txt'
    fpath.write_text(u'hello!')

    # Select first item
    qtbot.keyClick(widget, Qt.Key_Down)

    def interact():
        msgbox = widget.findChild(QMessageBox)
        assert msgbox
        qtbot.keyClick(msgbox, Qt.Key_Return)

    _ = create_timer(interact)
    widget.open_association('some-app')


if __name__ == "__main__":
    pytest.main()
