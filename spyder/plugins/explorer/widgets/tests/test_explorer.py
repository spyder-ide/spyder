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
from qtpy.QtCore import QFile, Qt, QTimer
from qtpy.QtGui import QClipboard
from qtpy.QtWidgets import (
    QApplication,
    QDialog,
    QDialogButtonBox,
    QFileSystemModel,
    QInputDialog,
    QMessageBox,
    QTextEdit,
)

# Local imports
from spyder.plugins.explorer.widgets import explorer, main_widget
from spyder.plugins.explorer.widgets.main_widget import FileExplorerTest
from spyder.plugins.explorer.widgets.utils import (
    is_network_path,
    is_unc_path,
)
from spyder.plugins.projects.widgets.main_widget import ProjectExplorerTest


HERE = osp.abspath(osp.dirname(__file__))


@pytest.fixture
def file_explorer(qtbot):
    """Set up FileExplorerTest."""
    widget = FileExplorerTest()
    widget.show()
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
    qtbot.addWidget(widget)
    return widget


@pytest.fixture
def unwatched_explorer(file_explorer, tmp_path, monkeypatch, qtbot):
    """
    Set up a file explorer showing a folder that Qt doesn't watch for
    changes, which is what happens with UNC paths on Windows.
    """
    for module in [explorer, main_widget]:
        monkeypatch.setattr(module, "is_unc_path", lambda path: True)

    widget = file_explorer.explorer
    treewidget = widget.treewidget
    treewidget.fsmodel.setOption(QFileSystemModel.DontWatchForChanges, True)

    # Resolve the path because getcwd returns it that way (e.g. on macOS)
    folder = tmp_path.resolve()
    (folder / "subdir").mkdir()
    (folder / "file.txt").touch()
    widget.chdir(str(folder))
    qtbot.waitUntil(lambda: "file.txt" in shown_names(treewidget))

    return widget, folder


def shown_names(treewidget, folder=None):
    """Names shown by treewidget in its root or in folder."""
    model = treewidget.fsmodel
    if folder is None:
        parent = treewidget.rootIndex()
    else:
        parent = model.index(str(folder))

    return {
        model.fileName(model.index(row, 0, parent))
        for row in range(model.rowCount(parent))
    }


def create_timer(func, interval=500):
    """Helper function to help interact with modal dialogs."""
    timer = QTimer()
    timer.setInterval(interval)
    timer.setSingleShot(True)
    timer.timeout.connect(func)
    timer.start()
    return timer


@pytest.fixture(params=[FileExplorerTest, ProjectExplorerTest])
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


@pytest.mark.parametrize('path_method', ['absolute', 'relative'])
def test_copy_path(explorer_with_files, path_method):
    """Test copy absolute and relative paths."""
    project, __, file_paths, __, cb = explorer_with_files
    explorer_directory = project.explorer.treewidget.fsmodel.rootPath()
    copied_from = project.explorer.treewidget._parent.__class__.__name__
    project.explorer.treewidget.copy_path(fnames=file_paths,
                                          method=path_method)
    cb_output = cb.text(mode=QClipboard.Clipboard)
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


@pytest.mark.parametrize("permanently", [True, False])
def test_delete_folder_without_trash(explorer_with_files, mocker, permanently):
    """
    Test that folders that can't be moved to the trash are deleted
    permanently only if users agree.

    This is a regression test for spyder-ide/spyder#26432
    """
    project, __, __, top_folder, __ = explorer_with_files
    treewidget = project.explorer.treewidget

    # Simulate a network share, which doesn't have a trash
    mocker.patch.object(explorer, "is_network_path", return_value=True)
    mocker.patch.object(QFile, "moveToTrash", return_value=(False, ""))

    # The first dialog asks to delete the folder and the second one to do it
    # permanently
    warning = mocker.patch.object(
        QMessageBox,
        "warning",
        side_effect=[
            QMessageBox.Yes,
            QMessageBox.Yes if permanently else QMessageBox.No,
        ],
    )
    tree_removed = mocker.Mock()
    treewidget.sig_tree_removed.connect(tree_removed)

    treewidget.delete(fnames=[top_folder])

    assert warning.call_count == 2
    assert osp.exists(top_folder) is not permanently
    assert tree_removed.called is permanently


