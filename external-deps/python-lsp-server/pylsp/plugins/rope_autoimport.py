# Copyright 2022- Python Language Server Contributors.

import logging
import threading
from typing import Any, Dict, Generator, List, Optional, Set, Union

import parso
from jedi import Script
from parso.python import tree
from parso.tree import NodeOrLeaf
from rope.base.resources import Resource
from rope.contrib.autoimport.defs import SearchResult
from rope.contrib.autoimport.sqlite import AutoImport

from pylsp import hookimpl
from pylsp.config.config import Config
from pylsp.workspace import Document, Workspace

from ._rope_task_handle import PylspTaskHandle

log = logging.getLogger(__name__)

_score_pow = 5
_score_max = 10**_score_pow
MAX_RESULTS_COMPLETIONS = 1000
MAX_RESULTS_CODE_ACTIONS = 5


class AutoimportCache:
    """Handles the cache creation."""

    def __init__(self):
        self.thread = None

    def reload_cache(
        self,
        config: Config,
        workspace: Workspace,
        files: Optional[List[Document]] = None,
        single_thread: Optional[bool] = False,
    ):
        if self.is_blocked():
            return

        memory: bool = config.plugin_settings("rope_autoimport").get("memory", False)
        rope_config = config.settings().get("rope", {})
        autoimport = workspace._rope_autoimport(rope_config, memory)
        resources: Optional[List[Resource]] = (
            None
            if files is None
            else [document._rope_resource(rope_config) for document in files]
        )

        if single_thread:
            self._reload_cache(workspace, autoimport, resources)
        else:
            # Creating the cache may take 10-20s for a environment with 5k python modules. That's
            # why we decided to move cache creation into its own thread.
            self.thread = threading.Thread(
                target=self._reload_cache, args=(workspace, autoimport, resources)
            )
            self.thread.start()

    def _reload_cache(
        self,
        workspace: Workspace,
        autoimport: AutoImport,
        resources: Optional[List[Resource]] = None,
    ):
        task_handle = PylspTaskHandle(workspace)
        autoimport.generate_cache(task_handle=task_handle, resources=resources)
        autoimport.generate_modules_cache(task_handle=task_handle)

    def is_blocked(self):
        return self.thread and self.thread.is_alive()


@hookimpl
def pylsp_settings() -> Dict[str, Dict[str, Dict[str, Any]]]:
    # Default rope_completion to disabled
    return {
        "plugins": {
            "rope_autoimport": {
                "enabled": False,
                "memory": False,
                "completions": {
                    "enabled": True,
                },
                "code_actions": {
                    "enabled": True,
                },
            }
        }
    }


def _should_insert(expr: tree.BaseNode, word_node: tree.Leaf) -> bool:
    """
    Check if we should insert the word_node on the given expr.

    Works for both correct and incorrect code. This is because the
    user is often working on the code as they write it.
    """
    if not word_node:
        return False
    if len(expr.children) == 0:
        return True
    first_child = expr.children[0]
    if isinstance(first_child, tree.EndMarker):
        if "#" in first_child.prefix:
            return False  # Check for single line comment
    if first_child == word_node:
        return True  # If the word is the first word then its fine
    if len(expr.children) > 1:
        if any(
            node.type == "operator" and "." in node.value or node.type == "trailer"
            for node in expr.children
        ):
            return False  # Check if we're on a method of a function
    if isinstance(first_child, (tree.PythonErrorNode, tree.PythonNode)):
        # The tree will often include error nodes like this to indicate errors
        # we want to ignore errors since the code is being written
        return _should_insert(first_child, word_node)
    return _handle_first_child(first_child, expr, word_node)


def _handle_first_child(
    first_child: NodeOrLeaf, expr: tree.BaseNode, word_node: tree.Leaf
) -> bool:
    """Check if we suggest imports given the following first child."""
    if isinstance(first_child, tree.Import):
        return False
    if isinstance(first_child, (tree.PythonLeaf, tree.PythonErrorLeaf)):
        # Check if the first item is a from or import statement even when incomplete
        if first_child.value in ("import", "from"):
            return False
    if isinstance(first_child, tree.Keyword):
        if first_child.value == "def":
            return _should_import_function(word_node, expr)
        if first_child.value == "class":
            return _should_import_class(word_node, expr)
    return True


