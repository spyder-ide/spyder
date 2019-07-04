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
from spyder.plugins.editor.plugin import Editor
from spyder.preferences.tests.conftest import config_dialog


class MainWindowMock:
    register_shortcut = Mock()
    file_menu_actions = []
    file_toolbar_actions = []
    edit_menu_actions = []
    edit_toolbar_actions = []
    run_menu_actions = []
    run_toolbar_actions = []
    debug_menu_actions = []
    debug_toolbar_actions = []
    source_menu_actions = []
    source_toolbar_actions = []
    statusBar = Mock()
    all_actions_defined = Mock()
    sig_pythonpath_changed = Mock()
    new_instance = Mock()
    plugin_focus_changed = Mock()
    fallback_completions = Mock()


@pytest.mark.parametrize(
    'config_dialog',
    # [[MainWindowMock, [ConfigPlugins], [Plugins]]]
    [[MainWindowMock, [], [Editor]]],
    indirect=True)
def test_config_dialog(config_dialog):
    configpage = config_dialog.get_page()
    assert configpage
    configpage.save_to_conf()
