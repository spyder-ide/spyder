# -*- coding: utf-8 -*-
# ----------------------------------------------------------------------------
# Copyright © Spyder Project Contributors
#
# Licensed under the terms of the MIT License
# ----------------------------------------------------------------------------
"""Tests for plugin config dialog."""

# Standard library imports
from unittest.mock import Mock

# Test library imports
from qtpy.QtCore import Signal
from qtpy.QtWidgets import QMainWindow
import pytest

# Local imports
from spyder.plugins.completion.plugin import CompletionPlugin
from spyder.plugins.preferences.tests.conftest import config_dialog  # noqa


class MainWindowMock(QMainWindow):
    sig_setup_finished = Signal()

    def __init__(self, parent):
        super(MainWindowMock, self).__init__(parent)
        self.statusbar = Mock()
        self.console = Mock()


@pytest.mark.parametrize(
    'config_dialog',
    [[MainWindowMock, [], [CompletionPlugin]]],
    indirect=True)
def test_config_dialog(config_dialog):
    expected_titles = {'General', 'Snippets', 'Linting', 'Introspection',
                       'Code style and formatting', 'Docstring style',
                       'Advanced', 'Other languages'}

    configpage = config_dialog.get_page()
    assert configpage
    tabs = configpage.tabs
    for i in range(0, tabs.count()):
        tab_text = tabs.tabText(i)
        assert tab_text in expected_titles
    configpage.save_to_conf()
