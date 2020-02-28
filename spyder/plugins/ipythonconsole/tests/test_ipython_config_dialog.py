# -*- coding: utf-8 -*-
# ----------------------------------------------------------------------------
# Copyright © Spyder Project Contributors
#
# Licensed under the terms of the MIT License
# ----------------------------------------------------------------------------
"""Tests for plugin config dialog."""

try:
    from unittest.mock import Mock
except ImportError:
    from mock import Mock  # Python 2

# Test library imports
import pytest

# Local imports
from spyder.plugins.ipythonconsole.plugin import IPythonConsole
from spyder.preferences.tests.conftest import config_dialog


class MainWindowMock:
    register_shortcut = Mock()


@pytest.mark.parametrize(
    'config_dialog',
    # [[MainWindowMock, [ConfigPlugins], [Plugins]]]
    [[MainWindowMock, [], [IPythonConsole]]],
    indirect=True)
def test_config_dialog(config_dialog):
    configpage = config_dialog.get_page()
    assert configpage
    configpage.save_to_conf()
