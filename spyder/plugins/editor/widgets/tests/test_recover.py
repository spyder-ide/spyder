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
from qtpy.QtWidgets import QDialogButtonBox, QGridLayout, QPushButton

# Local imports
from spyder.py3compat import PY3
from spyder.plugins.editor.widgets.recover import (make_temporary_files,
                                                   RecoveryDialog)


@pytest.fixture
def recovery_env(tmpdir):
    """Creates a dir with various autosave files and cleans up afterwards."""
    yield make_temporary_files(str(tmpdir))
    shutil.rmtree(str(tmpdir))


def test_recoverydialog_has_cancel_button(qtbot, tmpdir):
    """
    Test that RecoveryDialog has a button in a dialog button box and that
    this button cancels the dialog window.
    """
    dialog = RecoveryDialog(str(tmpdir), {})
    qtbot.addWidget(dialog)
    button = dialog.findChild(QDialogButtonBox).findChild(QPushButton)
    with qtbot.waitSignal(dialog.rejected):
        button.click()


def test_recoverydialog_grid_labels(qtbot, recovery_env):
    """Test that grid in RecoveryDialog has the correct labels ."""
    orig_dir, autosave_dir, autosave_mapping = recovery_env
    dialog = RecoveryDialog(autosave_dir, autosave_mapping)
    grid = dialog.findChild(QGridLayout)

    def text(i, j):
        return grid.itemAtPosition(i, j).widget().text()

    # ham.py: Both original and autosave files exist, mentioned in mapping
    assert osp.join(orig_dir, 'ham.py') in text(1, 0)
    assert osp.join(autosave_dir, 'ham.py') in text(1, 1)

    # spam.py: Only autosave file exists, mentioned in mapping
    assert osp.join(orig_dir, 'spam.py') in text(2, 0)
    assert 'no longer exists' in text(2, 0)
    assert osp.join(autosave_dir, 'spam.py') in text(2, 1)

    # eggs.py: Only original files exists, so cannot be recovered

    # cheese.py: Only autosave file exists, not mentioned in mapping
    assert 'not recorded' in text(3, 0)
    assert osp.join(autosave_dir, 'cheese.py') in text(3, 1)


def test_recoverydialog_exec_if_nonempty_when_empty(qtbot, tmpdir, mocker):
    """
    Test that exec_if_nonempty does not execute the dialog if autosave dir
    is empty.
    """
    dialog = RecoveryDialog(str(tmpdir), {'ham': 'spam'})
    mocker.patch.object(dialog, 'exec_')
    assert dialog.exec_if_nonempty() == dialog.Accepted
    dialog.exec_.assert_not_called()


def test_recoverydialog_exec_if_nonempty_when_nonempty(
        qtbot, recovery_env, mocker):
    """
    Test that exec_if_nonempty does not execute the dialog if autosave dir
    is empty.
    """
    orig_dir, autosave_dir, autosave_mapping = recovery_env
    dialog = RecoveryDialog(autosave_dir, autosave_mapping)
    mocker.patch.object(dialog, 'exec_', return_value='eggs')
    assert dialog.exec_if_nonempty() == 'eggs'
    assert dialog.exec_.called


def test_recoverydialog_exec_if_nonempty_when_no_autosave_dir(
        qtbot, recovery_env, mocker):
    """
    Test that exec_if_nonempty does not execute the dialog if the autosave
    dir does not exist.
    """
    orig_dir, autosave_dir, autosave_mapping = recovery_env
    shutil.rmtree(autosave_dir)
    dialog = RecoveryDialog(autosave_dir, autosave_mapping)
    mocker.patch.object(dialog, 'exec_')
    assert dialog.exec_if_nonempty() == dialog.Accepted
    dialog.exec_.assert_not_called()


def test_recoverydialog_restore_button(qtbot, recovery_env):
    """
    Test that after pressing the 'Restore' button, the original file is
    replaced by the autosave file, the latter is removed, and the row in the
    grid is deactivated.
    """
    orig_dir, autosave_dir, autosave_mapping = recovery_env
    dialog = RecoveryDialog(autosave_dir, autosave_mapping)
    grid = dialog.findChild(QGridLayout)
    button = grid.itemAtPosition(1, 2).widget()
    button.click()
    with open(osp.join(orig_dir, 'ham.py')) as f:
        assert f.read() == 'ham = "autosave"\n'
    assert not osp.isfile(osp.join(autosave_dir, 'ham.py'))
    for col in range(grid.columnCount()):
        assert not grid.itemAtPosition(1, col).widget().isEnabled()


def test_recoverydialog_restore_when_original_does_not_exist(
        qtbot, recovery_env):
    """
    Test that restoring an autosave file works when the original file no
    longer rexists.
    """
    orig_dir, autosave_dir, autosave_mapping = recovery_env
    dialog = RecoveryDialog(autosave_dir, autosave_mapping)
    grid = dialog.findChild(QGridLayout)
    button = grid.itemAtPosition(2, 2).widget()
    button.click()
    with open(osp.join(orig_dir, 'spam.py')) as f:
        assert f.read() == 'spam = "autosave"\n'
    assert not osp.isfile(osp.join(autosave_dir, 'spam.py'))
    for col in range(grid.columnCount()):
        assert not grid.itemAtPosition(2, col).widget().isEnabled()


