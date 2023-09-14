# Copyright 2021- Python Language Server Contributors.

import os
import time
from unittest.mock import patch, call

from test.fixtures import CALL_TIMEOUT_IN_SECONDS

import pytest

from pylsp import IS_WIN
from pylsp.lsp import NotebookCellKind


def wait_for_condition(condition, timeout=CALL_TIMEOUT_IN_SECONDS):
    """Wait for a condition to be true, or timeout."""
    start_time = time.time()
    while not condition():
        time.sleep(0.1)
        if time.time() - start_time > timeout:
            raise TimeoutError("Timeout waiting for condition")


@pytest.mark.skipif(IS_WIN, reason="Flaky on Windows")
def test_initialize(client_server_pair):
    client, server = client_server_pair
    response = client._endpoint.request(
        "initialize",
        {
            "processId": 1234,
            "rootPath": os.path.dirname(__file__),
            "initializationOptions": {},
        },
    ).result(timeout=CALL_TIMEOUT_IN_SECONDS)
    assert server.workspace is not None
    assert "notebookDocumentSync" in response["capabilities"].keys()


@pytest.mark.skipif(IS_WIN, reason="Flaky on Windows")
def test_notebook_document__did_open(
    client_server_pair,
):
    client, server = client_server_pair
    client._endpoint.request(
        "initialize",
        {
            "processId": 1234,
            "rootPath": os.path.dirname(__file__),
            "initializationOptions": {},
        },
    ).result(timeout=CALL_TIMEOUT_IN_SECONDS)

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
                        {
                            "kind": NotebookCellKind.Code,
                            "document": "cell_2_uri",
                        },
                        {
                            "kind": NotebookCellKind.Code,
                            "document": "cell_3_uri",
                        },
                        {
                            "kind": NotebookCellKind.Code,
                            "document": "cell_4_uri",
                        },
                        {
                            "kind": NotebookCellKind.Code,
                            "document": "cell_5_uri",
                        },
                    ],
                },
                # Test as many edge cases as possible for the diagnostics message
                "cellTextDocuments": [
                    {
                        "uri": "cell_1_uri",
                        "languageId": "python",
                        "text": "",
                    },
                    {
                        "uri": "cell_2_uri",
                        "languageId": "python",
                        "text": "\n",
                    },
                    {
                        "uri": "cell_3_uri",
                        "languageId": "python",
                        "text": "\nimport sys\n\nabc\n\n",
                    },
                    {
                        "uri": "cell_4_uri",
                        "languageId": "python",
                        "text": "x",
                    },
                    {
                        "uri": "cell_5_uri",
                        "languageId": "python",
                        "text": "y\n",
                    },
                ],
            },
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
):
    client, server = client_server_pair
    client._endpoint.request(
        "initialize",
        {
            "processId": 1234,
            "rootPath": os.path.dirname(__file__),
            "initializationOptions": {},
        },
    ).result(timeout=CALL_TIMEOUT_IN_SECONDS)

    # Open notebook
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
                        {
                            "kind": NotebookCellKind.Code,
                            "document": "cell_2_uri",
                        },
                    ],
                },
                "cellTextDocuments": [
                    {
                        "uri": "cell_1_uri",
                        "languageId": "python",
                        "text": "import sys",
                    },
                    {
                        "uri": "cell_2_uri",
                        "languageId": "python",
                        "text": "",
                    },
                ],
            },
        )
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
):
    client, server = client_server_pair
    client._endpoint.request(
        "initialize",
        {
            "processId": 1234,
            "rootPath": os.path.dirname(__file__),
            "initializationOptions": {},
        },
    ).result(timeout=CALL_TIMEOUT_IN_SECONDS)

    # Open notebook
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
                        {
                            "kind": NotebookCellKind.Code,
                            "document": "cell_2_uri",
                        },
                    ],
                },
                "cellTextDocuments": [
                    {
                        "uri": "cell_1_uri",
                        "languageId": "python",
                        "text": "import sys",
                    },
                    {
                        "uri": "cell_2_uri",
                        "languageId": "python",
                        "text": "",
                    },
                ],
            },
        )
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
def test_notebook_definition(client_server_pair):
    client, server = client_server_pair
    client._endpoint.request(
        "initialize",
        {
            "processId": 1234,
            "rootPath": os.path.dirname(__file__),
            "initializationOptions": {},
        },
    ).result(timeout=CALL_TIMEOUT_IN_SECONDS)

    # Open notebook
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
                        {
                            "kind": NotebookCellKind.Code,
                            "document": "cell_2_uri",
                        },
                    ],
                },
                "cellTextDocuments": [
                    {
                        "uri": "cell_1_uri",
                        "languageId": "python",
                        "text": "y=2\nx=1",
                    },
                    {
                        "uri": "cell_2_uri",
                        "languageId": "python",
                        "text": "x",
                    },
                ],
            },
        )
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
