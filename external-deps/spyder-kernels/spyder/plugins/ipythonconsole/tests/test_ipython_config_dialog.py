# -*- coding: utf-8 -*-
# ----------------------------------------------------------------------------
# Copyright © Spyder Project Contributors
#
# Licensed under the terms of the MIT License
# ----------------------------------------------------------------------------
"""Tests for plugin config dialog."""

from unittest.mock import MagicMock

# Test library imports
import pytest
from qtpy.QtWidgets import QMainWindow

# Local imports
from spyder.plugins.ipythonconsole.plugin import IPythonConsole
from spyder.plugins.preferences.tests.conftest import config_dialog


class MainWindowMock(QMainWindow):
    register_shortcut = MagicMock()
    editor = MagicMock()

    def __getattr__(self, attr):
        return MagicMock()


@pytest.mark.parametrize(
    'config_dialog',
    # [[MainWindowMock, [ConfigPlugins], [Plugins]]]
    [[MainWindowMock, [], [IPythonConsole]]],
    indirect=True)
def test_config_dialog(config_dialog):
    configpage = config_dialog.get_page()
    assert configpage
    configpage.save_to_conf()
