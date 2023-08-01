# Copyright 2022- Python Language Server Contributors.

from typing import Dict, List
from unittest.mock import Mock

import jedi
import parso
import pytest

from pylsp import lsp, uris
from pylsp.config.config import Config
from pylsp.plugins.rope_autoimport import _get_score, _should_insert, get_names
from pylsp.plugins.rope_autoimport import \
    pylsp_completions as pylsp_autoimport_completions
from pylsp.plugins.rope_autoimport import pylsp_initialize
from pylsp.workspace import Workspace

DOC_URI = uris.from_fs_path(__file__)


@pytest.fixture(scope="session")
def autoimport_workspace(tmp_path_factory) -> Workspace:
    "Special autoimport workspace. Persists across sessions to make in-memory sqlite3 database fast."
    workspace = Workspace(uris.from_fs_path(str(tmp_path_factory.mktemp("pylsp"))), Mock())
    workspace._config = Config(workspace.root_uri, {}, 0, {})
    workspace._config.update({"rope_autoimport": {"memory": True, "enabled": True}})
    pylsp_initialize(workspace._config, workspace)
    yield workspace
    workspace.close()


# pylint: disable=redefined-outer-name
@pytest.fixture
def completions(config: Config, autoimport_workspace: Workspace, request):
    document, position = request.param
    com_position = {"line": 0, "character": position}
    autoimport_workspace.put_document(DOC_URI, source=document)
    doc = autoimport_workspace.get_document(DOC_URI)
    yield pylsp_autoimport_completions(config, autoimport_workspace, doc, com_position)
    autoimport_workspace.rm_document(DOC_URI)


def should_insert(phrase: str, position: int):
    expr = parso.parse(phrase)
    word_node = expr.get_leaf_for_position((1, position))
    return _should_insert(expr, word_node)


def check_dict(query: Dict, results: List[Dict]) -> bool:
    for result in results:
        if all(result[key] == query[key] for key in query.keys()):
            return True
    return False


@pytest.mark.parametrize("completions", [("""pathli """, 6)], indirect=True)
def test_autoimport_completion(completions):
    assert completions
    assert check_dict(
        {
            "label": "pathlib",
            "kind": lsp.CompletionItemKind.Module
        }, completions)


@pytest.mark.parametrize("completions", [("""import """, 7)], indirect=True)
def test_autoimport_import(completions):
    assert len(completions) == 0


@pytest.mark.parametrize("completions", [("""pathlib""", 2)], indirect=True)
def test_autoimport_pathlib(completions):
    assert completions[0]["label"] == "pathlib"

    start = {"line": 0, "character": 0}
    edit_range = {"start": start, "end": start}
    assert completions[0]["additionalTextEdits"] == [{
        "range":
        edit_range,
        "newText":
        "import pathlib\n"
    }]


@pytest.mark.parametrize("completions", [("""import test\n""", 10)],
                         indirect=True)
def test_autoimport_import_with_name(completions):
    assert len(completions) == 0


@pytest.mark.parametrize("completions", [("""def func(s""", 10)],
                         indirect=True)
def test_autoimport_function(completions):

    assert len(completions) == 0


@pytest.mark.parametrize("completions", [("""class Test""", 10)],
                         indirect=True)
def test_autoimport_class(completions):
    assert len(completions) == 0


@pytest.mark.parametrize("completions", [("""\n""", 0)], indirect=True)
def test_autoimport_empty_line(completions):
    assert len(completions) == 0


@pytest.mark.parametrize("completions", [("""class Test(NamedTupl):""", 20)],
                         indirect=True)
def test_autoimport_class_complete(completions):
    assert len(completions) > 0


@pytest.mark.parametrize("completions", [("""class Test(NamedTupl""", 20)],
                         indirect=True)
def test_autoimport_class_incomplete(completions):
    assert len(completions) > 0


@pytest.mark.parametrize("completions", [("""def func(s:Lis""", 12)],
                         indirect=True)
def test_autoimport_function_typing(completions):
    assert len(completions) > 0
    assert check_dict({"label": "List"}, completions)


