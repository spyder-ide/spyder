# -----------------------------------------------------------------------------
# Copyright (c) 2009- Spyder Project Contributors
#
# Distributed under the terms of the MIT License
# (see spyder/__init__.py for details)
# -----------------------------------------------------------------------------

"""Files and Remote client integration tests."""

# Standard library imports
import os.path as osp

# Third party imports
import pytest
from qtpy.QtCore import Qt
from qtpy.QtWidgets import QApplication, QInputDialog, QMessageBox

# Local imports
from spyder.plugins.remoteclient.tests.conftest import (
    await_future,
    mark_remote_test,
)


def get_filenames_from_ui(treewidget):
    fnames = []
    treewidget.view.selectAll()
    indexes = treewidget._get_selected_indexes()

    for index in indexes:
        source_index = treewidget.proxy_model.mapToSource(index)
        data_index = treewidget.model.index(source_index.row(), 0)
        data = treewidget.model.data(data_index, Qt.UserRole + 1)
        fnames.append(osp.basename(data["name"]))

    return set(fnames)


@mark_remote_test
def test_setup(remote_explorer, remote_client_id):
    treewidget = remote_explorer.remote_treewidget
    assert remote_explorer.stackwidget.currentWidget() == treewidget
    assert treewidget.server_id == remote_client_id


@mark_remote_test
def test_delete(remote_explorer, remote_client_id, monkeypatch, qtbot):
    treewidget = remote_explorer.remote_treewidget
    dirname = "test-delete-files"

    # Create a new directory with the UI and move to it
    monkeypatch.setattr(QInputDialog, "getText", lambda *args: (dirname, True))

    with qtbot.waitSignal(treewidget.sig_stop_spinner_requested):
        treewidget.new_directory_action.triggered.emit()

    treewidget.chdir(dirname, server_id=remote_client_id)
    qtbot.waitUntil(lambda: treewidget.model.rowCount() == 0)

    # Create a couple of files with the UI
    for fname in ["a.txt", "b.txt"]:
        monkeypatch.setattr(
            QInputDialog, "getText", lambda *args: (fname, True)
        )

        with qtbot.waitSignal(treewidget.sig_stop_spinner_requested):
            treewidget.new_file_action.triggered.emit()

    qtbot.waitUntil(lambda: treewidget.model.rowCount() == 2)

    # Select and decline to delete those files
    treewidget.view.selectAll()

    for answer in [QMessageBox.No, QMessageBox.Cancel]:
        monkeypatch.setattr(QMessageBox, "warning", lambda *args: answer)

        with qtbot.waitSignal(treewidget.sig_stop_spinner_requested):
            treewidget.delete_action.triggered.emit()

    assert treewidget.model.rowCount() == 2

    # Delete files
    monkeypatch.setattr(
        QMessageBox, "warning", lambda *args: QMessageBox.YesToAll
    )

    with qtbot.waitSignal(treewidget.sig_stop_spinner_requested):
        treewidget.delete_action.triggered.emit()

    qtbot.waitUntil(lambda: treewidget.model.rowCount() == 0)

    # Delete remote test directory
    await_future(
        treewidget._do_remote_delete(f"/home/ubuntu/{dirname}", is_file=False),
        timeout=2,
    )


@mark_remote_test
def test_upload(remote_explorer, remote_client_id, mocker, monkeypatch, qtbot):
    treewidget = remote_explorer.remote_treewidget
    dirname = "test-upload-files"
    files_to_upload = [
        __file__,
        osp.join(osp.dirname(__file__), "test_explorer.py"),
    ]

    # Create a new directory with the UI and move to it
    monkeypatch.setattr(QInputDialog, "getText", lambda *args: (dirname, True))

    with qtbot.waitSignal(treewidget.sig_stop_spinner_requested):
        treewidget.new_directory_action.triggered.emit()

    treewidget.chdir(dirname, server_id=remote_client_id)
    qtbot.waitUntil(lambda: treewidget.model.rowCount() == 0)

    # Upload some files
    mocker.patch(
        "spyder.plugins.explorer.widgets.remote_explorer.getopenfilenames",
        return_value=(files_to_upload, "ignored"),
    )

    with qtbot.waitSignal(treewidget.sig_stop_spinner_requested):
        treewidget.upload_file_action.triggered.emit()

    qtbot.waitUntil(lambda: treewidget.model.rowCount() == 2)

    # Check uploaded file names
    assert get_filenames_from_ui(treewidget) == {
        "test_explorer.py",
        "test_remote_explorer.py",
    }

    # Try to upload the same files again and test we checked for existence
    mocker.patch.object(QMessageBox, "warning", return_value=QMessageBox.No)

    with qtbot.waitSignal(treewidget.sig_stop_spinner_requested):
        treewidget.upload_file_action.triggered.emit()

    assert len(QMessageBox.warning.mock_calls) == 2

    # Delete remote test directory
    await_future(
        treewidget._do_remote_delete(f"/home/ubuntu/{dirname}", is_file=False),
        timeout=2,
    )


