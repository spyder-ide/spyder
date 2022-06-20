# -*- coding: utf-8 -*-
# ----------------------------------------------------------------------------
# Copyright © Spyder Project Contributors
#
# Licensed under the terms of the MIT License
# ----------------------------------------------------------------------------
"""Tests for plugin config dialog."""

# Standard library imports
from multiprocessing.sharedctypes import Value
from unittest.mock import Mock
import pkg_resources

# Test library imports
from qtpy.QtCore import Signal
from qtpy.QtWidgets import QMainWindow
import pytest

# Local imports
from spyder.config.base import running_in_ci
from spyder.plugins.completion.plugin import CompletionPlugin
from spyder.plugins.preferences.tests.conftest import config_dialog


if not running_in_ci():
    fallback = pkg_resources.EntryPoint.parse(
        'fallback = spyder.plugins.completion.providers.fallback.provider:'
        'FallbackProvider'
    )

    snippets = pkg_resources.EntryPoint.parse(
        'snippets = spyder.plugins.completion.providers.snippets.provider:'
        'SnippetsProvider'
    )

    lsp = pkg_resources.EntryPoint.parse(
        'lsp = spyder.plugins.completion.providers.languageserver.provider:'
        'LanguageServerProvider'
    )

    # Create a fake Spyder distribution
    d = pkg_resources.Distribution(__file__)

    # Add the providers to the fake EntryPoint
    d._ep_map = {
        'spyder.completions': {
            'fallback': fallback,
            'snippets': snippets,
            'lsp': lsp
        }
    }


class MainWindowMock(QMainWindow):
    sig_setup_finished = Signal()
    sig_pythonpath_changed = Signal(object, object)

    def __init__(self, parent):
        super(MainWindowMock, self).__init__(parent)
        self.statusbar = Mock()
        self.console = Mock()


def WrappedCompletionPlugin():
    # Add the fake distribution to the global working_set
    if not running_in_ci():
        pkg_resources.working_set.add(d, 'spyder')
    return CompletionPlugin


@pytest.mark.parametrize(
    'config_dialog',
    [[MainWindowMock, [], [WrappedCompletionPlugin()]]],
    indirect=True)
def test_config_dialog(request, config_dialog):
    expected_titles = {'General', 'Snippets', 'Linting', 'Introspection',
                       'Code style and formatting', 'Docstring style',
                       'Advanced', 'Other languages'}

    def teardown():
        # Remove fake entry points from pkg_resources
        if not running_in_ci():
            pkg_resources.working_set.by_key.pop('unknown', None)
            pkg_resources.working_set.entry_keys.pop('spyder', None)
            pkg_resources.working_set.entry_keys.pop(__file__, None)
            try:
                pkg_resources.working_set.entries.remove('spyder')
            except ValueError:
                pass

    request.addfinalizer(teardown)

    configpage = config_dialog.get_page()
    assert configpage
    tabs = configpage.tabs
    for i in range(0, tabs.count()):
        tab_text = tabs.tabText(i)
        assert tab_text in expected_titles
    configpage.save_to_conf()
