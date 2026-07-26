# -*- coding: utf-8 -*-

# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

# Standard library imports
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

        return completions
    return completion_plugin_wrap


completion_plugin_all = create_completion_plugin()


class _WarmupReceiver(QObject):
    """Stand-in for a CodeEditor that only needs to receive responses."""

    sig_response = Signal(str, object)

    @Slot(str, object)
    def handle_response(self, method, params):
        self.sig_response.emit(method, params)


def _warmup_python_provider(completion_plugin, qtbot_module):
    """Pay the providers' first-request cold-start cost here, not in tests."""
    receiver = _WarmupReceiver()
    text = 'import math\nmath.h'

    open_params = {
        'file': '__completion_warmup__.py',
        'language': 'python',
        'version': 1,
        'text': text,
        'response_instance': receiver,
        'offset': 1,
        'selection_start': 0,
        'selection_end': 0,
        'codeeditor': receiver,
        'requires_response': False,
    }
    with qtbot_module.waitSignal(receiver.sig_response, timeout=30000):
        completion_plugin.send_request(
            'python', lsp.TEXT_DOCUMENT_DID_OPEN, open_params
        )

    completion_params = {
        'file': '__completion_warmup__.py',
        'line': 1,
        'column': len('math.h'),
        'offset': len(text),
        'selection_start': 0,
        'selection_end': 0,
        'current_word': 'h',
        'codeeditor': receiver,
        'response_instance': receiver,
        'requires_response': True,
    }
    with qtbot_module.waitSignal(receiver.sig_response, timeout=30000):
        completion_plugin.send_request(
            'python', lsp.TEXT_DOCUMENT_COMPLETION, completion_params
        )


@pytest.fixture(scope='module')
def completion_plugin_all_started(request, qtbot_module,
                                  completion_plugin_all):
    """Start all completion providers once per test module and reuse them."""
    completion_plugin = completion_plugin_all
    completion_plugin.wait_for_ms = 20000
    completion_plugin.start_all_providers()

    def wait_until_all_started():
        all_started = True
        for provider in completion_plugin.providers:

            provider_info = completion_plugin.providers[provider]
            all_started &= provider_info['status'] == completion_plugin.RUNNING
        return all_started

    qtbot_module.waitUntil(wait_until_all_started, timeout=30000)

    with qtbot_module.waitSignal(
            completion_plugin.sig_language_completions_available,
            timeout=30000) as blocker:
        completion_plugin.start_completion_services_for_language('python')

    capabilities, _ = blocker.args

    _warmup_python_provider(completion_plugin, qtbot_module)

    def teardown():
        completion_plugin.stop_all_providers()

    request.addfinalizer(teardown)
    return completion_plugin, capabilities
