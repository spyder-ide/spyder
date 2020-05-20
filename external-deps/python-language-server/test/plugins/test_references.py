# Copyright 2017 Palantir Technologies, Inc.
import os
import pytest
from pyls import uris
from pyls.workspace import Document
from pyls.plugins.references import pyls_references


DOC1_NAME = 'test1.py'
DOC2_NAME = 'test2.py'

DOC1 = """class Test1():
    pass
"""

DOC2 = """from test1 import Test1

try:
    Test1()
except UnicodeError:
    pass
"""


@pytest.fixture
def tmp_workspace(workspace):
    def create_file(name, content):
        fn = os.path.join(workspace.root_path, name)
        with open(fn, 'w') as f:
            f.write(content)
        workspace.put_document(uris.from_fs_path(fn), content)

    create_file(DOC1_NAME, DOC1)
    create_file(DOC2_NAME, DOC2)

    return workspace


def test_references(tmp_workspace):  # pylint: disable=redefined-outer-name
    # Over 'Test1' in class Test1():
    position = {'line': 0, 'character': 8}
    DOC1_URI = uris.from_fs_path(os.path.join(tmp_workspace.root_path, DOC1_NAME))
    doc1 = Document(DOC1_URI)

    refs = pyls_references(doc1, position)

    # Definition, the import and the instantiation
    assert len(refs) == 3

    # Briefly check excluding the definitions (also excludes imports, only counts uses)
    no_def_refs = pyls_references(doc1, position, exclude_declaration=True)
    assert len(no_def_refs) == 1

    # Make sure our definition is correctly located
    doc1_ref = [u for u in refs if u['uri'] == DOC1_URI][0]
    assert doc1_ref['range']['start'] == {'line': 0, 'character': 6}
    assert doc1_ref['range']['end'] == {'line': 0, 'character': 11}

    # Make sure our import is correctly located
    doc2_import_ref = [u for u in refs if u['uri'] != DOC1_URI][0]
    assert doc2_import_ref['range']['start'] == {'line': 0, 'character': 18}
    assert doc2_import_ref['range']['end'] == {'line': 0, 'character': 23}

    doc2_usage_ref = [u for u in refs if u['uri'] != DOC1_URI][1]
    assert doc2_usage_ref['range']['start'] == {'line': 3, 'character': 4}
    assert doc2_usage_ref['range']['end'] == {'line': 3, 'character': 9}


def test_references_builtin(tmp_workspace):  # pylint: disable=redefined-outer-name
    # Over 'UnicodeError':
    position = {'line': 4, 'character': 7}
    doc2_uri = uris.from_fs_path(os.path.join(tmp_workspace.root_path, DOC2_NAME))
    doc2 = Document(doc2_uri)

    refs = pyls_references(doc2, position)
    assert len(refs) >= 1

    assert refs[0]['range']['start'] == {'line': 4, 'character': 7}
    assert refs[0]['range']['end'] == {'line': 4, 'character': 19}
