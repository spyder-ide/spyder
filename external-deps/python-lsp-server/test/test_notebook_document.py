# Copyright 2021- Python Language Server Contributors.

import time
from unittest.mock import call, patch

import pytest

from pylsp import IS_WIN
from pylsp.lsp import NotebookCellKind
from pylsp.workspace import Notebook
from test.test_utils import (
    CALL_TIMEOUT_IN_SECONDS,
    send_initialize_request,
    send_notebook_did_open,
)


def wait_for_condition(condition, timeout=CALL_TIMEOUT_IN_SECONDS) -> None:
    """Wait for a condition to be true, or timeout."""
    start_time = time.time()
    while not condition():
        time.sleep(0.1)
        if time.time() - start_time > timeout:
            raise TimeoutError("Timeout waiting for condition")


@pytest.mark.skipif(IS_WIN, reason="Flaky on Windows")
def test_initialize(client_server_pair) -> None:
    client, server = client_server_pair
    response = send_initialize_request(client)
    assert server.workspace is not None
    selector = response["capabilities"]["notebookDocumentSync"]["notebookSelector"]
    assert isinstance(selector, list)


@pytest.mark.skipif(IS_WIN, reason="Flaky on Windows")
def test_workspace_did_change_configuration(client_server_pair) -> None:
    """Test that we can update a workspace config w/o error when a notebook is open."""
    client, server = client_server_pair
    send_initialize_request(client)
    assert server.workspace is not None

    with patch.object(server._endpoint, "notify") as mock_notify:
        client._endpoint.notify(
            "notebookDocument/didOpen",
            {
                "notebookDocument": {
                    "uri": "notebook_uri",
                    "notebookType": "jupyter-notebook",
                    "cells": [
                        {
                            "kind": NotebookCellKind.Code,
                            "document": "cell_1_uri",
                        },
                    ],
                },
                "cellTextDocuments": [
                    {
                        "uri": "cell_1_uri",
                        "languageId": "python",
                        "text": "",
                    },
                ],
            },
        )
        wait_for_condition(lambda: mock_notify.call_count >= 1)
    assert isinstance(server.workspace.get_document("notebook_uri"), Notebook)
    assert len(server.workspace.documents) == 2

    server.workspace.update_config(
        {"pylsp": {"plugins": {"flake8": {"enabled": True}}}}
    )

    assert server.config.plugin_settings("flake8").get("enabled") is True
    assert (
        server.workspace.get_document("cell_1_uri")
        ._config.plugin_settings("flake8")
        .get("enabled")
        is True
    )


@pytest.mark.skipif(IS_WIN, reason="Flaky on Windows")
def test_notebook_document__did_open(
    client_server_pair,
) -> None:
    client, server = client_server_pair
    send_initialize_request(client)

    with patch.object(server._endpoint, "notify") as mock_notify:
        # Test as many edge cases as possible for the diagnostics messages
        send_notebook_did_open(
            client, ["", "\n", "\nimport sys\n\nabc\n\n", "x", "y\n"]
        )
        wait_for_condition(lambda: mock_notify.call_count >= 5)
        expected_call_args = [
            call(
                "textDocument/publishDiagnostics",
                params={
                    "uri": "cell_1_uri",
                    "diagnostics": [],
                },
            ),
            call(
                "textDocument/publishDiagnostics",
                params={
                    "uri": "cell_2_uri",
                    "diagnostics": [],
                },
            ),
            call(
                "textDocument/publishDiagnostics",
                params={
                    "uri": "cell_3_uri",
                    "diagnostics": [
                        {
                            "source": "pyflakes",
                            "range": {
                                "start": {"line": 1, "character": 0},
                                "end": {"line": 1, "character": 11},
                            },
                            "message": "'sys' imported but unused",
                            "severity": 2,
                        },
                        {
                            "source": "pyflakes",
                            "range": {
                                "start": {"line": 3, "character": 0},
                                "end": {"line": 3, "character": 4},
                            },
                            "message": "undefined name 'abc'",
                            "severity": 1,
                        },
                        {
                            "source": "pycodestyle",
                            "range": {
                                "start": {"line": 1, "character": 0},
                                "end": {"line": 1, "character": 11},
                            },
                            "message": "E303 too many blank lines (4)",
                            "code": "E303",
                            "severity": 2,
                        },
                    ],
                },
            ),
            call(
                "textDocument/publishDiagnostics",
                params={
                    "uri": "cell_4_uri",
                    "diagnostics": [
                        {
                            "source": "pyflakes",
                            "range": {
                                "start": {"line": 0, "character": 0},
                                "end": {"line": 0, "character": 2},
                            },
                            "message": "undefined name 'x'",
                            "severity": 1,
                        },
                    ],
                },
            ),
            call(
                "textDocument/publishDiagnostics",
                params={
                    "uri": "cell_5_uri",
                    "diagnostics": [
                        {
                            "source": "pyflakes",
                            "range": {
                                "start": {"line": 0, "character": 0},
                                "end": {"line": 0, "character": 2},
                            },
                            "message": "undefined name 'y'",
                            "severity": 1,
                        },
                    ],
                },
            ),
        ]
        mock_notify.assert_has_calls(expected_call_args)


