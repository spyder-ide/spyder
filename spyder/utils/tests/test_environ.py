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
def setup_environ(qtbot):
    "Setup the Environment variables Dialog taking into account the os."    
    if os.name == 'nt':
        from spyder.utils.environ import WinUserEnvDialog
        dialog = WinUserEnvDialog()
    else:        
        from spyder.utils.environ import EnvDialog
        dialog = EnvDialog()
    qtbot.addWidget(dialog)
    
    return dialog

def test_environ(qtbot):
    """Test the environment variables dialog."""
    QTimer.singleShot(1000, lambda: close_message_box(qtbot))
    dialog = setup_environ(qtbot)
    dialog.show()
    assert dialog


if __name__ == "__main__":
    pytest.main()
