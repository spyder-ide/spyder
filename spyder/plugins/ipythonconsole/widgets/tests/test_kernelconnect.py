# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright © Spyder Project Contributors
#
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)
# -----------------------------------------------------------------------------

"""Tests for the Existing Kernel Connection widget."""

# Third party imports
import sys
import os
import pytest
from qtpy.QtCore import Qt
from qtpy.QtWidgets import QDialogButtonBox
import time

# Local imports
from spyder.plugins.ipythonconsole.widgets.kernelconnect import (
    KernelConnectionDialog
)
from spyder.config.main import CONF


# =============================================================================
# Fixtures
# =============================================================================
@pytest.fixture
def connection_dialog_factory(request):
    """Set up kernel connection dialog."""
    class DialogFactory(object):
        def get(self):
            dialog = KernelConnectionDialog()
            request.addfinalizer(dialog.close)
            return dialog

    def teardown():
        """Clear existing-kernel config and keyring passwords"""
        CONF.remove_section("existing-kernel")

        try:
            import keyring
            keyring.set_password("existing_kernel",
                                 "ssh_key_passphrase", "")
            keyring.set_password("existing_kernel",
                                 "ssh_password", "")
        except Exception:
            pass

    request.addfinalizer(teardown)
    return DialogFactory()


# =============================================================================
# Tests
# =============================================================================
def test_kernel_connection_dialog_remember_input_ssh_passphrase(
        qtbot, connection_dialog_factory):
    """Test that the dialog remember user's kernel connection
       settings and ssh key passphrase when the user checks the
       save checkbox."""

    dlg = connection_dialog_factory.get()

    cf_path = "test_cf_path"
    un = "test_username"
    hn = "test_hostname"
    pn = 123
    kf = "test_kf"
    kfp = "test_kfp"

    # fill out cf path
    dlg.cf.clear()
    qtbot.keyClicks(dlg.cf, cf_path)
    # check the remote kernel box
    dlg.rm_group.setChecked(True)
    # fill out hostname
    dlg.hn.clear()
    qtbot.keyClicks(dlg.hn, hn)
    # fill out port
    dlg.pn.clear()
    qtbot.keyClicks(dlg.pn, str(pn))
    # fill out username
    dlg.un.clear()
    qtbot.keyClicks(dlg.un, un)

    # select ssh keyfile radio
    dlg.kf_radio.setChecked(True)
    assert dlg.kf.isEnabled()

    # fill out ssh keyfile
    dlg.kf.clear()
    qtbot.keyClicks(dlg.kf, kf)

    # fill out passphrase
    dlg.kfp.clear()
    qtbot.keyClicks(dlg.kfp, kfp)

    # check save connection settings
    dlg.save_layout.setChecked(True)

    # Press ok and save connection settings
    qtbot.mouseClick(dlg.accept_btns.button(QDialogButtonBox.Ok),
                     Qt.LeftButton)

    # create new dialog and check fields
    new_dlg = connection_dialog_factory.get()
    assert new_dlg.cf.text() == cf_path
    assert new_dlg.rm_group.isChecked()
    assert new_dlg.hn.text() == hn
    assert new_dlg.un.text() == un
    assert new_dlg.pn.text() == str(pn)
    assert new_dlg.kf.text() == kf
    if (not sys.platform.startswith('linux') or
            not os.environ.get('CI') is not None):
        assert new_dlg.kfp.text() == kfp


def test_kernel_connection_dialog_doesnt_remember_input_ssh_passphrase(
        qtbot, connection_dialog_factory):
    """Test that the dialog doesn't remember user's kernel
       connection settings and ssh key passphrase when the user doesn't
       check the save checkbox."""

    dlg = connection_dialog_factory.get()

    cf_path = "test_cf_path"
    un = "test_username"
    hn = "test_hostname"
    pn = 123
    kf = "test_kf"
    kfp = "test_kfp"

    # fill out cf path
    dlg.cf.clear()
    qtbot.keyClicks(dlg.cf, cf_path)
    # check the remote kernel box
    dlg.rm_group.setChecked(True)
    # fill out hostname
    dlg.hn.clear()
    qtbot.keyClicks(dlg.hn, hn)
    # fill out port
    dlg.pn.clear()
    qtbot.keyClicks(dlg.pn, str(pn))
    # fill out username
    dlg.un.clear()
    qtbot.keyClicks(dlg.un, un)

    # select ssh keyfile radio
    dlg.kf_radio.setChecked(True)
    assert dlg.kf.isEnabled()

    # fill out ssh keyfile
    dlg.kf.clear()
    qtbot.keyClicks(dlg.kf, kf)

    # fill out passphrase
    dlg.kfp.clear()
    qtbot.keyClicks(dlg.kfp, kfp)

    # check save connection settings
    dlg.save_layout.setChecked(False)

    # Press ok and save connection settings
    qtbot.mouseClick(dlg.accept_btns.button(QDialogButtonBox.Ok),
                     Qt.LeftButton)

    # create new dialog and check fields
    new_dlg = connection_dialog_factory.get()
    assert new_dlg.cf.text() == ""
    assert not new_dlg.rm_group.isChecked()
    assert new_dlg.hn.text() == ""
    assert new_dlg.un.text() == ""
    assert new_dlg.pn.text() == "22"
    assert new_dlg.kf.text() == ""
    if (not sys.platform.startswith('linux') or
            not os.environ.get('CI') is not None):
        assert new_dlg.kfp.text() == ""


