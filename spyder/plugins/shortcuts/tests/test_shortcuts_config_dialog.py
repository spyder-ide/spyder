# -*- coding: utf-8 -*-
# ----------------------------------------------------------------------------
# Copyright © Spyder Project Contributors
#
# Licensed under the terms of the MIT License
# ----------------------------------------------------------------------------
"""Tests for plugin config dialog."""

# Standard library imports
import pytest

# Local imports
from spyder.plugins.shortcuts.plugin import Shortcuts
from spyder.plugins.preferences.tests.conftest import config_dialog


@pytest.mark.parametrize(
    'config_dialog',
    [[None, [], [Shortcuts]]],
    indirect=True)
def test_config_dialog(config_dialog):
    configpage = config_dialog.get_page()
    configpage.save_to_conf()
    assert configpage
