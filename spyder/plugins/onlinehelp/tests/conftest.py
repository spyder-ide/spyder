# -*- coding: utf-8 -*-
# ----------------------------------------------------------------------------
# Copyright © Spyder Project Contributors
#
# Licensed under the terms of the MIT License
# ----------------------------------------------------------------------------
"""Pytest configuration for plugin tests."""

try:
    from unittest.mock import Mock
except ImportError:
    from mock import Mock  # Python 2

# Test library imports
import pytest

# Local imports
from spyder.plugins.onlinehelp.plugin import OnlineHelp
from spyder.preferences.configdialog import ConfigDialog


class MainWindowMock:
    register_shortcut = Mock()


@pytest.fixture
def config_dialog(qtbot):
    dlg = ConfigDialog()
    qtbot.addWidget(dlg)
    main = MainWindowMock()
    plugin = OnlineHelp(main)
    widget = plugin._create_configwidget(dlg, main)
    if widget:
        dlg.add_page(widget)
    dlg.show()
    return dlg
