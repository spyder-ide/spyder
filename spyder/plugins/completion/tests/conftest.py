# -*- coding: utf-8 -*-

# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

# Standard library imports
import os.path as osp
from unittest.mock import Mock, MagicMock

# Third party imports
from lsprotocol import types as lsp
from qtpy.QtCore import QObject, Signal, Slot
from qtpy.QtWidgets import QMainWindow

# Local imports
from spyder.api.plugin_registration.registry import PLUGIN_REGISTRY
from spyder.config.manager import CONF
from spyder.plugins.completion.plugin import CompletionPlugin

# This is needed to avoid an error because QtAwesome
# needs a QApplication to work correctly.
from spyder.utils.qthelpers import qapplication
app = qapplication()

# PyTest imports
import pytest
from pytestqt.qtbot import QtBot


class MainWindowMock(QMainWindow):

    def __init__(self):
        super().__init__(None)
        self.register_shortcut = Mock()
        self.default_style = None
        self.widgetlist = []
        self.thirdparty_plugins = []
        self.shortcut_data = []
        self.prefs_dialog_instance = None
        self._APPLICATION_TOOLBARS = MagicMock()

        self.console = Mock()

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

    def get_plugin(self, plugin_name, error=True):
        if plugin_name in PLUGIN_REGISTRY:
            return PLUGIN_REGISTRY.get_plugin(plugin_name)


@pytest.fixture(scope="module")
def qtbot_module(qapp, request):
    """Module fixture for qtbot."""
    result = QtBot(request)
    return result


def create_completion_plugin():
    @pytest.fixture(scope='module')
    def completion_plugin_wrap(qtbot_module, request):
        main_window = MainWindowMock()
        completions = CompletionPlugin(main_window, CONF)

        def teardown():
            for provider_info in completions.providers.values():
                CONF.unobserve_configuration(provider_info['instance'])
            CONF.unobserve_configuration(completions)
            PLUGIN_REGISTRY.reset()
            main_window.close()

        request.addfinalizer(teardown)

        return completions
    return completion_plugin_wrap


completion_plugin_all = create_completion_plugin()


class _WarmupReceiver(QObject):
    """Stand-in for a CodeEditor that only needs to receive responses."""

    sig_response = Signal(str, object)

    @Slot(str, object)
    def handle_response(self, method, params):
        self.sig_response.emit(method, params)


@pytest.fixture(scope='module')
def completion_plugin_all_started(request, qtbot_module,
                                  completion_plugin_all):
    """Start all legacy completion providers once per test module."""
    completion_plugin = completion_plugin_all
    completion_plugin.wait_for_ms = 20000
    completion_plugin.start_all_providers()

    def wait_until_all_started():
        return all(
            info['status'] == completion_plugin.RUNNING
            for info in completion_plugin.providers.values()
        )

    qtbot_module.waitUntil(wait_until_all_started, timeout=30000)
    completion_plugin.start_completion_services_for_language('python')

    def teardown():
        for provider_name in list(completion_plugin.providers):
            completion_plugin.shutdown_provider_instance(provider_name)

    request.addfinalizer(teardown)
    return completion_plugin, None


@pytest.fixture(scope='module')
def language_services_all_started(
    request, qtbot_module, completion_plugin_all_started
):
    """LanguageServices plugin serving Python through the legacy adapter.

    Returns ``(language_services, completion_plugin, capabilities)``.
    """
    from spyder.plugins.completion.adapter import LegacyCompletionsProvider
    from spyder.plugins.languageservices.api.languages import Language
    from spyder.plugins.languageservices.plugin import (
        LanguageServices,
        wait_for,
    )

    completion_plugin, _ = completion_plugin_all_started
    language_services = LanguageServices(completion_plugin.main, CONF)
    # The built-in providers come from the spyder.language_services entry
    # points loaded by the plugin. The legacy adapter wraps third-party ones.
    legacy = LegacyCompletionsProvider(language_services, completion_plugin)
    language_services.services_api.register_provider(legacy)
    providers = [
        language_services.get_provider(name)
        for name in language_services.provider_names()
    ]
    for provider in providers:
        wait_for(language_services.start_provider(provider.NAME), 30)
    wait_for(language_services.start_language(Language.PYTHON), 60)
    qtbot_module.waitUntil(
        lambda: "pylsp" in language_services.providers_for(Language.PYTHON),
        timeout=30000,
    )
    capabilities = language_services.capabilities(Language.PYTHON)
    assert capabilities.completion_provider is not None

    def teardown():
        for provider in providers:
            wait_for(language_services.stop_provider(provider.NAME), 30)
            CONF.unobserve_configuration(provider)
        CONF.unobserve_configuration(language_services)

    request.addfinalizer(teardown)
    return language_services, completion_plugin, capabilities


def route_diagnostics(language_services, editor):
    """Connect the plugin diagnostics to ``editor`` (returns the slot)."""
    from spyder.plugins.languageservices.api.uri import uri_as_path

    def on_diagnostics(params):
        if uri_as_path(params.uri) == osp.abspath(editor.filename):
            editor.handle_response(
                lsp.TEXT_DOCUMENT_PUBLISH_DIAGNOSTICS, params.diagnostics
            )

    language_services.sig_diagnostics.connect(on_diagnostics)
    return on_diagnostics