@pytest.mark.skipif(IS_WIN, reason="Flaky on Windows")
def test_notebook_document__did_change(
    client_server_pair,
) -> None:
    client, server = client_server_pair
    send_initialize_request(client)

    # Open notebook
    with patch.object(server._endpoint, "notify") as mock_notify:
        send_notebook_did_open(client, ["import sys", ""])
        wait_for_condition(lambda: mock_notify.call_count >= 2)
        assert len(server.workspace.documents) == 3
        for uri in ["cell_1_uri", "cell_2_uri", "notebook_uri"]:
            assert uri in server.workspace.documents
        assert len(server.workspace.get_document("notebook_uri").cells) == 2
        expected_call_args = [
            call(
                "textDocument/publishDiagnostics",
                params={
                    "uri": "cell_1_uri",
                    "diagnostics": [
                        {
                            "source": "pyflakes",
                            "range": {
                                "start": {"line": 0, "character": 0},
                                "end": {"line": 0, "character": 11},
                            },
                            "message": "'sys' imported but unused",
                            "severity": 2,
                        }
                    ],
                },
            ),
            call(
                "textDocument/publishDiagnostics",
                params={"uri": "cell_2_uri", "diagnostics": []},
            ),
        ]
        mock_notify.assert_has_calls(expected_call_args)

    # Remove second cell
    with patch.object(server._endpoint, "notify") as mock_notify:
        client._endpoint.notify(
            "notebookDocument/didChange",
            {
                "notebookDocument": {
                    "uri": "notebook_uri",
                },
                "change": {
                    "cells": {
                        "structure": {
                            "array": {
                                "start": 1,
                                "deleteCount": 1,
                            },
                            "didClose": [
                                {
                                    "uri": "cell_2_uri",
                                }
                            ],
                        },
                    }
                },
            },
        )
        wait_for_condition(lambda: mock_notify.call_count >= 2)
        assert len(server.workspace.documents) == 2
        assert "cell_2_uri" not in server.workspace.documents
        assert len(server.workspace.get_document("notebook_uri").cells) == 1
        expected_call_args = [
            call(
                "textDocument/publishDiagnostics",
                params={
                    "uri": "cell_1_uri",
                    "diagnostics": [
                        {
                            "source": "pyflakes",
                            "range": {
                                "start": {"line": 0, "character": 0},
                                "end": {"line": 0, "character": 10},
                            },
                            "message": "'sys' imported but unused",
                            "severity": 2,
                        },
                        {
                            "source": "pycodestyle",
                            "range": {
                                "start": {"line": 0, "character": 10},
                                "end": {"line": 0, "character": 10},
                            },
                            "message": "W292 no newline at end of file",
                            "code": "W292",
                            "severity": 2,
                        },
                    ],
                },
            )
        ]
        mock_notify.assert_has_calls(expected_call_args)

    # Add second cell
    with patch.object(server._endpoint, "notify") as mock_notify:
        client._endpoint.notify(
            "notebookDocument/didChange",
            {
                "notebookDocument": {
                    "uri": "notebook_uri",
                },
                "change": {
                    "cells": {
                        "structure": {
                            "array": {
                                "start": 1,
                                "deleteCount": 0,
                                "cells": [
                                    {
                                        "kind": NotebookCellKind.Code,
                                        "document": "cell_3_uri",
                                    }
                                ],
                            },
                            "didOpen": [
                                {
                                    "uri": "cell_3_uri",
                                    "languageId": "python",
                                    "text": "x",
                                }
                            ],
                        },
                    }
                },
            },
        )
        wait_for_condition(lambda: mock_notify.call_count >= 2)
        assert len(server.workspace.documents) == 3
        assert "cell_3_uri" in server.workspace.documents
        assert len(server.workspace.get_document("notebook_uri").cells) == 2
        expected_call_args = [
            call(
                "textDocument/publishDiagnostics",
                params={
                    "uri": "cell_1_uri",
                    "diagnostics": [
                        {
                            "source": "pyflakes",
                            "range": {
                                "start": {"line": 0, "character": 0},
                                "end": {"line": 0, "character": 11},
                            },
                            "message": "'sys' imported but unused",
                            "severity": 2,
                        }
                    ],
                },
            ),
            call(
                "textDocument/publishDiagnostics",
                params={
                    "uri": "cell_3_uri",
                    "diagnostics": [
                        {
                            "source": "pyflakes",
                            "range": {
                                "start": {"line": 0, "character": 0},
                                "end": {"line": 0, "character": 1},
                            },
                            "message": "undefined name 'x'",
                            "severity": 1,
                        },
                        {
                            "source": "pycodestyle",
                            "range": {
                                "start": {"line": 0, "character": 1},
                                "end": {"line": 0, "character": 1},
                            },
                            "message": "W292 no newline at end of file",
                            "code": "W292",
                            "severity": 2,
                        },
                    ],
                },
            ),
        ]
        mock_notify.assert_has_calls(expected_call_args)

    # Edit second cell
    with patch.object(server._endpoint, "notify") as mock_notify:
        client._endpoint.notify(
            "notebookDocument/didChange",
            {
                "notebookDocument": {
                    "uri": "notebook_uri",
                },
                "change": {
                    "cells": {
                        "textContent": [
                            {
                                "document": {
                                    "uri": "cell_3_uri",
                                },
                                "changes": [{"text": "sys.path"}],
                            }
                        ]
                    }
                },
            },
        )
        wait_for_condition(lambda: mock_notify.call_count >= 2)
        expected_call_args = [
            call(
                "textDocument/publishDiagnostics",
                params={"uri": "cell_1_uri", "diagnostics": []},
            ),
            call(
                "textDocument/publishDiagnostics",
                params={
                    "uri": "cell_3_uri",
                    "diagnostics": [
                        {
                            "source": "pycodestyle",
                            "range": {
                                "start": {"line": 0, "character": 8},
                                "end": {"line": 0, "character": 8},
                            },
                            "message": "W292 no newline at end of file",
                            "code": "W292",
                            "severity": 2,
                        }
                    ],
                },
            ),
        ]
        mock_notify.assert_has_calls(expected_call_args)


