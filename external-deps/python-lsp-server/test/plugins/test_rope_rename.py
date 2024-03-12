# Copyright 2017-2020 Palantir Technologies, Inc.
# Copyright 2021- Python Language Server Contributors.

import os

import pytest

from pylsp import uris
from pylsp.plugins.rope_rename import pylsp_rename
from pylsp.workspace import Document

DOC_NAME = "test1.py"
DOC = """class Test1():
    pass

class Test2(Test1):
    pass
"""

DOC_NAME_SIMPLE = "test2.py"
DOC_SIMPLE = "foo = 12"


@pytest.fixture
def tmp_workspace(temp_workspace_factory):
    return temp_workspace_factory({DOC_NAME: DOC, DOC_NAME_SIMPLE: DOC_SIMPLE})


def test_rope_rename(tmp_workspace, config):
    position = {"line": 0, "character": 6}
    DOC_URI = uris.from_fs_path(os.path.join(tmp_workspace.root_path, DOC_NAME))
    doc = Document(DOC_URI, tmp_workspace)

    result = pylsp_rename(config, tmp_workspace, doc, position, "ShouldBeRenamed")
    assert len(result.keys()) == 1

    changes = result.get("documentChanges")
    assert len(changes) == 1
    changes = changes[0]

    # Note that this test differs from test_jedi_rename, because rope does not
    # seem to modify files that haven't been opened with textDocument/didOpen.
    assert changes.get("edits") == [
        {
            "range": {
                "start": {"line": 0, "character": 0},
                "end": {"line": 5, "character": 0},
            },
            "newText": "class ShouldBeRenamed():\n    pass\n\nclass Test2(ShouldBeRenamed):\n    pass\n",
        }
    ]

    # Regression test for issue python-lsp/python-lsp-server#413
    # rename foo
    position = {"line": 0, "character": 0}
    DOC_URI = uris.from_fs_path(os.path.join(tmp_workspace.root_path, DOC_NAME_SIMPLE))
    doc = Document(DOC_URI, tmp_workspace)

    result = pylsp_rename(config, tmp_workspace, doc, position, "bar")
    assert len(result.keys()) == 1

    changes = result.get("documentChanges")
    assert len(changes) == 1

    assert changes[0].get("edits") == [
        {
            "range": {
                "start": {"line": 0, "character": 0},
                "end": {"line": 0, "character": 0},
            },
            "newText": "bar = 12",
        }
    ]