def _should_import_class(word_node: tree.Leaf, expr: tree.BaseNode) -> bool:
    prev_node = None
    for node in expr.children:
        if isinstance(node, tree.Name):
            if isinstance(prev_node, tree.Operator):
                if node == word_node and prev_node.value == "(":
                    return True
        prev_node = node

    return False


def _should_import_function(word_node: tree.Leaf, expr: tree.BaseNode) -> bool:
    prev_node = None
    for node in expr.children:
        if _handle_argument(node, word_node):
            return True
        if isinstance(prev_node, tree.Operator):
            if prev_node.value == "->":
                if node == word_node:
                    return True
        prev_node = node
    return False


def _handle_argument(node: NodeOrLeaf, word_node: tree.Leaf):
    if isinstance(node, tree.PythonNode):
        if node.type == "tfpdef":
            if node.children[2] == word_node:
                return True
        if node.type == "parameters":
            for parameter in node.children:
                if _handle_argument(parameter, word_node):
                    return True
    return False


def _process_statements(
    suggestions: List[SearchResult],
    doc_uri: str,
    word: str,
    autoimport: AutoImport,
    document: Document,
    feature: str = "completions",
) -> Generator[Dict[str, Any], None, None]:
    for suggestion in suggestions:
        insert_line = autoimport.find_insertion_line(document.source) - 1
        start = {"line": insert_line, "character": 0}
        edit_range = {"start": start, "end": start}
        edit = {"range": edit_range, "newText": suggestion.import_statement + "\n"}
        score = _get_score(
            suggestion.source, suggestion.import_statement, suggestion.name, word
        )
        if score > _score_max:
            continue
        # TODO make this markdown
        if feature == "completions":
            yield {
                "label": suggestion.name,
                "kind": suggestion.itemkind,
                "sortText": _sort_import(score),
                "data": {"doc_uri": doc_uri},
                "detail": _document(suggestion.import_statement),
                "additionalTextEdits": [edit],
            }
        elif feature == "code_actions":
            yield {
                "title": suggestion.import_statement,
                "kind": "quickfix",
                "edit": {"changes": {doc_uri: [edit]}},
                # data is a supported field for codeAction responses
                # See https://microsoft.github.io/language-server-protocol/specifications/lsp/3.17/specification/#textDocument_codeAction
                "data": {"sortText": _sort_import(score)},
            }
        else:
            raise ValueError(f"Unknown feature: {feature}")


def get_names(script: Script) -> Set[str]:
    """Get all names to ignore from the current file."""
    raw_names = script.get_names(definitions=True)
    log.debug(raw_names)
    return {name.name for name in raw_names}


@hookimpl
def pylsp_completions(
    config: Config,
    workspace: Workspace,
    document: Document,
    position,
    ignored_names: Union[Set[str], None],
):
    """Get autoimport suggestions."""
    if (
        not config.plugin_settings("rope_autoimport")
        .get("completions", {})
        .get("enabled", True)
    ) or cache.is_blocked():
        return []

    line = document.lines[position["line"]]
    expr = parso.parse(line)
    word_node = expr.get_leaf_for_position((1, position["character"]))
    if not _should_insert(expr, word_node):
        return []
    word = word_node.value
    log.debug(f"autoimport: searching for word: {word}")
    rope_config = config.settings(document_path=document.path).get("rope", {})
    ignored_names: Set[str] = ignored_names or get_names(
        document.jedi_script(use_document_path=True)
    )
    autoimport = workspace._rope_autoimport(rope_config)
    suggestions = list(autoimport.search_full(word, ignored_names=ignored_names))
    results = sorted(
        _process_statements(
            suggestions, document.uri, word, autoimport, document, "completions"
        ),
        key=lambda statement: statement["sortText"],
    )
    if len(results) > MAX_RESULTS_COMPLETIONS:
        results = results[:MAX_RESULTS_COMPLETIONS]
    return results


