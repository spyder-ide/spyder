# Copyright 2017-2020 Palantir Technologies, Inc.
# Copyright 2021- Python Language Server Contributors.

import os
import time
import multiprocessing
import sys
from threading import Thread

from pylsp_jsonrpc.exceptions import JsonRpcMethodNotFound
import pytest

from pylsp.python_lsp import start_io_lang_server, PythonLSPServer

CALL_TIMEOUT = 10
PY2 = sys.version_info[0] == 2
PY3 = sys.version_info[0] == 3


def start_client(client):
    client.start()


class _ClientServer:
    """ A class to setup a client/server pair """
    def __init__(self, check_parent_process=False):
        # Client to Server pipe
        csr, csw = os.pipe()
        # Server to client pipe
        scr, scw = os.pipe()

        if os.name == 'nt':
            ParallelKind = Thread
        else:
            if sys.version_info[:2] >= (3, 8):
                ParallelKind = multiprocessing.get_context("fork").Process
            else:
                ParallelKind = multiprocessing.Process

        self.process = ParallelKind(target=start_io_lang_server, args=(
            os.fdopen(csr, 'rb'), os.fdopen(scw, 'wb'), check_parent_process, PythonLSPServer
        ))
        self.process.start()

        self.client = PythonLSPServer(os.fdopen(scr, 'rb'), os.fdopen(csw, 'wb'), start_io_lang_server)
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


@pytest.mark.skipif(os.name == 'nt' or (sys.platform.startswith('linux') and PY3),
                    reason='Skipped on win and fails on linux >=3.6')
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


@pytest.mark.skipif(sys.platform.startswith('linux') and PY3,
                    reason='Fails on linux and py3')
def test_not_exit_without_check_parent_process_flag(client_server):  # pylint: disable=redefined-outer-name
    response = client_server._endpoint.request('initialize', {
        'processId': 1234,
        'rootPath': os.path.dirname(__file__),
        'initializationOptions': {}
    }).result(timeout=CALL_TIMEOUT)
    assert 'capabilities' in response


@pytest.mark.skipif(bool(os.environ.get('CI')), reason='This test is hanging on CI')
def test_missing_message(client_server):  # pylint: disable=redefined-outer-name
    with pytest.raises(JsonRpcMethodNotFound):
        client_server._endpoint.request('unknown_method').result(timeout=CALL_TIMEOUT)
