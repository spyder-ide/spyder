# -*- coding: utf-8 -*-
# ----------------------------------------------------------------------------
# Copyright © Spyder Project Contributors
#
# Licensed under the terms of the MIT License
# ----------------------------------------------------------------------------
"""Tests for plugin config dialog."""


# Test library imports
import pytest

# Local imports
from spyder.plugins.history.plugin import HistoryLog
from spyder.plugins.preferences.tests.conftest import config_dialog


@pytest.mark.parametrize(
    'config_dialog',
    # [[MainWindowMock, [ConfigPlugins], [Plugins]]]
    [[None, [], [HistoryLog]]],
    indirect=True)
def test_config_dialog(config_dialog):
    configpage = config_dialog.get_page()
    assert configpage
    configpage.save_to_conf()