def test_recoverydialog_restore_when_original_not_recorded(
        qtbot, recovery_env, mocker):
    """
    Test that restoring an autosave file works when the original file no
    longer rexists.
    """
    orig_dir, autosave_dir, autosave_mapping = recovery_env
    new_name = osp.join(orig_dir, 'monty.py')
    mocker.patch('spyder.plugins.editor.widgets.recover.getsavefilename',
                 return_value=(new_name, 'ignored'))
    dialog = RecoveryDialog(autosave_dir, autosave_mapping)
    grid = dialog.findChild(QGridLayout)
    button = grid.itemAtPosition(3, 2).widget()
    button.click()
    with open(new_name) as f:
        assert f.read() == 'cheese = "autosave"\n'
    assert not osp.isfile(osp.join(autosave_dir, 'cheese.py'))
    for col in range(grid.columnCount()):
        assert not grid.itemAtPosition(3, col).widget().isEnabled()


def test_recoverydialog_restore_when_error(qtbot, recovery_env, mocker):
    """
    Test that if an error arises when restoring a file, both the original and
    the autosave files are kept unchanged, a dialog is displayed, and the row
    in the grid is not deactivated.
    """
    orig_dir, autosave_dir, autosave_mapping = recovery_env
    if PY3:
        mocker.patch('spyder.plugins.editor.widgets.recover.os.replace',
                     side_effect=OSError)
    else:
        mocker.patch('spyder.plugins.editor.widgets.recover.shutil.copy2',
                     side_effect=IOError)
    mock_QMessageBox = mocker.patch(
                'spyder.plugins.editor.widgets.recover.QMessageBox')
    dialog = RecoveryDialog(autosave_dir, autosave_mapping)
    grid = dialog.findChild(QGridLayout)
    button = grid.itemAtPosition(1, 2).widget()
    button.click()
    with open(osp.join(orig_dir, 'ham.py')) as f:
        assert f.read() == 'ham = "original"\n'
    with open(osp.join(autosave_dir, 'ham.py')) as f:
        assert f.read() == 'ham = "autosave"\n'
    mock_QMessageBox.assert_called_once()
    for col in range(grid.columnCount()):
        assert grid.itemAtPosition(1, col).widget().isEnabled()


def test_recoverydialog_accepted_after_all_restored(
        qtbot, recovery_env, mocker):
    """
    Test that the recovery dialog is accepted after all Restore buttons are
    clicked, but not before.
    """
    orig_dir, autosave_dir, autosave_mapping = recovery_env
    new_name = osp.join(orig_dir, 'monty.py')
    mocker.patch('spyder.plugins.editor.widgets.recover.getsavefilename',
                 return_value=(new_name, 'ignored'))
    dialog = RecoveryDialog(autosave_dir, autosave_mapping)
    grid = dialog.findChild(QGridLayout)
    with qtbot.assertNotEmitted(dialog.accepted):
        for row in range(1, grid.rowCount() - 1):
            grid.itemAtPosition(row, 2).widget().click()
    with qtbot.waitSignal(dialog.accepted):
        row = grid.rowCount() - 1
        grid.itemAtPosition(row, 2).widget().click()


def test_recoverydialog_discard_button(qtbot, recovery_env):
    """
    Test that after pressing the 'Discard' button, the autosave file is
    deleted, the original file unchanged, and the row in the grid is
    deactivated.
    """
    orig_dir, autosave_dir, autosave_mapping = recovery_env
    dialog = RecoveryDialog(autosave_dir, autosave_mapping)
    grid = dialog.findChild(QGridLayout)
    button = grid.itemAtPosition(1, 3).widget()
    button.click()
    assert not osp.isfile(osp.join(autosave_dir, 'ham.py'))
    with open(osp.join(orig_dir, 'ham.py')) as f:
        assert f.read() == 'ham = "original"\n'
    for col in range(grid.columnCount()):
        assert not grid.itemAtPosition(1, col).widget().isEnabled()


def test_recoverydialog_discard_when_error(qtbot, recovery_env, mocker):
    """
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
    grid = dialog.findChild(QGridLayout)
    button = grid.itemAtPosition(1, 3).widget()
    button.click()
    with open(osp.join(orig_dir, 'ham.py')) as f:
        assert f.read() == 'ham = "original"\n'
    with open(osp.join(autosave_dir, 'ham.py')) as f:
        assert f.read() == 'ham = "autosave"\n'
    mock_QMessageBox.assert_called_once()
    for col in range(grid.columnCount()):
        assert grid.itemAtPosition(1, col).widget().isEnabled()


def test_recoverydialog_open_button(qtbot, recovery_env):
    """
    Test that after pressing the 'Open' button, `files_to_open` contains
    the autosave and the original file, and the row in the grid is
    deactivated.
    """
    orig_dir, autosave_dir, autosave_mapping = recovery_env
    dialog = RecoveryDialog(autosave_dir, autosave_mapping)
    grid = dialog.findChild(QGridLayout)
    button = grid.itemAtPosition(1, 4).widget()
    button.click()
    assert dialog.files_to_open == [osp.join(orig_dir, 'ham.py'),
                                    osp.join(autosave_dir, 'ham.py')]
    for col in range(grid.columnCount()):
        assert not grid.itemAtPosition(1, col).widget().isEnabled()


def test_recoverydialog_open_when_no_original(qtbot, recovery_env):
    """
    Test that when the user request to open an autosave file for which the
    original file is not known, `files_to_open` contains only the autosave
    file.
    """
    orig_dir, autosave_dir, autosave_mapping = recovery_env
    dialog = RecoveryDialog(autosave_dir, autosave_mapping)
    grid = dialog.findChild(QGridLayout)
    button = grid.itemAtPosition(3, 4).widget()
    button.click()
    assert dialog.files_to_open == [osp.join(autosave_dir, 'cheese.py')]
    for col in range(grid.columnCount()):
        assert not grid.itemAtPosition(3, col).widget().isEnabled()
