# -*- coding: utf-8 -*-

# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

import os
from textwrap import dedent

import pytest
from qtpy.QtCore import QObject, Signal, Slot

from spyder.plugins.completion.api import (
    CompletionRequestTypes, WorkspaceUpdateKind)


class CompletionManager(QObject):
    """Dummy completion plugin that can handle LSP responses."""
    sig_response = Signal(str, dict)

    @Slot(str, dict)
    def handle_response(self, method, params):
        self.sig_response.emit(method, params)


@pytest.fixture(scope='module', params=[
    pytest.lazy_fixture('lsp_provider'),
    pytest.lazy_fixture('lsp_stdio_provider')])
def lsp_client_and_completion(request):
    """Create an LSP client/completion pair."""
    completion = CompletionManager()
    client = request.param.clients['python']['instance']
    return client, completion


@pytest.mark.order(3)
def test_didOpen(lsp_client_and_completion, qtbot):
    client, completion = lsp_client_and_completion

    # Parameters to perform a textDocument/didOpen request
    params = {
        'file': 'test.py',
        'language': 'python',
        'version': 1,
        'text': "",
        'response_callback': completion.handle_response,
        'codeeditor': completion,
        'requires_response': False
    }

    # Wait for the client to be started
    with qtbot.waitSignal(completion.sig_response, timeout=30000) as blocker:
        client.perform_request(CompletionRequestTypes.DOCUMENT_DID_OPEN,
                               params)
    response, _ = blocker.args

    # Assert the response has what we expect
    assert response == 'textDocument/publishDiagnostics'


@pytest.mark.order(3)
def test_get_signature(lsp_client_and_completion, qtbot):
    client, completion = lsp_client_and_completion

    # Parameters to perform a textDocument/didChange request
    params = {
        'file': 'test.py',
        'language': 'python',
        'version': 1,
        'text': "import os\nos.walk(\n",
        'codeeditor': completion,
        'requires_response': False
    }

    # Perform the request
    with qtbot.waitSignal(completion.sig_response, timeout=30000):
        client.perform_request(CompletionRequestTypes.DOCUMENT_DID_CHANGE,
                               params)

    # Parameters to perform a textDocument/signatureHelp request
    signature_params = {
        'file': 'test.py',
        'line': 1,
        'column': 10,
        'requires_response': True,
        'response_callback': completion.handle_response
    }

    # Perform the request
    with qtbot.waitSignal(completion.sig_response, timeout=30000) as blocker:
        client.perform_request(CompletionRequestTypes.DOCUMENT_SIGNATURE,
                               signature_params)
    _, response = blocker.args

    # Assert the response has what we expect
    assert response['params']['signatures']['label'].startswith('walk')


@pytest.mark.order(3)
def test_get_completions(lsp_client_and_completion, qtbot):
    client, completion = lsp_client_and_completion

    # Parameters to perform a textDocument/didChange request
    params = {
        'file': 'test.py',
        'language': 'python',
        'version': 1,
        'text': "import o",
        'codeeditor': completion,
        'requires_response': False
    }

    # Perform the request
    with qtbot.waitSignal(completion.sig_response, timeout=30000):
        client.perform_request(CompletionRequestTypes.DOCUMENT_DID_CHANGE,
                               params)

    # Parameters to perform a textDocument/completion request
    completion_params = {
        'file': 'test.py',
        'line': 0,
        'column': 8,
        'requires_response': True,
        'response_callback': completion.handle_response
    }

    # Perform the request
    with qtbot.waitSignal(completion.sig_response, timeout=30000) as blocker:
        client.perform_request(CompletionRequestTypes.DOCUMENT_COMPLETION,
                               completion_params)
    _, response = blocker.args

    # Assert the response has what we expect
    completions = response['params']
    assert 'os' in [x['label'] for x in completions]


@pytest.mark.order(3)
def test_go_to_definition(lsp_client_and_completion, qtbot):
    client, completion = lsp_client_and_completion

    # Parameters to perform a textDocument/didChange request
    params = {
        'file': 'test.py',
        'language': 'python',
        'version': 1,
        'text': "import os\nos.walk\n",
        'codeeditor': completion,
        'requires_response': False
    }

    # Perform the request
    with qtbot.waitSignal(completion.sig_response, timeout=30000):
        client.perform_request(CompletionRequestTypes.DOCUMENT_DID_CHANGE,
                               params)

    # Parameters to perform a textDocument/definition request
    go_to_definition_params = {
        'file': 'test.py',
        'line': 0,
        'column': 19,
        'requires_response': True,
        'response_callback': completion.handle_response
    }

    # Perform the request
    with qtbot.waitSignal(completion.sig_response, timeout=30000) as blocker:
        client.perform_request(CompletionRequestTypes.DOCUMENT_DEFINITION,
                               go_to_definition_params)
    _, response = blocker.args

    # Assert the response has what we expect
    definition = response['params']
    assert 'os.py' in definition['file']


@pytest.mark.order(3)
def test_local_signature(lsp_client_and_completion, qtbot):
    client, completion = lsp_client_and_completion

    # Parameters to perform a textDocument/didOpen request
    text = dedent('''
    def test(a, b):
        """Test docstring"""
        pass
    test''')
    params = {
        'file': 'test.py',
        'language': 'python',
        'version': 1,
        'text': text,
        'codeeditor': completion,
        'requires_response': False
    }

    # Perform the request
    with qtbot.waitSignal(completion.sig_response, timeout=30000) as blocker:
        client.perform_request(CompletionRequestTypes.DOCUMENT_DID_CHANGE,
                               params)

    # Parameters to perform a textDocument/hover request
    signature_params = {
        'file': 'test.py',
        'line': 4,
        'column': 0,
        'requires_response': True,
        'response_callback': completion.handle_response
    }

    # Perform the request
    with qtbot.waitSignal(completion.sig_response, timeout=30000) as blocker:
        client.perform_request(CompletionRequestTypes.DOCUMENT_HOVER,
                               signature_params)
    _, response = blocker.args

    # Assert the response has what we expect
    definition = response['params']
    assert 'Test docstring' in definition


@pytest.mark.order(3)
def test_send_workspace_folders_change(lsp_client_and_completion, qtbot):
    client, completion = lsp_client_and_completion
    folder = '/tmp/'

    # Test addition
    params = {
        'folder': folder,
        'kind': WorkspaceUpdateKind.ADDITION,
        'instance': ''
    }

    client.send_workspace_folders_change(params)
    assert folder in client.watched_folders

    # Test deletion
    params = {
        'folder': folder,
        'kind': WorkspaceUpdateKind.DELETION,
        'instance': ''
    }

    client.send_workspace_folders_change(params)
    assert folder not in client.watched_folders
