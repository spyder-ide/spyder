# Copyright 2017 Palantir Technologies, Inc.
import os
import time
import multiprocessing
from threading import Thread

from test import unix_only
from pyls_jsonrpc.exceptions import JsonRpcMethodNotFound
import pytest

from pyls.python_ls import start_io_lang_server, PythonLanguageServer

CALL_TIMEOUT = 10


def start_client(client):
    client.start()


class _ClientServer(object):
    """ A class to setup a client/server pair """
    def __init__(self, check_parent_process=False):
        # Client to Server pipe
        csr, csw = os.pipe()
        # Server to client pipe
        scr, scw = os.pipe()

        ParallelKind = multiprocessing.Process if os.name != 'nt' else Thread

        self.process = ParallelKind(target=start_io_lang_server, args=(
            os.fdopen(csr, 'rb'), os.fdopen(scw, 'wb'), check_parent_process, PythonLanguageServer
        ))
        self.process.start()

        self.client = PythonLanguageServer(os.fdopen(scr, 'rb'), os.fdopen(csw, 'wb'), start_io_lang_server)
        self.client_thread = Thread(target=start_client, args=[self.client])
        self.client_thread.daemon = True
        self.client_thread.start()


@pytest.fixture
def client_server():
    """ A fixture that sets up a client/server pair and shuts down the server
    This client/server pair does not support checking parent process aliveness
    """
    client_server_pair = _ClientServer()

    yield client_server_pair.client

    shutdown_response = client_server_pair.client._endpoint.request('shutdown').result(timeout=CALL_TIMEOUT)
    assert shutdown_response is None
    client_server_pair.client._endpoint.notify('exit')


@pytest.fixture
def client_exited_server():
    """ A fixture that sets up a client/server pair that support checking parent process aliveness
    and assert the server has already exited
    """
    client_server_pair = _ClientServer(True)

    # yield client_server_pair.client
    yield client_server_pair

    assert client_server_pair.process.is_alive() is False


def test_initialize(client_server):  # pylint: disable=redefined-outer-name
    response = client_server._endpoint.request('initialize', {
        'rootPath': os.path.dirname(__file__),
        'initializationOptions': {}
    }).result(timeout=CALL_TIMEOUT)
    assert 'capabilities' in response


@unix_only
def test_exit_with_parent_process_died(client_exited_server):  # pylint: disable=redefined-outer-name
    # language server should have already exited before responding
    lsp_server, mock_process = client_exited_server.client, client_exited_server.process
    # with pytest.raises(Exception):
    lsp_server._endpoint.request('initialize', {
        'processId': mock_process.pid,
        'rootPath': os.path.dirname(__file__),
        'initializationOptions': {}
    }).result(timeout=CALL_TIMEOUT)

    mock_process.terminate()
    time.sleep(CALL_TIMEOUT)
    assert not client_exited_server.client_thread.is_alive()


def test_not_exit_without_check_parent_process_flag(client_server):  # pylint: disable=redefined-outer-name
    response = client_server._endpoint.request('initialize', {
        'processId': 1234,
        'rootPath': os.path.dirname(__file__),
        'initializationOptions': {}
    }).result(timeout=CALL_TIMEOUT)
    assert 'capabilities' in response


def test_missing_message(client_server):  # pylint: disable=redefined-outer-name
    with pytest.raises(JsonRpcMethodNotFound):
        client_server._endpoint.request('unknown_method').result(timeout=CALL_TIMEOUT)