def test_delete_files_without_trash(explorer_with_files, mocker):
    """
    Test that selecting Yes to All when deleting several files that can't be
    moved to the trash only asks once to delete them permanently.

    This is a regression test for spyder-ide/spyder#26432
    """
    project, __, __, top_folder, __ = explorer_with_files
    treewidget = project.explorer.treewidget
    fnames = []
    for name in ["a.txt", "b.txt", "c.txt"]:
        fname = osp.join(top_folder, name)
        with open(fname, "w") as f:
            f.write(name)
        fnames.append(fname)

    mocker.patch.object(explorer, "is_network_path", return_value=True)
    mocker.patch.object(QFile, "moveToTrash", return_value=(False, ""))
    warning = mocker.patch.object(
        QMessageBox,
        "warning",
        side_effect=[QMessageBox.YesToAll, QMessageBox.YesToAll],
    )
    removed = mocker.Mock()
    treewidget.sig_removed.connect(removed)

    treewidget.delete(fnames=fnames)

    assert warning.call_count == 2
    assert not any(osp.exists(fname) for fname in fnames)
    assert removed.call_count == 3


def test_delete_without_trash_outside_network(explorer_with_files, mocker):
    """
    Test that an error is shown when files outside network shares can't be
    moved to the trash, instead of deleting them permanently.

    This is a regression test for spyder-ide/spyder#26432
    """
    project, __, __, top_folder, __ = explorer_with_files
    treewidget = project.explorer.treewidget
    mocker.patch.object(QFile, "moveToTrash", return_value=(False, ""))
    warning = mocker.patch.object(
        QMessageBox, "warning", return_value=QMessageBox.Yes
    )
    critical = mocker.patch.object(QMessageBox, "critical")
    tree_removed = mocker.Mock()
    treewidget.sig_tree_removed.connect(tree_removed)

    treewidget.delete(fnames=[top_folder])

    # Only the first dialog is shown, followed by an error
    assert warning.call_count == 1
    assert critical.call_count == 1
    assert osp.exists(top_folder)
    assert not tree_removed.called


def test_rename_file_with_files(explorer_with_files, mocker, qtbot):
    """Test that rename_file renames the file and sends out right signal."""
    project, __, file_paths, __, __ = explorer_with_files
    for old_path in file_paths:
        if osp.isfile(old_path):
            old_basename = osp.basename(old_path)
            new_basename = 'new' + old_basename
            new_path = osp.join(osp.dirname(old_path), new_basename)
            mocker.patch.object(QInputDialog, 'getText',
                                return_value=(new_basename, True))
            treewidget = project.explorer.treewidget
            with qtbot.waitSignal(treewidget.sig_renamed) as blocker:
                treewidget.rename_file(old_path)
            assert blocker.args == [old_path, new_path]
            assert not osp.exists(old_path)
            with open(new_path, 'r') as fh:
                text = fh.read()
            assert text == "File Path:\n" + str(old_path).replace(os.sep, '/')


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
                    qtbot.mouseClick(
                        treewidget.viewport(), Qt.LeftButton, pos=pos)

                    if single_click:
                        assert full_path == file_explorer.label1.text()
                    else:
                        assert full_path != file_explorer.label1.text()

    # Test single click to open
    treewidget.set_conf('single_click_to_open', True)
    run_test_helper(single_click=True, initial_index=initial_index)

    # Test double click to open
    treewidget.set_conf('single_click_to_open', False)
    run_test_helper(single_click=False, initial_index=initial_index)


@pytest.mark.order(1)
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


@pytest.mark.order(1)
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