@pytest.mark.skipif(IS_WIN, reason="Flaky on Windows")
def test_notebook__did_close(
    client_server_pair,
) -> None:
    client, server = client_server_pair
    send_initialize_request(client)

    # Open notebook
    with patch.object(server._endpoint, "notify") as mock_notify:
        send_notebook_did_open(client, ["import sys", ""])
        wait_for_condition(lambda: mock_notify.call_count >= 2)
        assert len(server.workspace.documents) == 3
        for uri in ["cell_1_uri", "cell_2_uri", "notebook_uri"]:
            assert uri in server.workspace.documents

    # Close notebook
    with patch.object(server._endpoint, "notify") as mock_notify:
        client._endpoint.notify(
            "notebookDocument/didClose",
            {
                "notebookDocument": {
                    "uri": "notebook_uri",
                },
                "cellTextDocuments": [
                    {
                        "uri": "cell_1_uri",
                    },
                    {
                        "uri": "cell_2_uri",
                    },
                ],
            },
        )
        wait_for_condition(lambda: mock_notify.call_count >= 2)
        assert len(server.workspace.documents) == 0


@pytest.mark.skipif(IS_WIN, reason="Flaky on Windows")
def test_notebook_definition(client_server_pair) -> None:
    client, server = client_server_pair
    send_initialize_request(client)

    # Open notebook
    with patch.object(server._endpoint, "notify") as mock_notify:
        send_notebook_did_open(client, ["y=2\nx=1", "x"])
        # wait for expected diagnostics messages
        wait_for_condition(lambda: mock_notify.call_count >= 2)
        assert len(server.workspace.documents) == 3
        for uri in ["cell_1_uri", "cell_2_uri", "notebook_uri"]:
            assert uri in server.workspace.documents

    future = client._endpoint.request(
        "textDocument/definition",
        {
            "textDocument": {
                "uri": "cell_2_uri",
            },
            "position": {"line": 0, "character": 1},
        },
    )
    result = future.result(CALL_TIMEOUT_IN_SECONDS)
    assert result == [
        {
            "uri": "cell_1_uri",
            "range": {
                "start": {"line": 1, "character": 0},
                "end": {"line": 1, "character": 1},
            },
        }
    ]


@pytest.mark.skipif(IS_WIN, reason="Flaky on Windows")
def test_notebook_completion(client_server_pair) -> None:
    """
    Tests that completions work across cell boundaries for notebook document support
    """
    client, server = client_server_pair
    send_initialize_request(client)

    # Open notebook
    with patch.object(server._endpoint, "notify") as mock_notify:
        send_notebook_did_open(
            client, ["answer_to_life_universe_everything = 42", "answer_"]
        )
        # wait for expected diagnostics messages
        wait_for_condition(lambda: mock_notify.call_count >= 2)
        assert len(server.workspace.documents) == 3
        for uri in ["cell_1_uri", "cell_2_uri", "notebook_uri"]:
            assert uri in server.workspace.documents

    future = client._endpoint.request(
        "textDocument/completion",
        {
            "textDocument": {
                "uri": "cell_2_uri",
            },
            "position": {"line": 0, "character": 7},
        },
    )
    result = future.result(CALL_TIMEOUT_IN_SECONDS)
    assert result == {
        "isIncomplete": False,
        "items": [
            {
                "data": {"doc_uri": "cell_2_uri"},
                "insertText": "answer_to_life_universe_everything",
                "kind": 6,
                "label": "answer_to_life_universe_everything",
                "sortText": "aanswer_to_life_universe_everything",
            },
        ],
    }