@mark_remote_test
def test_download(
    remote_explorer, remote_client_id, mocker, monkeypatch, qtbot, tmp_path
):
    treewidget = remote_explorer.remote_treewidget
    dirname = "test-download-files"
    files_to_download = ["a.txt", "b.txt"]

    # Create a new directory with the UI and move to it
    monkeypatch.setattr(QInputDialog, "getText", lambda *args: (dirname, True))

    with qtbot.waitSignal(treewidget.sig_stop_spinner_requested):
        treewidget.new_directory_action.triggered.emit()

    treewidget.chdir(dirname, server_id=remote_client_id)
    qtbot.waitUntil(lambda: treewidget.model.rowCount() == 0)

    # Create remote files to download
    for fname in files_to_download:
        monkeypatch.setattr(
            QInputDialog, "getText", lambda *args: (fname, True)
        )

        with qtbot.waitSignal(treewidget.sig_stop_spinner_requested):
            treewidget.new_file_action.triggered.emit()

    qtbot.waitUntil(lambda: treewidget.model.rowCount() == 2)

    # Download files
    treewidget.view.selectAll()

    mocker.patch(
        "spyder.plugins.explorer.widgets.remote_explorer.getexistingdirectory",
        return_value=str(tmp_path),
    )

    with qtbot.waitSignal(treewidget.sig_stop_spinner_requested):
        treewidget.download_action.triggered.emit()

    # Check that downloaded files exist locally
    for fname in files_to_download:
        assert (tmp_path / fname).exists()

    # Try to download the same files again and test we checked for existence
    mocker.patch.object(QMessageBox, "warning", return_value=QMessageBox.No)

    with qtbot.waitSignal(treewidget.sig_stop_spinner_requested):
        treewidget.download_action.triggered.emit()

    assert len(QMessageBox.warning.mock_calls) == 2

    # Delete remote test directory
    await_future(
        treewidget._do_remote_delete(f"/home/ubuntu/{dirname}", is_file=False),
        timeout=2,
    )


@mark_remote_test
def test_copy_paste(
    remote_explorer, remote_client_id, mocker, monkeypatch, qtbot
):
    treewidget = remote_explorer.remote_treewidget
    copy_paste_dirs = ["test-copy-files", "test-paste-files"]
    copy_paste_files = ["a.txt", "b.txt"]

    # Create directories with the UI and move to it
    for dirname in copy_paste_dirs:
        monkeypatch.setattr(
            QInputDialog, "getText", lambda *args: (dirname, True)
        )

        with qtbot.waitSignal(treewidget.sig_stop_spinner_requested):
            treewidget.new_directory_action.triggered.emit()

    # Move to copy dir
    treewidget.chdir(copy_paste_dirs[0], server_id=remote_client_id)
    qtbot.waitUntil(lambda: treewidget.model.rowCount() == 0)

    # Create remote files to copy
    for fname in copy_paste_files:
        monkeypatch.setattr(
            QInputDialog, "getText", lambda *args: (fname, True)
        )

        with qtbot.waitSignal(treewidget.sig_stop_spinner_requested):
            treewidget.new_file_action.triggered.emit()

    qtbot.waitUntil(lambda: treewidget.model.rowCount() == 2)

    # Copy files
    treewidget.view.selectAll()
    treewidget.copy_action.triggered.emit()

    # Move to paste directory
    treewidget.go_to_previous_directory()
    qtbot.waitUntil(lambda: treewidget.model.rowCount() > 2)

    treewidget.chdir(copy_paste_dirs[1], server_id=remote_client_id)
    qtbot.waitUntil(lambda: treewidget.model.rowCount() == 0)

    # Paste files
    with qtbot.waitSignal(treewidget.sig_stop_spinner_requested):
        treewidget.paste_action.triggered.emit()

    qtbot.waitUntil(lambda: treewidget.model.rowCount() == 2)

    # Check filenames
    assert get_filenames_from_ui(treewidget) == set(copy_paste_files)

    # Try to paste the same files again and test we checked for existence
    mocker.patch.object(QMessageBox, "warning", return_value=QMessageBox.No)

    with qtbot.waitSignal(treewidget.sig_stop_spinner_requested):
        treewidget.paste_action.triggered.emit()

    assert len(QMessageBox.warning.mock_calls) == 2

    # Delete remote test directories
    for dirname in copy_paste_dirs:
        await_future(
            treewidget._do_remote_delete(
                f"/home/ubuntu/{dirname}", is_file=False
            ),
            timeout=2,
        )


