# -*- coding: utf-8 -*-

# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

import os
from textwrap import dedent

import pytest
from qtpy.QtCore import QObject, Signal

from spyder.config.main import CONF
from spyder.plugins.editor.lsp.client import LSPClient
from spyder.plugins.editor.lsp import (
    SERVER_CAPABILITES, LSPRequestTypes, LSPEventTypes)



class LSPSignalCapture(QObject):
    sig_response_signal = Signal(str, dict)
    sig_lsp_notification = Signal(dict, str)


@pytest.fixture
def lsp_client(qtbot):
    config = CONF.get('lsp-server', 'python')
    lsp_signal = LSPSignalCapture()
    lsp = LSPClient(None, config['args'], config, config['external'],
                    plugin_configurations=config.get('configurations', {}),
                    language='python')
    lsp.register_plugin_type(
        LSPEventTypes.DOCUMENT, lsp_signal.sig_lsp_notification)
    # qtbot.addWidget(lsp)
    yield lsp, lsp_signal
    if os.name != 'nt':
        lsp.stop()


def test_initialization(qtbot, lsp_client):
    lsp, lsp_signal = lsp_client
    with qtbot.waitSignal(
        lsp_signal.sig_lsp_notification, timeout=10000) as blocker:
        lsp.start()
    options, _ = blocker.args
    assert all([option in SERVER_CAPABILITES for option in options.keys()])


def test_get_signature(qtbot, lsp_client):
    lsp, lsp_signal = lsp_client
    with qtbot.waitSignal(
        lsp_signal.sig_lsp_notification, timeout=10000):
        lsp.start()
    open_params = {
        'file': 'test.py',
        'language': 'python',
        'version': 1,
        'text': "import os\nos.walk(\n",
        'signal': lsp_signal.sig_response_signal,
        'requires_response': False
    }

    with qtbot.waitSignal(
        lsp_signal.sig_response_signal, timeout=10000) as blocker:
        lsp.perform_request(LSPRequestTypes.DOCUMENT_DID_OPEN, open_params)

    signature_params = {
        'file': 'test.py',
        'line': 1,
        'column': 10,
        'requires_response': True,
        'response_sig': lsp_signal.sig_response_signal
    }

    with qtbot.waitSignal(
        lsp_signal.sig_response_signal, timeout=10000) as blocker:
        lsp.perform_request(
            LSPRequestTypes.DOCUMENT_SIGNATURE, signature_params)
    _, response = blocker.args
    assert response['params']['signatures']['label'].startswith('walk')


def test_get_completions(qtbot, lsp_client):
    lsp, lsp_signal = lsp_client
    with qtbot.waitSignal(
        lsp_signal.sig_lsp_notification, timeout=10000):
        lsp.start()
    open_params = {
        'file': 'test.py',
        'language': 'python',
        'version': 1,
        'text': "import o",
        'signal': lsp_signal.sig_response_signal,
        'requires_response': False
    }

    with qtbot.waitSignal(
        lsp_signal.sig_response_signal, timeout=10000) as blocker:
        lsp.perform_request(LSPRequestTypes.DOCUMENT_DID_OPEN, open_params)

    completion_params = {
        'file': 'test.py',
        'line': 0,
        'column': 8,
        'requires_response': True,
        'response_sig': lsp_signal.sig_response_signal
    }

    with qtbot.waitSignal(
        lsp_signal.sig_response_signal, timeout=10000) as blocker:
        lsp.perform_request(
            LSPRequestTypes.DOCUMENT_COMPLETION, completion_params)
    _, response = blocker.args
    completions = response['params']
    assert 'os' in [x['label'] for x in completions]


def test_go_to_definition(qtbot, lsp_client):
    lsp, lsp_signal = lsp_client
    with qtbot.waitSignal(
        lsp_signal.sig_lsp_notification, timeout=10000):
        lsp.start()
    open_params = {
        'file': 'test.py',
        'language': 'python',
        'version': 1,
        'text': "import os\nos.walk\n",
        'signal': lsp_signal.sig_response_signal,
        'requires_response': False
    }

    with qtbot.waitSignal(
        lsp_signal.sig_response_signal, timeout=10000) as blocker:
        lsp.perform_request(LSPRequestTypes.DOCUMENT_DID_OPEN, open_params)

    go_to_definition_params = {
        'file': 'test.py',
        'line': 0,
        'column': 19,
        'requires_response': True,
        'response_sig': lsp_signal.sig_response_signal
    }

    with qtbot.waitSignal(
        lsp_signal.sig_response_signal, timeout=10000) as blocker:
        lsp.perform_request(
            LSPRequestTypes.DOCUMENT_DEFINITION, go_to_definition_params)
    _, response = blocker.args
    definition = response['params']
    assert 'os.py' in definition['file']


def test_local_signature(qtbot, lsp_client):
    lsp, lsp_signal = lsp_client
    with qtbot.waitSignal(
        lsp_signal.sig_lsp_notification, timeout=10000):
        lsp.start()
    text = dedent('''
    def test(a, b):
        """Test docstring"""
        pass
    test''')
    open_params = {
        'file': 'test.py',
        'language': 'python',
        'version': 1,
        'text': text,
        'signal': lsp_signal.sig_response_signal,
        'requires_response': False
    }

    with qtbot.waitSignal(
        lsp_signal.sig_response_signal, timeout=10000) as blocker:
        lsp.perform_request(LSPRequestTypes.DOCUMENT_DID_OPEN, open_params)

    signature_params = {
        'file': 'test.py',
        'line': 4,
        'column': 0,
        'requires_response': True,
        'response_sig': lsp_signal.sig_response_signal
    }

    with qtbot.waitSignal(
        lsp_signal.sig_response_signal, timeout=10000) as blocker:
        lsp.perform_request(
            LSPRequestTypes.DOCUMENT_HOVER, signature_params)
    _, response = blocker.args
    definition = response['params']
    assert 'Test docstring' in definition
