# Copyright 2022- Python Language Server Contributors.

from typing import Any, Dict, List
from unittest.mock import Mock

import jedi
import parso
import pytest

from pylsp import lsp, uris
from pylsp.config.config import Config
from pylsp.plugins.rope_autoimport import (
    _get_score,
    _should_insert,
    get_name_or_module,
    get_names,
)
from pylsp.plugins.rope_autoimport import (
    pylsp_completions as pylsp_autoimport_completions,
)
from pylsp.plugins.rope_autoimport import pylsp_initialize
from pylsp.workspace import Workspace


DOC_URI = uris.from_fs_path(__file__)


def contains_autoimport(suggestion: Dict[str, Any], module: str) -> bool:
    """Checks if `suggestion` contains an autoimport for `module`."""
    return suggestion.get("label", "") == module and "import" in suggestion.get(
        "detail", ""
    )


@pytest.fixture(scope="session")
def autoimport_workspace(tmp_path_factory) -> Workspace:
    "Special autoimport workspace. Persists across sessions to make in-memory sqlite3 database fast."
    workspace = Workspace(
        uris.from_fs_path(str(tmp_path_factory.mktemp("pylsp"))), Mock()
    )
    workspace._config = Config(workspace.root_uri, {}, 0, {})
    workspace._config.update(
        {
            "rope_autoimport": {
                "memory": True,
                "enabled": True,
                "completions": {"enabled": True},
                "code_actions": {"enabled": True},
            }
        }
    )
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
    yield pylsp_autoimport_completions(
        config, autoimport_workspace, doc, com_position, None
    )
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
        {"label": "pathlib", "kind": lsp.CompletionItemKind.Module}, completions
    )


@pytest.mark.parametrize("completions", [("""import """, 7)], indirect=True)
def test_autoimport_import(completions):
    assert len(completions) == 0


@pytest.mark.parametrize("completions", [("""pathlib""", 2)], indirect=True)
def test_autoimport_pathlib(completions):
    assert completions[0]["label"] == "pathlib"

    start = {"line": 0, "character": 0}
    edit_range = {"start": start, "end": start}
    assert completions[0]["additionalTextEdits"] == [
        {"range": edit_range, "newText": "import pathlib\n"}
    ]


@pytest.mark.parametrize("completions", [("""import test\n""", 10)], indirect=True)
def test_autoimport_import_with_name(completions):
    assert len(completions) == 0


@pytest.mark.parametrize("completions", [("""def func(s""", 10)], indirect=True)
def test_autoimport_function(completions):
    assert len(completions) == 0


@pytest.mark.parametrize("completions", [("""class Test""", 10)], indirect=True)
def test_autoimport_class(completions):
    assert len(completions) == 0


@pytest.mark.parametrize("completions", [("""\n""", 0)], indirect=True)
def test_autoimport_empty_line(completions):
    assert len(completions) == 0


@pytest.mark.parametrize(
    "completions", [("""class Test(NamedTupl):""", 20)], indirect=True
)
def test_autoimport_class_complete(completions):
    assert len(completions) > 0


@pytest.mark.parametrize(
    "completions", [("""class Test(NamedTupl""", 20)], indirect=True
)
def test_autoimport_class_incomplete(completions):
    assert len(completions) > 0


@pytest.mark.parametrize("completions", [("""def func(s:Lis""", 12)], indirect=True)
def test_autoimport_function_typing(completions):
    assert len(completions) > 0
    assert check_dict({"label": "List"}, completions)


@pytest.mark.parametrize(
    "completions", [("""def func(s : Lis ):""", 16)], indirect=True
)
def test_autoimport_function_typing_complete(completions):
    assert len(completions) > 0
    assert check_dict({"label": "List"}, completions)


@pytest.mark.parametrize(
    "completions", [("""def func(s : Lis ) -> Generat:""", 29)], indirect=True
)
def test_autoimport_function_typing_return(completions):
    assert len(completions) > 0
    assert check_dict({"label": "Generator"}, completions)