@pytest.mark.order(1)
def test_create_file_manager_actions(qtbot, file_explorer_associations,
                                     tmp_path):
    widget = file_explorer_associations.explorer.treewidget
    fpath = tmp_path / 'text.txt'
    fpath.write_text(u'hello!')
    fpath_2 = tmp_path / 'text.json'
    fpath_2.write_text(u'hello!')
    fpath_3 = tmp_path / 'text.md'
    fpath_3.write_text(u'hello!')

    # Single file with valid association
    actions = widget._create_file_associations_actions([str(fpath)])
    action_texts = [action.text().lower() for action in actions]
    assert any('app 1' in text for text in action_texts)
    assert any('default external application' in text for text in action_texts)

    # Two files with valid association
    actions = widget._create_file_associations_actions(
        [str(fpath), str(fpath_2)])
    action_texts = [action.text().lower() for action in actions]
    assert any('app 1' in text for text in action_texts)
    assert any('default external application' in text for text in action_texts)

    # Single file with no association
    actions = widget._create_file_associations_actions([str(fpath_3)])
    action_texts = [action.text().lower() for action in actions]
    assert not action_texts


@pytest.mark.order(1)
def test_clicked(qtbot, file_explorer_associations, tmp_path):
    widget = file_explorer_associations.explorer.treewidget
    some_dir = tmp_path / 'some_dir'
    some_dir.mkdir()
    fpath = some_dir / 'text.txt'
    fpath.write_text(u'hello!')
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


@pytest.mark.order(1)
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


@pytest.mark.order(1)
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


@pytest.mark.order(1)
def test_update_filters(file_explorer, qtbot):
    """
    Test that view is updated if the filter button is activated and
    filters are changed.

    This is a regression test for spyder-ide/spyder#14328
    """
    widget = file_explorer.explorer.treewidget

    # Assert explorer.py is present (in case we rename it)
    explorer_file = osp.join(osp.dirname(HERE), 'explorer.py')
    assert osp.isfile(explorer_file)

    # Assert explorer.py is in view before applying the new filters
    idx0 = widget.get_index(explorer_file)
    assert idx0.isValid()

    # Activate filters
    widget.filter_button.toggle()

    # Auxiliary function to interact with the filters dialog.
    def interact():
        dlg = file_explorer.explorer.findChild(QDialog)
        assert dlg

        # Change filters
        filters = dlg.findChild(QTextEdit)
        filters.setPlainText('*.png')

        # Apply settings
        button_box = dlg.findChild(QDialogButtonBox)
        button_box.button(QDialogButtonBox.Ok).clicked.emit()

    # Edit filters
    _ = create_timer(interact)
    file_explorer.explorer.edit_filter()

    # Wait for filters to be applied
    qtbot.wait(1000)

    # Assert explorer.py is not view.
    idx1 = widget.get_index(explorer_file)
    assert not idx1.isValid()


def test_go_to_current_file(file_explorer, tmp_path):
    """Test that 'Go to current file' navigates to the file's directory."""
    widget = file_explorer.explorer

    # Action should be disabled initially (no editor file set)
    assert not widget.go_to_dir_of_file_in_editor_action.isEnabled()

    # Create a file in a subdirectory
    subdir = tmp_path / "project" / "src"
    subdir.mkdir(parents=True)
    test_file = subdir / "main.py"
    test_file.write_text("pass")

    # Simulate the editor reporting its current file
    widget.set_current_editor_file(str(test_file))
    assert widget.go_to_dir_of_file_in_editor_action.isEnabled()

    # Trigger the action
    widget.go_to_current_file()
    assert widget.get_current_folder() == str(subdir)

    # Setting a file with a non-existent directory disables the action
    widget.set_current_editor_file("/nonexistent/path/file.py")
    assert not widget.go_to_dir_of_file_in_editor_action.isEnabled()

    # Setting None disables the action
    widget.set_current_editor_file(None)
    assert not widget.go_to_dir_of_file_in_editor_action.isEnabled()


@pytest.mark.parametrize(
    "path, expected",
    [
        ("\\\\server\\share\\dir", True),
        ("//server/share/dir", True),
        ("C:\\Users\\spyder", False),
        ("/home/spyder", False),
    ]
)
def test_is_unc_path(path, expected):
    """Test that UNC paths are detected."""
    assert is_unc_path(path) == expected


def test_is_network_path(tmp_path):
    """Test that network paths are detected."""
    assert is_network_path("\\\\server\\share\\dir")
    assert not is_network_path(str(tmp_path))


