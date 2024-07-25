# Copyright 2017-2020 Palantir Technologies, Inc.
# Copyright 2021- Python Language Server Contributors.

import os
from io import StringIO
from unittest.mock import MagicMock

import pytest
from pylsp_jsonrpc.dispatchers import MethodDispatcher
from pylsp_jsonrpc.endpoint import Endpoint
from pylsp_jsonrpc.exceptions import JsonRpcException

from pylsp import uris
from pylsp.config.config import Config
from pylsp.python_lsp import PythonLSPServer
from pylsp.workspace import Document, Workspace
from test.test_utils import CALL_TIMEOUT_IN_SECONDS, ClientServerPair

DOC_URI = uris.from_fs_path(__file__)
DOC = """import sys

def main():
    print sys.stdin.read()
"""


class FakeEditorMethodsMixin:
    """
    Represents the methods to be added to a dispatcher class when faking an editor.
    """

    def m_window__work_done_progress__create(self, *_args, **_kwargs):
        """
        Fake editor method `window/workDoneProgress/create`.

        related spec:
        https://microsoft.github.io/language-server-protocol/specifications/lsp/3.17/specification/#window_workDoneProgress_create
        """
        return None


class FakePythonLSPServer(FakeEditorMethodsMixin, PythonLSPServer):
    pass


class FakeEndpoint(Endpoint):
    """
    Fake Endpoint representing the editor / LSP client.

    The `dispatcher` dict will be used to synchronously calculate the responses
    for calls to `.request` and resolve the futures with the value or errors.

    Fake methods in the `dispatcher` should raise `JsonRpcException` for any
    error.
    """

    def request(self, method, params=None):
        request_future = super().request(method, params)
        try:
            request_future.set_result(self._dispatcher[method](params))
        except JsonRpcException as e:
            request_future.set_exception(e)

        return request_future


@pytest.fixture
def pylsp(tmpdir):
    """Return an initialized python LS"""
    ls = FakePythonLSPServer(StringIO, StringIO, endpoint_cls=FakeEndpoint)

    ls.m_initialize(
        processId=1, rootUri=uris.from_fs_path(str(tmpdir)), initializationOptions={}
    )

    return ls


@pytest.fixture
def pylsp_w_workspace_folders(tmpdir):
    """Return an initialized python LS"""
    ls = FakePythonLSPServer(StringIO, StringIO, endpoint_cls=FakeEndpoint)

    folder1 = tmpdir.mkdir("folder1")
    folder2 = tmpdir.mkdir("folder2")

    ls.m_initialize(
        processId=1,
        rootUri=uris.from_fs_path(str(folder1)),
        initializationOptions={},
        workspaceFolders=[
            {"uri": uris.from_fs_path(str(folder1)), "name": "folder1"},
            {"uri": uris.from_fs_path(str(folder2)), "name": "folder2"},
        ],
    )

    workspace_folders = [folder1, folder2]
    return (ls, workspace_folders)


@pytest.fixture()
def consumer():
    return MagicMock()


@pytest.fixture()
def endpoint(consumer):
    class Dispatcher(FakeEditorMethodsMixin, MethodDispatcher):
        pass

    return FakeEndpoint(Dispatcher(), consumer, id_generator=lambda: "id")


@pytest.fixture
def workspace(tmpdir, endpoint):
    """Return a workspace."""
    ws = Workspace(uris.from_fs_path(str(tmpdir)), endpoint)
    ws._config = Config(ws.root_uri, {}, 0, {})
    yield ws
    ws.close()


@pytest.fixture
def workspace_other_root_path(tmpdir, endpoint):
    """Return a workspace with a root_path other than tmpdir."""
    ws_path = str(tmpdir.mkdir("test123").mkdir("test456"))
    ws = Workspace(uris.from_fs_path(ws_path), endpoint)
    ws._config = Config(ws.root_uri, {}, 0, {})
    return ws


@pytest.fixture
def config(workspace):
    """Return a config object."""
    cfg = Config(workspace.root_uri, {}, 0, {})
    cfg._plugin_settings = {
        "plugins": {"pylint": {"enabled": False, "args": [], "executable": None}}
    }
    return cfg


@pytest.fixture
def doc(workspace):
    return Document(DOC_URI, workspace, DOC)


@pytest.fixture
def temp_workspace_factory(workspace):
    """
    Returns a function that creates a temporary workspace from the files dict.
    The dict is in the format {"file_name": "file_contents"}
    """

    def fn(files):
        def create_file(name, content):
            fn = os.path.join(workspace.root_path, name)
            with open(fn, "w", encoding="utf-8") as f:
                f.write(content)
            workspace.put_document(uris.from_fs_path(fn), content)

        for name, content in files.items():
            create_file(name, content)
        return workspace

    return fn


@pytest.fixture
def client_server_pair():
    """A fixture that sets up a client/server pair and shuts down the server"""
    client_server_pair_obj = ClientServerPair()

    yield (client_server_pair_obj.client, client_server_pair_obj.server)

    shutdown_response = client_server_pair_obj.client._endpoint.request(
        "shutdown"
    ).result(timeout=CALL_TIMEOUT_IN_SECONDS)
    assert shutdown_response is None
    client_server_pair_obj.client._endpoint.notify("exit")
