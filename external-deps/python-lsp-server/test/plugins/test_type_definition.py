# Copyright 2021- Python Language Server Contributors.

from pylsp import uris
from pylsp.plugins.type_definition import pylsp_type_definition
from pylsp.workspace import Document

DOC_URI = uris.from_fs_path(__file__)
DOC = """\
from dataclasses import dataclass

@dataclass
class IntPair:
    a: int
    b: int

def main() -> None:
    l0 = list(1, 2)

    my_pair = IntPair(a=10, b=20)
    print(f"Original pair: {my_pair}")
"""


def test_type_definitions(config, workspace) -> None:
    # Over 'IntPair' in 'main'
    cursor_pos = {"line": 10, "character": 14}

    # The definition of 'IntPair'
    def_range = {
        "start": {"line": 3, "character": 6},
        "end": {"line": 3, "character": 13},
    }

    doc = Document(DOC_URI, workspace, DOC)
    assert [{"uri": DOC_URI, "range": def_range}] == pylsp_type_definition(
        config, doc, cursor_pos
    )


def test_builtin_definition(config, workspace) -> None:
    # Over 'list' in main
    cursor_pos = {"line": 8, "character": 9}

    doc = Document(DOC_URI, workspace, DOC)

    defns = pylsp_type_definition(config, doc, cursor_pos)
    assert len(defns) == 1
    assert defns[0]["uri"].endswith("builtins.pyi")


def test_mutli_file_type_definitions(config, workspace, tmpdir) -> None:
    # Create a dummy module out of the workspace's root_path and try to get
    # a definition on it in another file placed next to it.
    module_content = """\
from dataclasses import dataclass

@dataclass
class IntPair:
    a: int
    b: int
"""
    p1 = tmpdir.join("intpair.py")
    p1.write(module_content)
    # The uri for intpair.py
    module_path = str(p1)
    module_uri = uris.from_fs_path(module_path)

    # Content of doc to test type definition
    doc_content = """\
from intpair import IntPair

def main() -> None:
    l0 = list(1, 2)

    my_pair = IntPair(a=10, b=20)
    print(f"Original pair: {my_pair}")
"""
    p2 = tmpdir.join("main.py")
    p2.write(doc_content)
    doc_path = str(p2)
    doc_uri = uris.from_fs_path(doc_path)

    doc = Document(doc_uri, workspace, doc_content)

    # The range where IntPair is defined in intpair.py
    def_range = {
        "start": {"line": 3, "character": 6},
        "end": {"line": 3, "character": 13},
    }

    # The position where IntPair is called in main.py
    cursor_pos = {"line": 5, "character": 14}

    assert [{"uri": module_uri, "range": def_range}] == pylsp_type_definition(
        config, doc, cursor_pos
    )