def _document(import_statement: str) -> str:
    return """# Auto-Import\n""" + import_statement


def _get_score(
    source: int, full_statement: str, suggested_name: str, desired_name
) -> int:
    import_length = len("import")
    full_statement_score = len(full_statement) - import_length
    suggested_name_score = (len(suggested_name) - len(desired_name)) ** 2
    source_score = 20 * source
    return suggested_name_score + full_statement_score + source_score


def _sort_import(score: int) -> str:
    score = max(min(score, (_score_max) - 1), 0)
    # Since we are using ints, we need to pad them.
    # We also want to prioritize autoimport behind everything since its the last priority.
    # The minimum is to prevent score from overflowing the pad
    return "[z" + str(score).rjust(_score_pow, "0")


def get_name_or_module(document, diagnostic) -> str:
    start = diagnostic["range"]["start"]
    return (
        parso.parse(document.lines[start["line"]])
        .get_leaf_for_position((1, start["character"] + 1))
        .value
    )


@hookimpl
def pylsp_code_actions(
    config: Config,
    workspace: Workspace,
    document: Document,
    range: Dict,
    context: Dict,
) -> List[Dict]:
    """
    Provide code actions through rope.

    Parameters
    ----------
    config : pylsp.config.config.Config
        Current config.
    workspace : pylsp.workspace.Workspace
        Current workspace.
    document : pylsp.workspace.Document
        Document to apply code actions on.
    range : Dict
        Range argument given by pylsp. Not used here.
    context : Dict
        CodeActionContext given as dict.

    Returns
    -------
      List of dicts containing the code actions.
    """
    if (
        not config.plugin_settings("rope_autoimport")
        .get("code_actions", {})
        .get("enabled", True)
    ) or cache.is_blocked():
        return []

    log.debug(f"textDocument/codeAction: {document} {range} {context}")
    code_actions = []
    for diagnostic in context.get("diagnostics", []):
        if "undefined name" not in diagnostic.get("message", "").lower():
            continue

        word = get_name_or_module(document, diagnostic)
        log.debug(f"autoimport: searching for word: {word}")
        rope_config = config.settings(document_path=document.path).get("rope", {})
        autoimport = workspace._rope_autoimport(rope_config)
        suggestions = list(autoimport.search_full(word))
        log.debug("autoimport: suggestions: %s", suggestions)
        results = sorted(
            _process_statements(
                suggestions,
                document.uri,
                word,
                autoimport,
                document,
                "code_actions",
            ),
            key=lambda statement: statement["data"]["sortText"],
        )

        if len(results) > MAX_RESULTS_CODE_ACTIONS:
            results = results[:MAX_RESULTS_CODE_ACTIONS]
        code_actions.extend(results)

    return code_actions


@hookimpl
def pylsp_initialize(config: Config, workspace: Workspace):
    """Initialize AutoImport.

    Generates the cache for local and global items.
    """
    cache.reload_cache(config, workspace)


@hookimpl
def pylsp_document_did_open(config: Config, workspace: Workspace):
    """Initialize AutoImport.

    Generates the cache for local and global items.
    """
    cache.reload_cache(config, workspace)


@hookimpl
def pylsp_document_did_save(config: Config, workspace: Workspace, document: Document):
    """Update the names associated with this document."""
    cache.reload_cache(config, workspace, [document])


@hookimpl
def pylsp_workspace_configuration_changed(config: Config, workspace: Workspace):
    """
    Initialize autoimport if it has been enabled through a
    workspace/didChangeConfiguration message from the frontend.

    Generates the cache for local and global items.
    """
    if config.plugin_settings("rope_autoimport").get("enabled", False):
        cache.reload_cache(config, workspace)
    else:
        log.debug("autoimport: Skipping cache reload.")


cache: AutoimportCache = AutoimportCache()