@mark_remote_test
def test_copy_paths(
    remote_explorer, remote_client_id, monkeypatch, qtbot, tmp_path
):
    treewidget = remote_explorer.remote_treewidget
    dirname = "test-cppy-paths"
    files_to_copy_paths = ["a.txt", "b.txt"]

    # Create a new directory with the UI and move to it
    monkeypatch.setattr(QInputDialog, "getText", lambda *args: (dirname, True))

    with qtbot.waitSignal(treewidget.sig_stop_spinner_requested):
        treewidget.new_directory_action.triggered.emit()

    treewidget.chdir(f"/home/ubuntu/{dirname}", server_id=remote_client_id)
    qtbot.waitUntil(lambda: treewidget.model.rowCount() == 0)

    # Create remote files to copy tjeir paths
    for fname in files_to_copy_paths:
        monkeypatch.setattr(
            QInputDialog, "getText", lambda *args: (fname, True)
        )

        with qtbot.waitSignal(treewidget.sig_stop_spinner_requested):
            treewidget.new_file_action.triggered.emit()

    qtbot.waitUntil(lambda: treewidget.model.rowCount() == 2)

    # This is necessary to set the current index for the view and simulate what
    # users actually need to do to select some files to copy their paths
    treewidget.view.selectAll()
    treewidget.view.setCurrentIndex(treewidget._get_selected_indexes()[0])

    # Copy file paths
    treewidget.view.selectAll()
    treewidget.copy_path_action.triggered.emit()

    # Check copied paths
    cb = QApplication.clipboard()
    cb_output = cb.text(mode=cb.Clipboard)
    path_list = [path.strip(',"') for path in cb_output.split(" ")]
    expected_path_list = [
        f"/home/ubuntu/{dirname}/{fname}" for fname in files_to_copy_paths
    ]
    assert set(path_list) == set(expected_path_list)

    # Delete remote test directory
    await_future(
        treewidget._do_remote_delete(f"/home/ubuntu/{dirname}", is_file=False),
        timeout=2,
    )


@mark_remote_test
def test_new_files_and_directories(
    remote_explorer, remote_client_id, mocker, monkeypatch, qtbot
):
    treewidget = remote_explorer.remote_treewidget
    dirname = "test-new-files"
    files_to_create = ["a.txt", "b.py"]
    directories_to_create = ["foo", "bar"]

    # Create a new directory with the UI and move to it
    monkeypatch.setattr(QInputDialog, "getText", lambda *args: (dirname, True))

    with qtbot.waitSignal(treewidget.sig_stop_spinner_requested):
        treewidget.new_directory_action.triggered.emit()

    treewidget.chdir(dirname, server_id=remote_client_id)
    qtbot.waitUntil(lambda: treewidget.model.rowCount() == 0)

    # Create new files
    for fname in files_to_create:
        monkeypatch.setattr(
            QInputDialog, "getText", lambda *args: (fname, True)
        )

        action = (
            treewidget.new_module_action
            if fname.endswith(".py")
            else treewidget.new_file_action
        )
        with qtbot.waitSignal(treewidget.sig_stop_spinner_requested):
            action.triggered.emit()

    qtbot.waitUntil(lambda: treewidget.model.rowCount() == 2)

    # Try to create the same files again and test we checked for existence
    mocker.patch.object(QMessageBox, "warning", return_value=QMessageBox.No)

    for action in [treewidget.new_file_action, treewidget.new_module_action]:
        with qtbot.waitSignal(treewidget.sig_stop_spinner_requested):
            action.triggered.emit()

    assert len(QMessageBox.warning.mock_calls) == 2

    # Create new directories
    for dname in directories_to_create:
        monkeypatch.setattr(
            QInputDialog, "getText", lambda *args: (dname, True)
        )

        action = (
            treewidget.new_directory_action
            if dname == "foo"
            else treewidget.new_package_action
        )
        with qtbot.waitSignal(treewidget.sig_stop_spinner_requested):
            action.triggered.emit()

    qtbot.waitUntil(lambda: treewidget.model.rowCount() == 4)

    # Try to create one of the dirs again and test we checked for existence
    monkeypatch.setattr(QInputDialog, "getText", lambda *args: ("foo", True))
    mocker.patch.object(QMessageBox, "critical", return_value=QMessageBox.Ok)

    for action in [
        treewidget.new_directory_action,
        treewidget.new_package_action,
    ]:
        with qtbot.waitSignal(treewidget.sig_stop_spinner_requested):
            action.triggered.emit()

    assert len(QMessageBox.critical.mock_calls) == 2

    # Check "foo" directory is still empty. That checks that trying to create
    # a Python package with that name doesn't add an __init__.py file to it.
    treewidget.chdir(f"/home/ubuntu/{dirname}/foo", server_id=remote_client_id)
    qtbot.waitUntil(lambda: treewidget.model.rowCount() == 0)

    treewidget.chdir(f"/home/ubuntu/{dirname}/bar", server_id=remote_client_id)
    qtbot.waitUntil(lambda: treewidget.model.rowCount() == 1)

    assert get_filenames_from_ui(treewidget) == {"__init__.py"}

    # Delete remote test directory
    await_future(
        treewidget._do_remote_delete(f"/home/ubuntu/{dirname}", is_file=False),
        timeout=2,
    )


