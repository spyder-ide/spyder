# -*- coding: utf-8 -*-
# ----------------------------------------------------------------------------
# Copyright © Spyder Project Contributors
#
# Licensed under the terms of the MIT License
# ----------------------------------------------------------------------------
"""Tests for plugin config dialog."""

from unittest.mock import Mock

# Test library imports
import pytest
from qtpy.QtWidgets import QMainWindow

# Local imports
from spyder.plugins.editor.plugin import Editor
from spyder.plugins.preferences.tests.conftest import config_dialog


class MainWindowMock(QMainWindow):
    register_shortcut = Mock()
    file_menu_actions = []
    file_toolbar_actions = []
    statusbar = Mock()
    new_instance = Mock()
    plugin_focus_changed = Mock()
    fallback_completions = Mock()
    ipyconsole = Mock()
    mainmenu = Mock()
    sig_setup_finished = Mock()


@pytest.mark.parametrize(
    'config_dialog',
    # [[MainWindowMock, [ConfigPlugins], [Plugins]]]
    [[MainWindowMock, [], [Editor]]],
    indirect=True)
def test_config_dialog(config_dialog):
    configpage = config_dialog.get_page()
    assert configpage
    configpage.save_to_conf()
