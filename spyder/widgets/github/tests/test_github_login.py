# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright © Spyder Project Contributors
#
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)
# -----------------------------------------------------------------------------

"""Tests for the Github authentication dialog."""

# Third party imports
import pytest
from qtpy.QtCore import Qt

# Local imports
from spyder.widgets.github.gh_login import DlgGitHubLogin


# =============================================================================
# Fixtures
# =============================================================================
@pytest.fixture
def github_dialog(qtbot):
    """Set up error report dialog."""
    widget = DlgGitHubLogin(None, None, None, None)
    qtbot.addWidget(widget)
    return widget


# =============================================================================
# Tests
# =============================================================================
def test_dialog(github_dialog, qtbot):
    """Test that error report dialog UI behaves properly."""
    dlg = github_dialog

    # Assert Sign in button is disabled at first
    assert not dlg.bt_sign_in.isEnabled()

    # Introduce Username
    qtbot.keyClicks(dlg.le_user, 'user')

    # Assert Sign in button is still disabled
    assert not dlg.bt_sign_in.isEnabled()

    # Introduce now password
    qtbot.keyClicks(dlg.le_password, 'password')

    # Assert Sign in button is enabled
    assert dlg.bt_sign_in.isEnabled()

    # Remove user and password
    dlg.le_user.selectAll()
    dlg.le_user.cut()
    dlg.le_password.selectAll()
    dlg.le_user.cut()

    # Assert Sign in is disabled
    assert not dlg.bt_sign_in.isEnabled()

    # Change tab and add token
    dlg.tabs.setCurrentIndex(1)
    qtbot.keyClicks(dlg.le_token, 'token')

    # Assert Sign in button is enabled
    assert dlg.bt_sign_in.isEnabled()


if __name__ == "__main__":
    pytest.main()
