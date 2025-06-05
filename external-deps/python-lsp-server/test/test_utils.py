# Copyright 2017-2020 Palantir Technologies, Inc.
# Copyright 2021- Python Language Server Contributors.

import multiprocessing
import os
import sys
import time
from threading import Thread
from typing import Any
from unittest import mock

from docstring_to_markdown import UnknownFormatError
from flaky import flaky

from pylsp import _utils
from pylsp.lsp import NotebookCellKind
from pylsp.python_lsp import PythonLSPServer, start_io_lang_server

CALL_TIMEOUT_IN_SECONDS = 30


def send_notebook_did_open(client, cells: list[str]) -> None:
    """
    Sends a notebookDocument/didOpen notification with the given python cells.

    The notebook has the uri "notebook_uri" and the cells have the uris
    "cell_1_uri", "cell_2_uri", etc.
    """
    client._endpoint.notify(
        "notebookDocument/didOpen", notebook_with_python_cells(cells)
    )


def notebook_with_python_cells(cells: list[str]):
    """
    Create a notebook document with the given python cells.

    The notebook has the uri "notebook_uri" and the cells have the uris
    "cell_1_uri", "cell_2_uri", etc.
    """
    return {
        "notebookDocument": {
            "uri": "notebook_uri",
            "notebookType": "jupyter-notebook",
            "cells": [
                {
                    "kind": NotebookCellKind.Code,
                    "document": f"cell_{i + 1}_uri",
                }
                for i in range(len(cells))
            ],
        },
        "cellTextDocuments": [
            {
                "uri": f"cell_{i + 1}_uri",
                "languageId": "python",
                "text": cell,
            }
            for i, cell in enumerate(cells)
        ],
    }


def send_initialize_request(client, initialization_options: dict[str, Any] = None):
    return client._endpoint.request(
        "initialize",
        {
            "processId": 1234,
            "rootPath": os.path.dirname(__file__),
            "initializationOptions": initialization_options,
        },
    ).result(timeout=CALL_TIMEOUT_IN_SECONDS)


def start(obj) -> None:
    obj.start()


class ClientServerPair:
    """
    A class to setup a client/server pair.

    args:
        start_server_in_process: if True, the server will be started in a process.
        check_parent_process: if True, the server_process will check if the parent process is alive.
    """

    def __init__(
        self, start_server_in_process=False, check_parent_process=False
    ) -> None:
        # Client to Server pipe
        csr, csw = os.pipe()
        # Server to client pipe
        scr, scw = os.pipe()

        if start_server_in_process:
            ParallelKind = self._get_parallel_kind()
            self.server_process = ParallelKind(
                target=start_io_lang_server,
                args=(
                    os.fdopen(csr, "rb"),
                    os.fdopen(scw, "wb"),
                    check_parent_process,
                    PythonLSPServer,
                ),
            )
            self.server_process.start()
        else:
            self.server = PythonLSPServer(os.fdopen(csr, "rb"), os.fdopen(scw, "wb"))
            self.server_thread = Thread(target=start, args=[self.server])
            self.server_thread.start()

        self.client = PythonLSPServer(os.fdopen(scr, "rb"), os.fdopen(csw, "wb"))
        self.client_thread = Thread(target=start, args=[self.client])
        self.client_thread.start()

    def _get_parallel_kind(self):
        if os.name == "nt":
            return Thread

        if sys.version_info[:2] >= (3, 8):
            return multiprocessing.get_context("fork").Process

        return multiprocessing.Process


@flaky(max_runs=6, min_passes=1)
def test_debounce() -> None:
    interval = 0.1
    obj = mock.Mock()

    @_utils.debounce(0.1)
    def call_m():
        obj()

    assert not obj.mock_calls

    call_m()
    call_m()
    call_m()
    assert not obj.mock_calls

    time.sleep(interval * 2)
    assert len(obj.mock_calls) == 1

    call_m()
    time.sleep(interval * 2)
    assert len(obj.mock_calls) == 2


@flaky(max_runs=6, min_passes=1)
def test_debounce_keyed_by() -> None:
    interval = 0.1
    obj = mock.Mock()

    @_utils.debounce(0.1, keyed_by="key")
    def call_m(key):
        obj(key)

    assert not obj.mock_calls

    call_m(1)
    call_m(2)
    call_m(3)
    assert not obj.mock_calls

    time.sleep(interval * 2)
    obj.assert_has_calls(
        [
            mock.call(1),
            mock.call(2),
            mock.call(3),
        ],
        any_order=True,
    )
    assert len(obj.mock_calls) == 3

    call_m(1)
    call_m(1)
    call_m(1)
    time.sleep(interval * 2)
    assert len(obj.mock_calls) == 4


def test_list_to_string() -> None:
    assert _utils.list_to_string("string") == "string"
    assert _utils.list_to_string(["a", "r", "r", "a", "y"]) == "a,r,r,a,y"


def test_find_parents(tmpdir) -> None:
    subsubdir = tmpdir.ensure_dir("subdir", "subsubdir")
    path = subsubdir.ensure("path.py")
    test_cfg = tmpdir.ensure("test.cfg")

    assert _utils.find_parents(tmpdir.strpath, path.strpath, ["test.cfg"]) == [
        test_cfg.strpath
    ]


def test_merge_dicts() -> None:
    assert _utils.merge_dicts(
        {"a": True, "b": {"x": 123, "y": {"hello": "world"}}},
        {"a": False, "b": {"y": [], "z": 987}},
    ) == {"a": False, "b": {"x": 123, "y": [], "z": 987}}


def test_clip_column() -> None:
    assert _utils.clip_column(0, [], 0) == 0
    assert _utils.clip_column(2, ["123"], 0) == 2
    assert _utils.clip_column(3, ["123"], 0) == 3
    assert _utils.clip_column(5, ["123"], 0) == 3
    assert _utils.clip_column(0, ["\n", "123"], 0) == 0
    assert _utils.clip_column(1, ["\n", "123"], 0) == 0
    assert _utils.clip_column(2, ["123\n", "123"], 0) == 2
    assert _utils.clip_column(3, ["123\n", "123"], 0) == 3
    assert _utils.clip_column(4, ["123\n", "123"], 1) == 3


@mock.patch("docstring_to_markdown.convert")
def test_format_docstring_valid_rst_signature(mock_convert) -> None:
    """Test that a valid RST docstring includes the function signature."""
    docstring = """A function docstring.

    Parameters
    ----------
    a : str, something
    """

    # Mock the return value to avoid depedency on the real thing
    mock_convert.return_value = """A function docstring.

    #### Parameters

    - `a`: str, something
    """

    markdown = _utils.format_docstring(
        docstring,
        "markdown",
        ["something(a: str) -> str"],
    )["value"]

    assert markdown.startswith(
        _utils.wrap_signature("something(a: str) -> str"),
    )


@mock.patch("docstring_to_markdown.convert", side_effect=UnknownFormatError)
def test_format_docstring_invalid_rst_signature(_) -> None:
    """Test that an invalid RST docstring includes the function signature."""
    docstring = """A function docstring.

    Parameters
    ----------
    a : str, something
    """

    markdown = _utils.format_docstring(
        docstring,
        "markdown",
        ["something(a: str) -> str"],
    )["value"]

    assert markdown.startswith(
        _utils.wrap_signature("something(a: str) -> str"),
    )
