# Copyright 2017-2020 Palantir Technologies, Inc.
# Copyright 2021- Python Language Server Contributors.

import os
from io import StringIO
from unittest.mock import Mock
import pytest

from pylsp import uris
from pylsp.config.config import Config
from pylsp.python_lsp import PythonLSPServer
from pylsp.workspace import Workspace, Document


DOC_URI = uris.from_fs_path(__file__)
DOC = """import sys

def main():
    print sys.stdin.read()
"""


@pytest.fixture
def pylsp(tmpdir):
    """ Return an initialized python LS """
    ls = PythonLSPServer(StringIO, StringIO)

    ls.m_initialize(
        processId=1,
        rootUri=uris.from_fs_path(str(tmpdir)),
        initializationOptions={}
    )

    return ls


@pytest.fixture
def workspace(tmpdir):
    """Return a workspace."""
    ws = Workspace(uris.from_fs_path(str(tmpdir)), Mock())
    ws._config = Config(ws.root_uri, {}, 0, {})
    return ws


@pytest.fixture
def workspace_other_root_path(tmpdir):
    """Return a workspace with a root_path other than tmpdir."""
    ws_path = str(tmpdir.mkdir('test123').mkdir('test456'))
    ws = Workspace(uris.from_fs_path(ws_path), Mock())
    ws._config = Config(ws.root_uri, {}, 0, {})
    return ws


@pytest.fixture
def config(workspace):  # pylint: disable=redefined-outer-name
    """Return a config object."""
    return Config(workspace.root_uri, {}, 0, {})


@pytest.fixture
def doc(workspace):  # pylint: disable=redefined-outer-name
    return Document(DOC_URI, workspace, DOC)


@pytest.fixture
def temp_workspace_factory(workspace):  # pylint: disable=redefined-outer-name
    '''
    Returns a function that creates a temporary workspace from the files dict.
    The dict is in the format {"file_name": "file_contents"}
    '''
    def fn(files):
        def create_file(name, content):
            fn = os.path.join(workspace.root_path, name)
            with open(fn, 'w') as f:
                f.write(content)
            workspace.put_document(uris.from_fs_path(fn), content)

        for name, content in files.items():
            create_file(name, content)
        return workspace

    return fn
