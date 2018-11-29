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
    KernelConnectionDialog)
from spyder.config.main import CONF


# =============================================================================
# Fixtures
# =============================================================================
@pytest.fixture
def connection_dialog_factory(qtbot, request):
    """Set up kernel connection dialog."""
    class DialogFactory(object):
        def get_default_dialog(self):
            dialog = KernelConnectionDialog()
            request.addfinalizer(dialog.close)
            return dialog

        def submit_filled_dialog(self, use_keyfile, save_settings):
            dlg = self.get_default_dialog()

            # fill out cf path
            dlg.cf.clear()
            qtbot.keyClicks(dlg.cf, pytest.cf_path)
            # check the remote kernel box
            dlg.rm_group.setChecked(True)
            # fill out hostname
            dlg.hn.clear()
            qtbot.keyClicks(dlg.hn, pytest.hn)
            # fill out port
            dlg.pn.clear()
            qtbot.keyClicks(dlg.pn, str(pytest.pn))
            # fill out username
            dlg.un.clear()
            qtbot.keyClicks(dlg.un, pytest.un)

            if use_keyfile:
                # select ssh keyfile radio
                dlg.kf_radio.setChecked(True)
                assert dlg.kf.isEnabled()

                # fill out ssh keyfile
                dlg.kf.clear()
                qtbot.keyClicks(dlg.kf, pytest.kf)

                # fill out passphrase
                dlg.kfp.clear()
                qtbot.keyClicks(dlg.kfp, pytest.kfp)
            else:
                # select password radio
                dlg.pw_radio.setChecked(True)
                assert dlg.pw.isEnabled()

                # fill out password
                dlg.pw.clear()
                qtbot.keyClicks(dlg.pw, pytest.pw)

            # check save connection settings
            dlg.save_layout.setChecked(save_settings)

            return dlg

    def teardown():
        """Clear existing-kernel config and keyring passwords."""
        CONF.remove_section("existing-kernel")

        try:
            import keyring
            keyring.set_password("spyder_remote_kernel",
                                 "ssh_key_passphrase", "")
            keyring.set_password("spyder_remote_kernel",
                                 "ssh_password", "")
        except Exception:
            pass

    # test form values
    pytest.cf_path = "cf_path"
    pytest.un = "test_username"
    pytest.hn = "test_hostname"
    pytest.pn = 123
    pytest.kf = "test_kf"
    pytest.kfp = "test_kfp"
    pytest.pw = "test_pw"

    request.addfinalizer(teardown)
    return DialogFactory()


# =============================================================================
# Tests
# =============================================================================
def test_connection_dialog_remembers_input_with_ssh_passphrase(
        qtbot, connection_dialog_factory):
    """
    Test that the dialog remembers the user's kernel connection
    settings and ssh key passphrase when the user checks the
    save checkbox.
    """

    dlg = connection_dialog_factory.submit_filled_dialog(use_keyfile=True,
                                                         save_settings=True)

    # Press ok and save connection settings
    qtbot.mouseClick(dlg.accept_btns.button(QDialogButtonBox.Ok),
                     Qt.LeftButton)

    # create new dialog and check fields
    new_dlg = connection_dialog_factory.get_default_dialog()
    assert new_dlg.cf.text() == pytest.cf_path
    assert new_dlg.rm_group.isChecked()
    assert new_dlg.hn.text() == pytest.hn
    assert new_dlg.un.text() == pytest.un
    assert new_dlg.pn.text() == str(pytest.pn)
    assert new_dlg.kf.text() == pytest.kf
    if (not sys.platform.startswith('linux') or
            not os.environ.get('CI') is not None):
        assert new_dlg.kfp.text() == pytest.kfp


def test_connection_dialog_doesnt_remember_input_with_ssh_passphrase(
        qtbot, connection_dialog_factory):
    """
    Test that the dialog doesn't remember the user's kernel
    connection settings and ssh key passphrase when the user doesn't
    check the save checkbox.
    """

    dlg = connection_dialog_factory.submit_filled_dialog(use_keyfile=True,
                                                         save_settings=False)

    # Press ok and save connection settings
    qtbot.mouseClick(dlg.accept_btns.button(QDialogButtonBox.Ok),
                     Qt.LeftButton)

    # create new dialog and check fields
    new_dlg = connection_dialog_factory.get_default_dialog()
    assert new_dlg.cf.text() == ""
    assert not new_dlg.rm_group.isChecked()
    assert new_dlg.hn.text() == ""
    assert new_dlg.un.text() == ""
    assert new_dlg.pn.text() == "22"
    assert new_dlg.kf.text() == ""
    if (not sys.platform.startswith('linux') or
            not os.environ.get('CI') is not None):
        assert new_dlg.kfp.text() == ""


def test_connection_dialog_remembers_input_with_password(
        qtbot, connection_dialog_factory):
    """
    Test that the dialog remembers the user's kernel connection
    settings and ssh password when the user checks the save checkbox.
    """

    dlg = connection_dialog_factory.submit_filled_dialog(use_keyfile=False,
                                                         save_settings=True)

    # Press ok and save connection settings
    qtbot.mouseClick(dlg.accept_btns.button(QDialogButtonBox.Ok),
                     Qt.LeftButton)

    # create new dialog and check fields
    new_dlg = connection_dialog_factory.get_default_dialog()
    assert new_dlg.cf.text() == pytest.cf_path
    assert new_dlg.rm_group.isChecked()
    assert new_dlg.hn.text() == pytest.hn
    assert new_dlg.un.text() == pytest.un
    assert new_dlg.pn.text() == str(pytest.pn)
    if (not sys.platform.startswith('linux') or
            not os.environ.get('CI') is not None):
        assert new_dlg.pw.text() == pytest.pw


def test_connection_dialog_doesnt_remember_input_with_password(
        qtbot, connection_dialog_factory):
    """
    Test that the dialog doesn't remember the user's kernel
    connection settings and ssh password when the user doesn't
    check the save checkbox.
    """

    dlg = connection_dialog_factory.submit_filled_dialog(use_keyfile=False,
                                                         save_settings=False)

    # Press ok and save connection settings
    qtbot.mouseClick(dlg.accept_btns.button(QDialogButtonBox.Ok),
                     Qt.LeftButton)

    # create new dialog and check fields
    new_dlg = connection_dialog_factory.get_default_dialog()
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
