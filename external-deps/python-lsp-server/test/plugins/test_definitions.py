# Copyright 2017-2020 Palantir Technologies, Inc.
# Copyright 2021- Python Language Server Contributors.

import os

from pylsp import uris
from pylsp.plugins.definition import pylsp_definitions
from pylsp.workspace import Document

DOC_URI = uris.from_fs_path(__file__)
DOC = """def a():
    pass

print(a())


class Directory(object):
    def __init__(self):
        self.members = dict()

    def add_member(self, id, name):
        self.members[id] = name


subscripted_before_reference = {}
subscripted_before_reference[0] = 0
subscripted_before_reference


def my_func():
    print('called')

alias = my_func
my_list = [1, None, alias]
inception = my_list[2]

inception()

import numpy
numpy.ones
"""


def test_definitions(config, workspace):
    # Over 'a' in print a
    cursor_pos = {"line": 3, "character": 6}

    # The definition of 'a'
    def_range = {
        "start": {"line": 0, "character": 4},
        "end": {"line": 0, "character": 5},
    }

    doc = Document(DOC_URI, workspace, DOC)
    assert [{"uri": DOC_URI, "range": def_range}] == pylsp_definitions(
        config, doc, cursor_pos
    )


def test_indirect_definitions(config, workspace):
    # Over 'subscripted_before_reference'
    cursor_pos = {"line": 16, "character": 0}

    # The definition of 'subscripted_before_reference',
    # skipping intermediate writes to the most recent definition
    def_range = {
        "start": {"line": 14, "character": 0},
        "end": {"line": 14, "character": len("subscripted_before_reference")},
    }

    doc = Document(DOC_URI, workspace, DOC)
    assert [{"uri": DOC_URI, "range": def_range}] == pylsp_definitions(
        config, doc, cursor_pos
    )


def test_definition_with_multihop_inference_goto(config, workspace):
    # Over 'inception()'
    cursor_pos = {"line": 26, "character": 0}

    # The most recent definition of 'inception',
    # ignoring alias hops
    def_range = {
        "start": {"line": 24, "character": 0},
        "end": {"line": 24, "character": len("inception")},
    }

    doc = Document(DOC_URI, workspace, DOC)
    assert [{"uri": DOC_URI, "range": def_range}] == pylsp_definitions(
        config, doc, cursor_pos
    )


def test_numpy_definition(config, workspace):
    # Over numpy.ones
    cursor_pos = {"line": 29, "character": 8}

    doc = Document(DOC_URI, workspace, DOC)
    defns = pylsp_definitions(config, doc, cursor_pos)
    assert len(defns) > 0, defns


def test_builtin_definition(config, workspace):
    # Over 'i' in dict
    cursor_pos = {"line": 8, "character": 24}

    doc = Document(DOC_URI, workspace, DOC)
    orig_settings = config.settings()

    # Check definition for `dict` goes to `builtins.pyi::dict`
    follow_defns_setting = {"follow_builtin_definitions": True}
    settings = {"plugins": {"jedi_definition": follow_defns_setting}}
    config.update(settings)
    defns = pylsp_definitions(config, doc, cursor_pos)
    assert len(defns) == 1
    assert defns[0]["uri"].endswith("builtins.pyi")

    # Check no definitions for `dict`
    follow_defns_setting["follow_builtin_definitions"] = False
    config.update(settings)
    defns = pylsp_definitions(config, doc, cursor_pos)
    assert not defns

    config.update(orig_settings)


def test_assignment(config, workspace):
    # Over 's' in self.members[id]
    cursor_pos = {"line": 11, "character": 19}

    # The assignment of 'self.members'
    def_range = {
        "start": {"line": 8, "character": 13},
        "end": {"line": 8, "character": 20},
    }

    doc = Document(DOC_URI, workspace, DOC)
    assert [{"uri": DOC_URI, "range": def_range}] == pylsp_definitions(
        config, doc, cursor_pos
    )


def test_document_path_definitions(config, workspace_other_root_path, tmpdir):
    # Create a dummy module out of the workspace's root_path and try to get
    # a definition on it in another file placed next to it.
    module_content = """
def foo():
    pass
"""

    p = tmpdir.join("mymodule.py")
    p.write(module_content)

    # Content of doc to test definition
    doc_content = """from mymodule import foo"""
    doc_path = str(tmpdir) + os.path.sep + "myfile.py"
    doc_uri = uris.from_fs_path(doc_path)
    doc = Document(doc_uri, workspace_other_root_path, doc_content)

    # The range where is defined in mymodule.py
    def_range = {
        "start": {"line": 1, "character": 4},
        "end": {"line": 1, "character": 7},
    }

    # The position where foo is called in myfile.py
    cursor_pos = {"line": 0, "character": 24}

    # The uri for mymodule.py
    module_path = str(p)
    module_uri = uris.from_fs_path(module_path)

    assert [{"uri": module_uri, "range": def_range}] == pylsp_definitions(
        config, doc, cursor_pos
    )
