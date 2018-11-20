# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright © Spyder Project Contributors
#
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)
# -----------------------------------------------------------------------------

"""Tests for the Existing Kernel Connection widget."""

# Third party imports
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
def setup_dialog(qtbot):
    """Set up kernel connection dialog."""
    widget = KernelConnectionDialog()
    qtbot.addWidget(widget)

    return widget


# =============================================================================
# Tests
# =============================================================================
def test_save(qtbot):
    dlg = setup_dialog(qtbot)

    cf_path = "test_cf_path"
    un = "test_username"
    hn = "test_hostname"
    pn = 123
    kf = "test_kf"
    kfp = "test_kfp"

    # fill out cf path
    qtbot.keyClicks(dlg.cf, cf_path)
    # check the remote kernel box
    dlg.rm_group.setChecked(True)
    # fill out hostname
    qtbot.keyClicks(dlg.hn, hn)
    # fill out port
    dlg.pn.clear()
    qtbot.keyClicks(dlg.pn, str(pn))
    # fill out username
    qtbot.keyClicks(dlg.un, un)

    # select ssh keyfile radio
    dlg.kf_radio.setChecked(True)
    assert dlg.kf.isEnabled()

    # fill out ssh keyfile
    qtbot.keyClicks(dlg.kf, kf)

    # fill out passphrase
    dlg.kfp.clear()
    qtbot.keyClicks(dlg.kfp, kfp)

    # check save connection settings
    dlg.save_layout.setChecked(True)

    # save connection settings
    dlg.save_connection_settings()

    # create new dialog and check fields
    new_dlg = setup_dialog(qtbot)
    assert new_dlg.cf.text() == cf_path
    assert new_dlg.rm_group.isChecked()
    assert new_dlg.hn.text() == hn
    assert new_dlg.un.text() == un
    assert new_dlg.pn.text() == str(pn)
    assert new_dlg.kf.text() == kf
    assert new_dlg.kfp.text() == kfp


if __name__ == "__main__":
    pytest.main()
