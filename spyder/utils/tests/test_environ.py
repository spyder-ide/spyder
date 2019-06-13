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
from spyder.utils.test import close_message_box


@pytest.fixture
def environ_dialog(qtbot):
    "Setup the Environment variables Dialog taking into account the os."
    QTimer.singleShot(1000, lambda: close_message_box(qtbot))
    if os.name == 'nt':
        from spyder.utils.environ import WinUserEnvDialog
        dialog = WinUserEnvDialog()
    else:
        from spyder.utils.environ import EnvDialog
        dialog = EnvDialog()
    qtbot.addWidget(dialog)

    return dialog


def test_environ(environ_dialog, qtbot):
    """Test the environment variables dialog."""
    environ_dialog.show()
    assert environ_dialog


if __name__ == "__main__":
    pytest.main()