@mark_remote_test
def test_permission_errors(
    remote_explorer, remote_client_id, mocker, monkeypatch, qtbot, tmp_path
):
    treewidget = remote_explorer.remote_treewidget

    # This directory is created and populated by the Docker test files
    dirname = "test-errors"

    # Move to directory with the UI
    treewidget.chdir(dirname, server_id=remote_client_id)
    qtbot.waitUntil(lambda: treewidget.model.rowCount() == 3)

    # Get indexes to select them
    treewidget.view.selectAll()
    all_indexes = treewidget._get_selected_indexes()

    # Try to download directory that can't be read
    mocker.patch.object(QMessageBox, "critical", return_value=QMessageBox.Ok)
    mocker.patch(
        "spyder.plugins.explorer.widgets.remote_explorer.getexistingdirectory",
        return_value=str(tmp_path),
    )

    treewidget.view.setCurrentIndex(all_indexes[0])

    with qtbot.waitSignal(treewidget.sig_stop_spinner_requested):
        treewidget.download_action.triggered.emit()

    assert len(QMessageBox.critical.mock_calls) == 1

    # Try to download file that can't be read
    treewidget.view.setCurrentIndex(all_indexes[2])

    with qtbot.waitSignal(treewidget.sig_stop_spinner_requested):
        treewidget.download_action.triggered.emit()

    assert len(QMessageBox.critical.mock_calls) == 2

    # Move to directory that doesn't have write permissions
    treewidget.chdir(
        f"/home/ubuntu/{dirname}/cant-write-dir", server_id=remote_client_id
    )
    qtbot.waitUntil(lambda: treewidget.model.rowCount() == 0)

    # Try to upload file
    mocker.patch(
        "spyder.plugins.explorer.widgets.remote_explorer.getopenfilenames",
        return_value=([__file__], "ignored"),
    )

    with qtbot.waitSignal(treewidget.sig_stop_spinner_requested):
        treewidget.upload_file_action.triggered.emit()

    assert len(QMessageBox.critical.mock_calls) == 3
    assert treewidget.model.rowCount() == 0

    # Try to create new files
    for fname, action in [
        ("a.txt", treewidget.new_file_action),
        ("b.py", treewidget.new_module_action)
    ]:
        monkeypatch.setattr(
            QInputDialog, "getText", lambda *args: (fname, True)
        )
        with qtbot.waitSignal(treewidget.sig_stop_spinner_requested):
            action.triggered.emit()

    assert len(QMessageBox.critical.mock_calls) == 5
    assert treewidget.model.rowCount() == 0

    # Try to create new directories
    for dname, action in [
        ("foo", treewidget.new_directory_action),
        ("bar", treewidget.new_package_action)
    ]:
        monkeypatch.setattr(
            QInputDialog, "getText", lambda *args: (dname, True)
        )
        with qtbot.waitSignal(treewidget.sig_stop_spinner_requested):
            action.triggered.emit()

    assert len(QMessageBox.critical.mock_calls) == 7
    assert treewidget.model.rowCount() == 0


if __name__ == "__main__":
    pytest.main()
