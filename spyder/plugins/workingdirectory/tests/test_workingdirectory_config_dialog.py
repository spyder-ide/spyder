# -*- coding: utf-8 -*-
# ----------------------------------------------------------------------------
# Copyright © Spyder Project Contributors
#
# Licensed under the terms of the MIT License
# ----------------------------------------------------------------------------
"""Tests for plugin config dialog."""

# Third party imports
import pytest

# Local imports
from spyder.plugins.workingdirectory.plugin import WorkingDirectory
from spyder.preferences.tests.conftest import config_dialog


@pytest.mark.parametrize(
    'config_dialog',
    # [[MainWindowMock, [ConfigPlugins], [Plugins]]]
    [[None, [], [WorkingDirectory]]],
    indirect=True)
def test_config_dialog(qtbot, config_dialog):
    configpage = config_dialog.get_page()
    configpage.save_to_conf()
    assert configpage