def test_autoimport_defined_name(config, workspace):
    document = """List = "hi"\nLis"""
    com_position = {"line": 1, "character": 3}
    workspace.put_document(DOC_URI, source=document)
    doc = workspace.get_document(DOC_URI)
    completions = pylsp_autoimport_completions(
        config, workspace, doc, com_position, None
    )
    workspace.rm_document(DOC_URI)
    assert not check_dict({"label": "List"}, completions)


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
    result1 = _get_score(
        2, "from importlib_metadata import pathlib", "pathlib", "pathli"
    )
    result2 = _get_score(2, "import pathlib", "pathlib", "pathli")
    assert result1 > result2


def test_sort_both():
    result1 = _get_score(
        3, "from importlib_metadata import pathlib", "pathlib", "pathli"
    )
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
    assert results == set(["blah", "bleh", "e", "hello", "someone", "sfa", "a", "b"])


# Tests ruff, flake8 and pyflakes messages
@pytest.mark.parametrize(
    "message",
    ["Undefined name `os`", "F821 undefined name 'numpy'", "undefined name 'numpy'"],
)
def test_autoimport_code_actions_get_correct_module_name(autoimport_workspace, message):
    source = "os.path.join('a', 'b')"
    autoimport_workspace.put_document(DOC_URI, source=source)
    doc = autoimport_workspace.get_document(DOC_URI)
    diagnostic = {
        "range": {
            "start": {"line": 0, "character": 0},
            "end": {"line": 0, "character": 2},
        },
        "message": message,
    }
    module_name = get_name_or_module(doc, diagnostic)
    autoimport_workspace.rm_document(DOC_URI)
    assert module_name == "os"


# rope autoimport launches a sqlite database which checks from which thread it is called.
# This makes the test below fail because we access the db from a different thread.
# See https://stackoverflow.com/questions/48218065/objects-created-in-a-thread-can-only-be-used-in-that-same-thread
# @pytest.mark.skipif(IS_WIN, reason="Flaky on Windows")
# def test_autoimport_completions_for_notebook_document(
#     client_server_pair,
# ):
#     client, server = client_server_pair
#     send_initialize_request(client)

#     with patch.object(server._endpoint, "notify") as mock_notify:
#         # Expectations:
#         # 1. We receive an autoimport suggestion for "os" in the first cell because
#         #    os is imported after that.
#         # 2. We don't receive an autoimport suggestion for "os" in the second cell because it's
#         #    already imported in the second cell.
#         # 3. We don't receive an autoimport suggestion for "os" in the third cell because it's
#         #    already imported in the second cell.
#         # 4. We receive an autoimport suggestion for "sys" because it's not already imported
#         send_notebook_did_open(client, ["os", "import os\nos", "os", "sys"])
#         wait_for_condition(lambda: mock_notify.call_count >= 3)

#     server.m_workspace__did_change_configuration(
#         settings={
#             "pylsp": {
#                 "plugins": {
#                     "rope_autoimport": {
#                         "memory": True,
#                         "completions": {"enabled": True},
#                     },
#                 }
#             }
#         }
#     )
#     rope_autoimport_settings = server.workspace._config.plugin_settings(
#         "rope_autoimport"
#     )
#     assert rope_autoimport_settings.get("completions", {}).get("enabled", False) is True
#     assert rope_autoimport_settings.get("memory", False) is True

#     # 1.
#     suggestions = server.completions("cell_1_uri", {"line": 0, "character": 2}).get(
#         "items"
#     )
#     assert any(
#         suggestion
#         for suggestion in suggestions
#         if contains_autoimport(suggestion, "os")
#     )

#     # 2.
#     suggestions = server.completions("cell_2_uri", {"line": 1, "character": 2}).get(
#         "items"
#     )
#     assert not any(
#         suggestion
#         for suggestion in suggestions
#         if contains_autoimport(suggestion, "os")
#     )

#     # 3.
#     suggestions = server.completions("cell_3_uri", {"line": 0, "character": 2}).get(
#         "items"
#     )
#     assert not any(
#         suggestion
#         for suggestion in suggestions
#         if contains_autoimport(suggestion, "os")
#     )

#     # 4.
#     suggestions = server.completions("cell_4_uri", {"line": 0, "character": 3}).get(
#         "items"
#     )
#     assert any(
#         suggestion
#         for suggestion in suggestions
#         if contains_autoimport(suggestion, "sys")
#     )