def test_refresh_action_visibility(file_explorer, tmp_path, monkeypatch):
    """
    Test that the refresh action is shown for UNC paths in the local tree.

    This is a regression test for spyder-ide/spyder#26432
    """
    widget = file_explorer.explorer
    unc_dir = tmp_path / "unc"
    local_dir = tmp_path / "local"
    unc_dir.mkdir()
    local_dir.mkdir()
    monkeypatch.setattr(
        main_widget, "is_unc_path", lambda path: path == str(unc_dir)
    )

    widget.chdir(str(unc_dir))
    assert widget.refresh_action.isVisible()

    # Navigating from the tree also updates it
    widget.treewidget.chdir(str(local_dir))
    assert not widget.refresh_action.isVisible()

    widget.treewidget.chdir(str(unc_dir))
    assert widget.refresh_action.isVisible()


def test_network_share_message(file_explorer, tmp_path, monkeypatch):
    """
    Test that a message about refreshing manually is shown for UNC paths in
    the local tree.
    """
    widget = file_explorer.explorer
    info_message = widget._info_message
    unc_dir = tmp_path / "unc"
    local_dir = tmp_path / "local"
    unc_dir.mkdir()
    local_dir.mkdir()
    monkeypatch.setattr(
        main_widget, "is_unc_path", lambda path: path == str(unc_dir)
    )

    widget.chdir(str(unc_dir))
    assert not info_message.isHidden()
    assert "Refresh" in info_message.text()

    widget.treewidget.chdir(str(local_dir))
    assert info_message.isHidden()

    widget.treewidget.chdir(str(unc_dir))
    assert not info_message.isHidden()

    # The message is not shown again if users decided to hide it
    widget.set_conf("show_network_share_message", False)
    widget.treewidget.chdir(str(local_dir))
    widget.treewidget.chdir(str(unc_dir))
    assert info_message.isHidden()
    widget.set_conf("show_network_share_message", True)


def test_refresh_unwatched_folder(unwatched_explorer, qtbot):
    """
    Test that the refresh action reloads folders Qt doesn't watch, including
    expanded subfolders.

    This is a regression test for spyder-ide/spyder#26432
    """
    widget, folder = unwatched_explorer
    treewidget = widget.treewidget
    subdir = folder / "subdir"
    treewidget.expand(treewidget.fsmodel.index(str(subdir)))
    qtbot.wait(500)

    # Changes done outside Spyder are not shown
    (folder / "new.txt").touch()
    (subdir / "new_in_subdir.txt").touch()
    qtbot.wait(1000)
    assert "new.txt" not in shown_names(treewidget)

    # They are after refreshing and the subfolder stays expanded
    widget.refresh_action.trigger()
    qtbot.waitUntil(lambda: "new.txt" in shown_names(treewidget))
    qtbot.waitUntil(
        lambda: "new_in_subdir.txt" in shown_names(treewidget, subdir)
    )
    assert treewidget.isExpanded(treewidget.fsmodel.index(str(subdir)))


def test_file_operations_refresh_unwatched_folder(
    unwatched_explorer, qtbot, mocker
):
    """
    Test that file operations done in Files are shown right away in folders
    Qt doesn't watch.

    This is a regression test for spyder-ide/spyder#26432
    """
    widget, folder = unwatched_explorer
    treewidget = widget.treewidget

    # Rename
    mocker.patch.object(
        QInputDialog, "getText", return_value=("renamed.txt", True)
    )
    treewidget.rename_file(str(folder / "file.txt"))
    qtbot.waitUntil(lambda: "renamed.txt" in shown_names(treewidget))
    assert "file.txt" not in shown_names(treewidget)

    # New folder
    mocker.patch.object(
        QInputDialog, "getText", return_value=("new_folder", True)
    )
    treewidget.new_folder(basedir=str(folder))
    qtbot.waitUntil(lambda: "new_folder" in shown_names(treewidget))

    # Move
    treewidget.move(
        fnames=[str(folder / "renamed.txt")], directory=str(folder / "subdir")
    )
    qtbot.waitUntil(lambda: "renamed.txt" not in shown_names(treewidget))


if __name__ == "__main__":
    pytest.main()
