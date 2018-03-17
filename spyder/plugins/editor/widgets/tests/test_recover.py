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
    dialog.exec_.assert_called()


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
