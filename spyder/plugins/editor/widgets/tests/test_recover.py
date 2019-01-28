# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""Tests for recover.py"""

# Standard library imports
import os.path as osp
import pytest
import shutil

# Third party imports
from qtpy.QtWidgets import QDialogButtonBox, QPushButton, QTableWidget

# Local imports
from spyder.py3compat import PY2
from spyder.plugins.editor.widgets.recover import (make_temporary_files,
                                                   RecoveryDialog)


@pytest.fixture
def recovery_env(tmpdir):
    """Create a dir with various autosave files and cleans up afterwards."""
    yield make_temporary_files(str(tmpdir))
    shutil.rmtree(str(tmpdir))


def test_recoverydialog_has_cancel_button(qtbot, tmpdir):
    """
    Test that RecoveryDialog has a Cancel button.

    Test that a RecoveryDialog has a button in a dialog button box and that
    this button cancels the dialog window.
    """
    dialog = RecoveryDialog(str(tmpdir), {})
    qtbot.addWidget(dialog)
    button = dialog.findChild(QDialogButtonBox).findChild(QPushButton)
    with qtbot.waitSignal(dialog.rejected):
        button.click()


def test_recoverydialog_table_labels(qtbot, recovery_env):
    """Test that table in RecoveryDialog has the correct labels."""
    orig_dir, autosave_dir, autosave_mapping = recovery_env
    dialog = RecoveryDialog(autosave_dir, autosave_mapping)
    table = dialog.findChild(QTableWidget)

    def text(i, j):
        return table.cellWidget(i, j).text()

    # ham.py: Both original and autosave files exist, mentioned in mapping
    assert osp.join(orig_dir, 'ham.py') in text(0, 0)
    assert osp.join(autosave_dir, 'ham.py') in text(0, 1)

    # spam.py: Only autosave file exists, mentioned in mapping
    assert osp.join(orig_dir, 'spam.py') in text(1, 0)
    assert 'no longer exists' in text(1, 0)
    assert osp.join(autosave_dir, 'spam.py') in text(1, 1)

    # eggs.py: Only original files exists, so cannot be recovered
    # It won't be in the table, so nothing to test

    # cheese.py: Only autosave file exists, not mentioned in mapping
    assert 'not recorded' in text(2, 0)
    assert osp.join(autosave_dir, 'cheese.py') in text(2, 1)

    # Thus, there should be three rows in total
    assert table.rowCount() == 3


def test_recoverydialog_exec_if_nonempty_when_empty(qtbot, tmpdir, mocker):
    """
    Test that exec_if_nonempty does nothing if autosave dir is empty.

    Specifically, test that it does not `exec_()` the dialog.
    """
    dialog = RecoveryDialog(str(tmpdir), {'ham': 'spam'})
    mocker.patch.object(dialog, 'exec_')
    assert dialog.exec_if_nonempty() == dialog.Accepted
    dialog.exec_.assert_not_called()


def test_recoverydialog_exec_if_nonempty_when_nonempty(
        qtbot, recovery_env, mocker):
    """Test that exec_if_nonempty executes dialog if autosave dir not empty."""
    orig_dir, autosave_dir, autosave_mapping = recovery_env
    dialog = RecoveryDialog(autosave_dir, autosave_mapping)
    mocker.patch.object(dialog, 'exec_', return_value='eggs')
    assert dialog.exec_if_nonempty() == 'eggs'
    assert dialog.exec_.called


def test_recoverydialog_exec_if_nonempty_when_no_autosave_dir(
        qtbot, recovery_env, mocker):
    """
    Test that exec_if_nonempty does nothing if autosave dir does not exist.

    Specifically, test that it does not `exec_()` the dialog.
    """
    orig_dir, autosave_dir, autosave_mapping = recovery_env
    shutil.rmtree(autosave_dir)
    dialog = RecoveryDialog(autosave_dir, autosave_mapping)
    mocker.patch.object(dialog, 'exec_')
    assert dialog.exec_if_nonempty() == dialog.Accepted
    dialog.exec_.assert_not_called()


def test_recoverydialog_restore_button(qtbot, recovery_env):
    """
    Test the `Restore` button in `RecoveryDialog`.

    Test that after pressing the 'Restore' button, the original file is
    replaced by the autosave file, the latter is removed, and the row in the
    grid is deactivated.
    """
    orig_dir, autosave_dir, autosave_mapping = recovery_env
    dialog = RecoveryDialog(autosave_dir, autosave_mapping)
    table = dialog.findChild(QTableWidget)
    button = table.cellWidget(0, 2).findChildren(QPushButton)[0]
    button.click()
    with open(osp.join(orig_dir, 'ham.py')) as f:
        assert f.read() == 'ham = "autosave"\n'
    assert not osp.isfile(osp.join(autosave_dir, 'ham.py'))
    for col in range(table.columnCount()):
        assert not table.cellWidget(0, col).isEnabled()


