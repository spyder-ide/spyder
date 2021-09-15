# -*- coding: utf-8 -*-

# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

# Standard library imports
import os
from collections import OrderedDict
import pkg_resources
from unittest.mock import Mock, MagicMock

# Third party imports
from qtpy.QtWidgets import QMainWindow

# Local imports
from spyder.api.plugin_registration.registry import PLUGIN_REGISTRY
from spyder.config.base import running_in_ci
from spyder.config.manager import CONF
from spyder.plugins.completion.plugin import CompletionPlugin
from spyder.plugins.completion.providers.kite.utils.status import (
    check_if_kite_installed)

# This is needed to avoid an error because QtAwesome
# needs a QApplication to work correctly.
from spyder.utils.qthelpers import qapplication
app = qapplication()

# PyTest imports
import pytest
from pytestqt.qtbot import QtBot


class MainWindowMock(QMainWindow):
    register_shortcut = Mock()

    def __init__(self):
        super().__init__(None)
        self.default_style = None
        self.widgetlist = []
        self.thirdparty_plugins = []
        self.shortcut_data = []
        self.prefs_dialog_instance = None
        self._APPLICATION_TOOLBARS = MagicMock()

        self.console = Mock()
        self.sig_main_interpreter_changed = Mock()

        PLUGIN_REGISTRY.sig_plugin_ready.connect(self.register_plugin)

        # Load shortcuts for tests
        for context, name, __ in CONF.iter_shortcuts():
            self.shortcut_data.append((None, context, name, None, None))

        for attr in ['mem_status', 'cpu_status']:
            mock_attr = Mock()
            setattr(mock_attr, 'toolTip', lambda: '')
            setattr(mock_attr, 'setToolTip', lambda x: '')
            setattr(mock_attr, 'prefs_dialog_instance', lambda: '')
            setattr(self, attr, mock_attr)

    def register_plugin(self, plugin_name, external=False):
        plugin = PLUGIN_REGISTRY.get_plugin(plugin_name)
        plugin._register()

    def get_plugin(self, plugin_name):
        if plugin_name in PLUGIN_REGISTRY:
            return PLUGIN_REGISTRY.get_plugin(plugin_name)

    def set_prefs_size(self, size):
        pass

    def reset_spyder(self):
        pass


def register_all_providers():
    """Create a entry points distribution to register all the providers."""
    # This is not necessary in CIs
    if running_in_ci():
        return

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
    # Add the fake distribution to the global working_set
    pkg_resources.working_set.add(d, 'spyder')


def remove_fake_distribution():
    """Remove fake entry points from pkg_resources"""
    # This is not necessary in CIs
    if running_in_ci():
        return

    pkg_resources.working_set.by_key.pop('unknown')
    pkg_resources.working_set.entry_keys.pop('spyder')
    pkg_resources.working_set.entry_keys.pop(__file__)
    pkg_resources.working_set.entries.remove('spyder')


@pytest.fixture(scope="module")
def qtbot_module(qapp, request):
    """Module fixture for qtbot."""
    result = QtBot(request)
    return result


def create_completion_plugin(create_fake_distribution=None,
                             remove_fake_distribution=None):
    @pytest.fixture(scope='module')
    def completion_plugin_wrap(qtbot_module, request):
        if create_fake_distribution is not None:
            create_fake_distribution()

        main_window = MainWindowMock()
        completions = CompletionPlugin(main_window, CONF)

        # Remove Kite (In case it was registered via setup.py)
        completions.providers.pop('kite', None)

        def teardown():
            if remove_fake_distribution is not None:
                remove_fake_distribution()

        request.addfinalizer(teardown)
        return completions
    return completion_plugin_wrap


completion_plugin = create_completion_plugin()
completion_plugin_all = create_completion_plugin(
    create_fake_distribution=register_all_providers,
    remove_fake_distribution=remove_fake_distribution)


@pytest.fixture(scope='function')
def completion_plugin_all_started(request, qtbot_module,
                                  completion_plugin_all):

    completion_plugin = completion_plugin_all

    os.environ['SPY_TEST_USE_INTROSPECTION'] = 'True'
    completion_plugin.wait_for_ms = 20000
    completion_plugin.start_all_providers()

    kite_installed, _ = check_if_kite_installed()
    total_providers = 3 + int(kite_installed)

    def wait_until_all_started():
        all_started = True
        for provider in completion_plugin.providers:
            if provider == 'kite' and not kite_installed:
                continue

            provider_info = completion_plugin.providers[provider]
            all_started &= provider_info['status'] == completion_plugin.RUNNING
        return all_started

    qtbot_module.waitUntil(wait_until_all_started, timeout=30000)

    with qtbot_module.waitSignal(
            completion_plugin.sig_language_completions_available, timeout=30000) as blocker:
        completion_plugin.start_completion_services_for_language('python')

    capabilities, _ = blocker.args

    def teardown():
        os.environ['SPY_TEST_USE_INTROSPECTION'] = 'False'
        completion_plugin.unregister()

    request.addfinalizer(teardown)
    return completion_plugin, capabilities
