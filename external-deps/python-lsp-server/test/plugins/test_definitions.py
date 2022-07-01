# Copyright 2017-2020 Palantir Technologies, Inc.
# Copyright 2021- Python Language Server Contributors.

import os

from pylsp import uris
from pylsp.plugins.definition import pylsp_definitions
from pylsp.workspace import Document


DOC_URI = uris.from_fs_path(__file__)
DOC = """def a():
    pass

print a()


class Directory(object):
    def __init__(self):
        self.members = dict()

    def add_member(self, id, name):
        self.members[id] = name
"""


def test_definitions(config, workspace):
    # Over 'a' in print a
    cursor_pos = {'line': 3, 'character': 6}

    # The definition of 'a'
    def_range = {
        'start': {'line': 0, 'character': 4},
        'end': {'line': 0, 'character': 5}
    }

    doc = Document(DOC_URI, workspace, DOC)
    assert [{'uri': DOC_URI, 'range': def_range}] == pylsp_definitions(config, doc, cursor_pos)


def test_builtin_definition(config, workspace):
    # Over 'i' in dict
    cursor_pos = {'line': 8, 'character': 24}

    # No go-to def for builtins
    doc = Document(DOC_URI, workspace, DOC)
    assert not pylsp_definitions(config, doc, cursor_pos)


def test_assignment(config, workspace):
    # Over 's' in self.members[id]
    cursor_pos = {'line': 11, 'character': 19}

    # The assignment of 'self.members'
    def_range = {
        'start': {'line': 8, 'character': 13},
        'end': {'line': 8, 'character': 20}
    }

    doc = Document(DOC_URI, workspace, DOC)
    assert [{'uri': DOC_URI, 'range': def_range}] == pylsp_definitions(config, doc, cursor_pos)


def test_document_path_definitions(config, workspace_other_root_path, tmpdir):
    # Create a dummy module out of the workspace's root_path and try to get
    # a definition on it in another file placed next to it.
    module_content = '''
def foo():
    pass
'''

    p = tmpdir.join("mymodule.py")
    p.write(module_content)

    # Content of doc to test definition
    doc_content = """from mymodule import foo"""
    doc_path = str(tmpdir) + os.path.sep + 'myfile.py'
    doc_uri = uris.from_fs_path(doc_path)
    doc = Document(doc_uri, workspace_other_root_path, doc_content)

    # The range where is defined in mymodule.py
    def_range = {
        'start': {'line': 1, 'character': 4},
        'end': {'line': 1, 'character': 7}
    }

    # The position where foo is called in myfile.py
    cursor_pos = {'line': 0, 'character': 24}

    # The uri for mymodule.py
    module_path = str(p)
    module_uri = uris.from_fs_path(module_path)

    assert [{'uri': module_uri, 'range': def_range}] == pylsp_definitions(config, doc, cursor_pos)
