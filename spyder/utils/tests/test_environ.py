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
import subprocess

# Test library imports
import pytest

# Third party imports
from qtpy.QtCore import QTimer

# Local imports
from spyder.py3compat import PY3
from spyder.utils.test import close_message_box
from spyder.utils.environ import clean_env


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


@pytest.mark.skipif(PY3, reason=("This tests only applies to Python 2."))
def test_clean_env():
    env = {
        'foo': '/foo/bar/測試',
        'bar': '/spam',
        'PYTHONPATH': u'\u6e2c\u8a66',
    }
    new_env = clean_env(env)
    assert new_env['foo'] == '/foo/bar/\xe6\xb8\xac\xe8\xa9\xa6'
    assert new_env['PYTHONPATH'] == '\xe6\xb8\xac\xe8\xa9\xa6'


if __name__ == "__main__":
    pytest.main()
