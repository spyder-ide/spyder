# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
#

"""
Tests for environ.py
"""
# Standard library imports
import os

# Test library imports
import pytest

# Third party imports
from qtpy.QtCore import QTimer

# Local imports
from spyder.utils.environ import get_user_environment_variables, UserEnvDialog
from spyder.utils.test import close_message_box


@pytest.fixture
def environ_dialog(qtbot):
    "Setup the Environment variables Dialog."
    QTimer.singleShot(1000, lambda: close_message_box(qtbot))
    dialog = UserEnvDialog()
    qtbot.addWidget(dialog)

    return dialog


def test_get_user_environment_variables():
    """Test get_user_environment_variables function"""

    # All platforms should have a path environment variable, but
    # Windows may have mixed case.
    keys = {k.lower() for k in get_user_environment_variables()}
    assert "path" in keys

    # Test variable value with newline characters.
    # Regression test for spyder-ide#20097
    user_var = f"This is a variable with {os.linesep} characters"
    os.environ['USER_VAR'] = user_var
    user_env = get_user_environment_variables()
    assert user_env['USER_VAR'] == user_var


def test_environ(environ_dialog, qtbot):
    """Test the environment variables dialog."""
    environ_dialog.show()
    assert environ_dialog

    # All platforms should have a path environment variable, but
    # Windows may have mixed case.
    keys = {k.lower() for k in environ_dialog.get_value()}
    assert "path" in keys


if __name__ == "__main__":
    pytest.main()