def test_recoverydialog_restore_when_original_does_not_exist(
        qtbot, recovery_env):
    """
    Test the `Restore` button when the original file does not exist.

    Test that after pressing the 'Restore' button, the autosave file is moved
    to the location of the original file and the row in the grid is
    deactivated.
    """
    orig_dir, autosave_dir, autosave_mapping = recovery_env
    dialog = RecoveryDialog(autosave_dir, autosave_mapping)
    table = dialog.findChild(QTableWidget)
    button = table.cellWidget(1, 2).findChildren(QPushButton)[0]
    button.click()
    with open(osp.join(orig_dir, 'spam.py')) as f:
        assert f.read() == 'spam = "autosave"\n'
    assert not osp.isfile(osp.join(autosave_dir, 'spam.py'))
    for col in range(table.columnCount()):
        assert not table.cellWidget(1, col).isEnabled()


def test_recoverydialog_restore_when_original_not_recorded(
        qtbot, recovery_env, mocker):
    """
    Test the `Restore` button when the original file name is not known.

    Test that after pressing the 'Restore' button, the autosave file is moved
    to a location specified by the user and the row in the grid is deactivated.
    """
    orig_dir, autosave_dir, autosave_mapping = recovery_env
    new_name = osp.join(orig_dir, 'monty.py')
    mocker.patch('spyder.plugins.editor.widgets.recover.getsavefilename',
                 return_value=(new_name, 'ignored'))
    dialog = RecoveryDialog(autosave_dir, autosave_mapping)
    table = dialog.findChild(QTableWidget)
    button = table.cellWidget(2, 2).findChildren(QPushButton)[0]
    button.click()
    with open(new_name) as f:
        assert f.read() == 'cheese = "autosave"\n'
    assert not osp.isfile(osp.join(autosave_dir, 'cheese.py'))
    for col in range(table.columnCount()):
        assert not table.cellWidget(2, col).isEnabled()


def test_recoverydialog_restore_fallback(qtbot, recovery_env, mocker):
    """
    Test fallback for when os.replace() fails when recovering a file.

    Test that after pressing the 'Restore' button, if os.replace() fails,
    the fallback to copy and delete kicks in and the restore succeeds.
    Regression test for issue #8631.
    """
    orig_dir, autosave_dir, autosave_mapping = recovery_env
    if not PY2:
        mocker.patch('spyder.plugins.editor.widgets.recover.os.replace',
                     side_effect=OSError)
    dialog = RecoveryDialog(autosave_dir, autosave_mapping)
    table = dialog.findChild(QTableWidget)
    button = table.cellWidget(0, 2).findChildren(QPushButton)[0]
    button.click()
    with open(osp.join(orig_dir, 'ham.py')) as f:
        assert f.read() == 'ham = "autosave"\n'
    assert not osp.isfile(osp.join(autosave_dir, 'ham.py'))
    for col in range(table.columnCount()):
        assert not table.cellWidget(0, col).isEnabled()


def test_recoverydialog_restore_when_error(qtbot, recovery_env, mocker):
    """
    Test that errors during a restore action are handled gracefully.

    Test that if an error arises when restoring a file, both the original and
    the autosave files are kept unchanged, a dialog is displayed, and the row
    in the grid is not deactivated.
    """
    orig_dir, autosave_dir, autosave_mapping = recovery_env
    if not PY2:
        mocker.patch('spyder.plugins.editor.widgets.recover.os.replace',
                     side_effect=OSError)
    mocker.patch('spyder.plugins.editor.widgets.recover.shutil.copy2',
                 side_effect=IOError)
    mock_QMessageBox = mocker.patch(
                'spyder.plugins.editor.widgets.recover.QMessageBox')
    dialog = RecoveryDialog(autosave_dir, autosave_mapping)
    table = dialog.findChild(QTableWidget)
    button = table.cellWidget(0, 2).findChildren(QPushButton)[0]
    button.click()
    with open(osp.join(orig_dir, 'ham.py')) as f:
        assert f.read() == 'ham = "original"\n'
    with open(osp.join(autosave_dir, 'ham.py')) as f:
        assert f.read() == 'ham = "autosave"\n'
    assert mock_QMessageBox.called
    for col in range(table.columnCount()):
        assert table.cellWidget(0, col).isEnabled()


