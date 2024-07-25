# Copyright 2017-2020 Palantir Technologies, Inc.
# Copyright 2021- Python Language Server Contributors.

import os
import sys
import time

import pytest
from flaky import flaky
from pylsp_jsonrpc.exceptions import JsonRpcMethodNotFound

from test.test_utils import ClientServerPair, send_initialize_request

RUNNING_IN_CI = bool(os.environ.get("CI"))

CALL_TIMEOUT_IN_SECONDS = 10


@pytest.fixture
def client_exited_server():
    """A fixture that sets up a client/server pair that support checking parent process aliveness
    and assert the server has already exited
    """
    client_server_pair_obj = ClientServerPair(True, True)

    yield client_server_pair_obj

    assert client_server_pair_obj.server_process.is_alive() is False


@flaky(max_runs=10, min_passes=1)
@pytest.mark.skipif(sys.platform == "darwin", reason="Too flaky on Mac")
def test_initialize(client_server_pair):
    client, _ = client_server_pair
    response = client._endpoint.request(
        "initialize",
        {"rootPath": os.path.dirname(__file__), "initializationOptions": {}},
    ).result(timeout=CALL_TIMEOUT_IN_SECONDS)
    assert "capabilities" in response


@flaky(max_runs=10, min_passes=1)
@pytest.mark.skipif(
    not sys.platform.startswith("Linux"), reason="Skipped on win and flaky on mac"
)
def test_exit_with_parent_process_died(
    client_exited_server,
):
    # language server should have already exited before responding
    lsp_server, mock_process = (
        client_exited_server.client,
        client_exited_server.server_process,
    )
    # with pytest.raises(Exception):
    lsp_server._endpoint.request(
        "initialize",
        {
            "processId": mock_process.pid,
            "rootPath": os.path.dirname(__file__),
            "initializationOptions": {},
        },
    ).result(timeout=CALL_TIMEOUT_IN_SECONDS)

    mock_process.terminate()
    time.sleep(CALL_TIMEOUT_IN_SECONDS)
    assert not client_exited_server.client_thread.is_alive()


@flaky(max_runs=10, min_passes=1)
@pytest.mark.skipif(sys.platform.startswith("linux"), reason="Fails on linux")
def test_not_exit_without_check_parent_process_flag(
    client_server_pair,
):
    client, _ = client_server_pair
    response = send_initialize_request(client)
    assert "capabilities" in response


@flaky(max_runs=10, min_passes=1)
@pytest.mark.skipif(RUNNING_IN_CI, reason="This test is hanging on CI")
def test_missing_message(client_server_pair):
    client, _ = client_server_pair
    with pytest.raises(JsonRpcMethodNotFound):
        client._endpoint.request("unknown_method").result(
            timeout=CALL_TIMEOUT_IN_SECONDS
        )
