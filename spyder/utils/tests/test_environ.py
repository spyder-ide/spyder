# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
#

"""
Tests for environ.py
"""

# Test library imports
import pytest

# Third party imports
from qtpy.QtCore import QTimer

# Local imports
from spyder.utils.test import close_message_box


@pytest.fixture
def environ_dialog(qtbot):
    "Setup the Environment variables Dialog."
    QTimer.singleShot(1000, lambda: close_message_box(qtbot))
    from spyder.utils.environ import UserEnvDialog
    dialog = UserEnvDialog()
    qtbot.addWidget(dialog)

    return dialog


def test_environ(environ_dialog, qtbot):
    """Test the environment variables dialog."""
    environ_dialog.show()
    assert environ_dialog


if __name__ == "__main__":
    pytest.main()