def test_recoverydialog_accepted_after_all_restored(
        qtbot, recovery_env, mocker):
    """
    Test that the recovery dialog is accepted after all files are restored.

    Click all `Restore` buttons and test that the dialog is accepted
    afterwards, but not before.
    """
    orig_dir, autosave_dir, autosave_mapping = recovery_env
    new_name = osp.join(orig_dir, 'monty.py')
    mocker.patch('spyder.plugins.editor.widgets.recover.getsavefilename',
                 return_value=(new_name, 'ignored'))
    dialog = RecoveryDialog(autosave_dir, autosave_mapping)
    table = dialog.findChild(QTableWidget)
    with qtbot.assertNotEmitted(dialog.accepted):
        for row in range(table.rowCount() - 1):
            table.cellWidget(row, 2).findChildren(QPushButton)[0].click()
    with qtbot.waitSignal(dialog.accepted):
        row = table.rowCount() - 1
        table.cellWidget(row, 2).findChildren(QPushButton)[0].click()


def test_recoverydialog_discard_button(qtbot, recovery_env):
    """
    Test the `Discard` button in the recovery dialog.

    Test that after pressing the 'Discard' button, the autosave file is
    deleted, the original file unchanged, and the row in the grid is
    deactivated.
    """
    orig_dir, autosave_dir, autosave_mapping = recovery_env
    dialog = RecoveryDialog(autosave_dir, autosave_mapping)
    table = dialog.findChild(QTableWidget)
    button = table.cellWidget(0, 2).findChildren(QPushButton)[1]
    button.click()
    assert not osp.isfile(osp.join(autosave_dir, 'ham.py'))
    with open(osp.join(orig_dir, 'ham.py')) as f:
        assert f.read() == 'ham = "original"\n'
    for col in range(table.columnCount()):
        assert not table.cellWidget(0, col).isEnabled()


def test_recoverydialog_discard_when_error(qtbot, recovery_env, mocker):
    """
    Test that errors during a discard action are handled gracefully.

    Test that if an error arises when discarding a file, both the original and
    the autosave files are kept unchanged, a dialog is displayed, and the row
    in the grid is not deactivated.
    """
    orig_dir, autosave_dir, autosave_mapping = recovery_env
    mocker.patch('spyder.plugins.editor.widgets.recover.os.remove',
                 side_effect=OSError)
    mock_QMessageBox = mocker.patch(
                'spyder.plugins.editor.widgets.recover.QMessageBox')
    dialog = RecoveryDialog(autosave_dir, autosave_mapping)
    table = dialog.findChild(QTableWidget)
    button = table.cellWidget(0, 2).findChildren(QPushButton)[1]
    button.click()
    with open(osp.join(orig_dir, 'ham.py')) as f:
        assert f.read() == 'ham = "original"\n'
    with open(osp.join(autosave_dir, 'ham.py')) as f:
        assert f.read() == 'ham = "autosave"\n'
    assert mock_QMessageBox.called
    for col in range(table.columnCount()):
        assert table.cellWidget(0, col).isEnabled()


def test_recoverydialog_open_button(qtbot, recovery_env):
    """
    Test the `Open` button in the recovery dialog.

    Test that after pressing the 'Open' button, `files_to_open` contains
    the autosave and the original file, and the row in the grid is
    deactivated.
    """
    orig_dir, autosave_dir, autosave_mapping = recovery_env
    dialog = RecoveryDialog(autosave_dir, autosave_mapping)
    table = dialog.findChild(QTableWidget)
    button = table.cellWidget(0, 2).findChildren(QPushButton)[2]
    button.click()
    assert dialog.files_to_open == [osp.join(orig_dir, 'ham.py'),
                                    osp.join(autosave_dir, 'ham.py')]
    for col in range(table.columnCount()):
        assert not table.cellWidget(0, col).isEnabled()


def test_recoverydialog_open_when_no_original(qtbot, recovery_env):
    """
    Test the `Open` button when the original file is not known.

    Test that when the user requests to open an autosave file for which the
    original file is not known, `files_to_open` contains only the autosave
    file.
    """
    orig_dir, autosave_dir, autosave_mapping = recovery_env
    dialog = RecoveryDialog(autosave_dir, autosave_mapping)
    table = dialog.findChild(QTableWidget)
    button = table.cellWidget(2, 2).findChildren(QPushButton)[2]
    button.click()
    assert dialog.files_to_open == [osp.join(autosave_dir, 'cheese.py')]
    for col in range(table.columnCount()):
        assert not table.cellWidget(2, col).isEnabled()
