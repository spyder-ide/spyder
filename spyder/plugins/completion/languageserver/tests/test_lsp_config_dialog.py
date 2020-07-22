# -*- coding: utf-8 -*-
# ----------------------------------------------------------------------------
# Copyright © Spyder Project Contributors
#
# Licensed under the terms of the MIT License
# ----------------------------------------------------------------------------
"""Tests for plugin config dialog."""

# Standard library imports
try:
    from unittest.mock import Mock
except ImportError:
    from mock import Mock

# Test library imports
from qtpy.QtCore import QObject, Signal
import pytest

# Local imports
from spyder.plugins.completion.languageserver.plugin import LanguageServerPlugin
from spyder.preferences.tests.conftest import config_dialog


class MainWindowMock(QObject):
    sig_setup_finished = Signal()

    def __init__(self):
        super(MainWindowMock, self).__init__(None)
        self.statusBar = Mock()


@pytest.mark.parametrize(
    'config_dialog',
    # [[MainWindowMock, [ConfigPlugins], [Plugins]]]
    [[MainWindowMock, [], [LanguageServerPlugin]]],
    indirect=True)
def test_config_dialog(config_dialog):
    configpage = config_dialog.get_page()
    assert configpage
    configpage.save_to_conf()