def test_kernel_connection_dialog_remember_input_password(
        qtbot, connection_dialog_factory):
    """Test that the dialog remember user's kernel connection
       settings and ssh password when the user checks the save checkbox."""

    dlg = connection_dialog_factory.get()

    cf_path = "test_cf_path"
    un = "test_username"
    hn = "test_hostname"
    pn = 123
    pw = "test_pw"

    # fill out cf path
    # dlg.cf.clear()
    qtbot.keyClicks(dlg.cf, cf_path)
    # check the remote kernel box
    dlg.rm_group.setChecked(True)
    # fill out hostname
    # dlg.hn.clear()
    qtbot.keyClicks(dlg.hn, hn)
    # fill out port
    dlg.pn.clear()
    qtbot.keyClicks(dlg.pn, str(pn))
    # fill out username
    dlg.un.clear()
    qtbot.keyClicks(dlg.un, un)

    # select password radio
    dlg.pw_radio.setChecked(True)
    assert dlg.pw.isEnabled()

    # fill out password
    dlg.pw.clear()
    qtbot.keyClicks(dlg.pw, pw)

    # check save connection settings
    dlg.save_layout.setChecked(True)

    # Press ok and save connection settings
    qtbot.mouseClick(dlg.accept_btns.button(QDialogButtonBox.Ok),
                     Qt.LeftButton)

    # create new dialog and check fields
    new_dlg = connection_dialog_factory.get()
    assert new_dlg.cf.text() == cf_path
    assert new_dlg.rm_group.isChecked()
    assert new_dlg.hn.text() == hn
    assert new_dlg.un.text() == un
    assert new_dlg.pn.text() == str(pn)
    if (not sys.platform.startswith('linux') or
            not os.environ.get('CI') is not None):
        assert new_dlg.pw.text() == pw


def test_kernel_connection_dialog_doesnt_remember_input_password(
        qtbot, connection_dialog_factory):
    """Test that the dialog doesn't remember user's kernel
       connection settings and ssh password when the user doesn't
       check the save checkbox."""

    dlg = connection_dialog_factory.get()

    cf_path = "test_cf_path"
    un = "test_username"
    hn = "test_hostname"
    pn = 123
    pw = "testpw"

    # fill out cf path
    dlg.cf.clear()
    qtbot.keyClicks(dlg.cf, cf_path)
    # check the remote kernel box
    dlg.rm_group.setChecked(True)
    # fill out hostname
    dlg.hn.clear()
    qtbot.keyClicks(dlg.hn, hn)
    # fill out port
    dlg.pn.clear()
    qtbot.keyClicks(dlg.pn, str(pn))
    # fill out username
    dlg.un.clear()
    qtbot.keyClicks(dlg.un, un)

    # select password radio
    dlg.pw_radio.setChecked(True)
    assert dlg.pw.isEnabled()

    # fill out password
    dlg.pw.clear()
    qtbot.keyClicks(dlg.pw, pw)

    # check save connection settings
    dlg.save_layout.setChecked(False)

    # Press ok and save connection settings
    qtbot.mouseClick(dlg.accept_btns.button(QDialogButtonBox.Ok),
                     Qt.LeftButton)

    # create new dialog and check fields
    new_dlg = connection_dialog_factory.get()
    assert new_dlg.cf.text() == ""
    assert not new_dlg.rm_group.isChecked()
    assert new_dlg.hn.text() == ""
    assert new_dlg.un.text() == ""
    assert new_dlg.pn.text() == "22"
    if (not sys.platform.startswith('linux') or
            not os.environ.get('CI') is not None):
        assert new_dlg.pw.text() == ""


if __name__ == "__main__":
    pytest.main()
