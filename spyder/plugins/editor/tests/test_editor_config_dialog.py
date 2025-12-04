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
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.register_shortcut = Mock()
        self.file_menu_actions = []
        self.file_toolbar_actions = []
        self.statusbar = Mock()
        self.new_instance = Mock()
        self.plugin_focus_changed = Mock()
        self.fallback_completions = Mock()
        self.ipyconsole = Mock()
        self.mainmenu = Mock()
        self.sig_setup_finished = Mock()
        self.switcher = Mock()


@pytest.mark.parametrize(
    'config_dialog',
    # [[MainWindowMock, [ConfigPlugins], [Plugins]]]
    [[MainWindowMock, [], [Editor]]],
    indirect=True)
def test_config_dialog(config_dialog):
    configpage = config_dialog.get_page()
    assert configpage
    configpage.save_to_conf()