@pytest.mark.parametrize("completions", [("""def func(s : Lis ):""", 16)],
                         indirect=True)
def test_autoimport_function_typing_complete(completions):
    assert len(completions) > 0
    assert check_dict({"label": "List"}, completions)


@pytest.mark.parametrize("completions",
                         [("""def func(s : Lis ) -> Generat:""", 29)],
                         indirect=True)
def test_autoimport_function_typing_return(completions):
    assert len(completions) > 0
    assert check_dict({"label": "Generator"}, completions)


def test_autoimport_defined_name(config, workspace):
    document = """List = "hi"\nLis"""
    com_position = {"line": 1, "character": 3}
    workspace.put_document(DOC_URI, source=document)
    doc = workspace.get_document(DOC_URI)
    completions = pylsp_autoimport_completions(config, workspace, doc,
                                               com_position)
    workspace.rm_document(DOC_URI)
    assert not check_dict({"label": "List"}, completions)


# This test has several large issues.
# 1. autoimport relies on its sources being written to disk. This makes testing harder
# 2. the hook doesn't handle removed files
# 3. The testing framework cannot access the actual autoimport object so it cannot clear the cache
# def test_autoimport_update_module(config: Config, workspace: Workspace):
#     document2 = "SomethingYouShouldntWrite = 1"
#     document = """SomethingYouShouldntWrit"""
#     com_position = {
#         "line": 0,
#         "character": 3,
#     }
#     doc2_path = workspace.root_path + "/test_file_no_one_should_write_to.py"
#     if os.path.exists(doc2_path):
#         os.remove(doc2_path)
#     DOC2_URI = uris.from_fs_path(doc2_path)
#     workspace.put_document(DOC_URI, source=document)
#     doc = workspace.get_document(DOC_URI)
#     completions = pylsp_autoimport_completions(config, workspace, doc, com_position)
#     assert len(completions) == 0
#     with open(doc2_path, "w") as f:
#         f.write(document2)
#     workspace.put_document(DOC2_URI, source=document2)
#     doc2 = workspace.get_document(DOC2_URI)
#     pylsp_document_did_save(config, workspace, doc2)
#     assert check_dict({"label": "SomethingYouShouldntWrite"}, completions)
#     workspace.put_document(DOC2_URI, source="\n")
#     doc2 = workspace.get_document(DOC2_URI)
#     os.remove(doc2_path)
#     pylsp_document_did_save(config, workspace, doc2)
#     completions = pylsp_autoimport_completions(config, workspace, doc, com_position)
#     assert len(completions) == 0
#     workspace.rm_document(DOC_URI)


class TestShouldInsert:

    def test_dot(self):

        assert not should_insert("""str.""", 4)

    def test_dot_partial(self):

        assert not should_insert("""str.metho\n""", 9)

    def test_comment(self):
        assert not should_insert("""#""", 1)

    def test_comment_indent(self):

        assert not should_insert("""    # """, 5)

    def test_from(self):
        assert not should_insert("""from """, 5)
        assert should_insert("""from """, 4)


def test_sort_sources():
    result1 = _get_score(1, "import pathlib", "pathlib", "pathli")
    result2 = _get_score(2, "import pathlib", "pathlib", "pathli")
    assert result1 < result2


def test_sort_statements():
    result1 = _get_score(2, "from importlib_metadata import pathlib",
                         "pathlib", "pathli")
    result2 = _get_score(2, "import pathlib", "pathlib", "pathli")
    assert result1 > result2


def test_sort_both():
    result1 = _get_score(3, "from importlib_metadata import pathlib",
                         "pathlib", "pathli")
    result2 = _get_score(2, "import pathlib", "pathlib", "pathli")
    assert result1 > result2


def test_get_names():
    source = """
    from a import s as e
    import blah, bleh
    hello = "str"
    a, b = 1, 2
    def someone():
        soemthing
    class sfa:
        sfiosifo
    """
    results = get_names(jedi.Script(code=source))
    assert results == set(
        ["blah", "bleh", "e", "hello", "someone", "sfa", "a", "b"])
