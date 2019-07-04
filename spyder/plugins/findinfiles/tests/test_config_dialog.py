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
from spyder.plugins.findinfiles.plugin import FindInFiles
from spyder.preferences.tests.conftest import config_dialog


class MainWindowMock:
    register_shortcut = Mock()


@pytest.mark.parametrize(
    'config_dialog',
    # [[MainWindowMock, [ConfigPlugins], [Plugins]]]
    [[None, [], [FindInFiles]]],
    indirect=True)
def test_config_dialog(config_dialog):
    configpage = config_dialog.get_page()
    assert configpage is None
