# Copyright 2017 Palantir Technologies, Inc.
import sys
from mock import Mock
import pytest

from pyls import uris
from pyls.config.config import Config
from pyls.python_ls import PythonLanguageServer
from pyls.workspace import Workspace, Document

if sys.version_info[0] < 3:
    from StringIO import StringIO
else:
    from io import StringIO

DOC_URI = uris.from_fs_path(__file__)
DOC = """import sys

def main():
    print sys.stdin.read()
"""


@pytest.fixture
def pyls(tmpdir):
    """ Return an initialized python LS """
    ls = PythonLanguageServer(StringIO, StringIO)

    ls.m_initialize(
        processId=1,
        rootUri=uris.from_fs_path(str(tmpdir)),
        initializationOptions={}
    )

    return ls


@pytest.fixture
def workspace(tmpdir):
    """Return a workspace."""
    return Workspace(uris.from_fs_path(str(tmpdir)), Mock())


@pytest.fixture
def config(workspace):  # pylint: disable=redefined-outer-name
    """Return a config object."""
    return Config(workspace.root_uri, {}, 0, {})


@pytest.fixture
def doc():
    return Document(DOC_URI, DOC)
