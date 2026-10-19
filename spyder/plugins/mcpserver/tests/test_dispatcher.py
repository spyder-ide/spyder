# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""Tests for dispatching tool calls on behalf of clients."""

# Standard library imports
from concurrent.futures import Future

# Third-party imports
import pytest

# Local imports
from spyder.api.plugins import ExposedCallError, current_caller
from spyder.plugins.mcpserver.api import MCPTool
from spyder.plugins.mcpserver.dispatcher import ToolDispatcher

CLIENT = {"id": "agent-1", "name": "Agent 1"}

SCHEMA = {
    "type": "object",
    "properties": {
        "code": {"type": "string"},
        "console_id": {"type": "string"},
    },
}


def whoami(call):
    caller = current_caller()
    console = call.arguments.get("console_id", "selected")
    return f"{caller.name if caller else None} in {console}"


@pytest.fixture
def dispatcher(qtbot):
    tools = {
        "run": MCPTool("run", "Run code.", whoami, SCHEMA),
        "look": MCPTool("look", "Look.", whoami, SCHEMA, read_only=True),
    }
    return ToolDispatcher(lambda: tools)


def call(dispatcher, name, arguments=None, client=CLIENT):
    results = []
    dispatcher.call(
        name,
        arguments or {},
        client,
        lambda content, is_error: results.append(
            (content[0]["text"], is_error)
        ),
    )
    return results


def test_calls_run_as_their_client(dispatcher):
    assert call(dispatcher, "run") == [("Agent 1 in selected", False)]
    assert call(dispatcher, "run", client=None) == [
        ("None in selected", False)
    ]
    assert [c.name for c in dispatcher.get_clients()] == ["Agent 1"]

    # The caller is only set during the call
    assert current_caller() is None

    assert call(dispatcher, "missing") == [("Unknown tool: missing", True)]


def test_client_arguments(dispatcher):
    dispatcher.set_client_argument("agent-1", "console_id", "2/B")
    assert call(dispatcher, "run") == [("Agent 1 in 2/B", False)]
    assert call(dispatcher, "look") == [("Agent 1 in 2/B", False)]

    # Arguments given by the client win
    assert call(dispatcher, "run", {"console_id": "1/A"}) == [
        ("Agent 1 in 1/A", False)
    ]

    # Other clients aren't affected
    other = {"id": "agent-2", "name": "Agent 2"}
    assert call(dispatcher, "run", client=other) == [
        ("Agent 2 in selected", False)
    ]

    dispatcher.set_client_argument("agent-1", "console_id", None)
    assert call(dispatcher, "run") == [("Agent 1 in selected", False)]


def test_argument_asker(dispatcher):
    asked = []
    answers = {}

    def ask_console(caller, tool, context):
        asked.append((caller.name, tool.name))
        return answers.get(caller.id)

    dispatcher.register_argument_asker("console_id", ask_console)

    # Read-only tools don't ask
    assert call(dispatcher, "look") == [("Agent 1 in selected", False)]
    assert asked == []

    # Tools that change state ask, and None means no value
    assert call(dispatcher, "run") == [("Agent 1 in selected", False)]
    answers["agent-1"] = "3/C"
    assert call(dispatcher, "run") == [("Agent 1 in 3/C", False)]
    assert asked == [("Agent 1", "run")] * 2

    # Nothing is asked if there's a default
    dispatcher.set_client_argument("agent-1", "console_id", "2/B")
    assert call(dispatcher, "run") == [("Agent 1 in 2/B", False)]
    assert len(asked) == 2


def test_argument_asker_future(dispatcher):
    future = Future()
    dispatcher.register_argument_asker(
        "console_id", lambda caller, tool, context: future
    )

    # The call waits for the answer
    results = call(dispatcher, "run")
    assert results == []
    future.set_result("4/D")
    assert results == [("Agent 1 in 4/D", False)]

    # Askers can cancel the call
    future = Future()
    results = call(dispatcher, "run")
    future.set_exception(ExposedCallError("The user cancelled it."))
    assert results == [("The user cancelled it.", True)]


def test_busy_clients(dispatcher):
    future = Future()
    dispatcher.register_argument_asker(
        "console_id", lambda caller, tool, context: future
    )
    results = call(dispatcher, "run")
    assert dispatcher.get_busy_clients() == {"agent-1"}

    future.set_result("4/D")
    assert results == [("Agent 1 in 4/D", False)]
    assert dispatcher.get_busy_clients() == set()

    # Errors finish calls too
    call(dispatcher, "missing")
    assert dispatcher.get_busy_clients() == set()


def test_notes(dispatcher):
    """Clients get notes about what happened in Spyder, once."""
    dispatcher.register_client("agent-2", "Agent 2")
    call(dispatcher, "run")

    # The client that caused something isn't told about it
    dispatcher.notify_clients("A project was opened.", exclude="agent-1")
    assert call(dispatcher, "run") == [("Agent 1 in selected", False)]

    dispatcher.notify_clients("Console 1/A was restarted.")
    results = []
    dispatcher.call(
        "run",
        {},
        CLIENT,
        lambda content, is_error: results.append(
            [item["text"] for item in content]
        ),
    )
    assert results == [
        [
            "Since your last call, in Spyder:\n"
            "- Console 1/A was restarted.",
            "Agent 1 in selected",
        ]
    ]

    # Registered clients get them too, also without calling tools
    assert dispatcher.take_notes("agent-2") == [
        "A project was opened.",
        "Console 1/A was restarted.",
    ]
    assert dispatcher.take_notes("agent-2") == []

    dispatcher.unregister_client("agent-2")
    dispatcher.notify_clients("Something else.")
    assert dispatcher.take_notes("agent-2") == []


def test_note_for_one_client_and_call_observer(dispatcher):
    calls = []
    dispatcher.set_call_observer(
        lambda caller, tool, arguments: calls.append(
            (caller.name, tool.name, arguments)
        )
    )
    dispatcher.set_client_argument("agent-1", "console_id", "2/B")
    call(dispatcher, "run", {"code": "1"})
    assert calls == [("Agent 1", "run", {"code": "1", "console_id": "2/B"})]

    dispatcher.register_client("agent-2", "Agent 2")
    dispatcher.notify_client("agent-2", "Console 2/B was closed.")
    dispatcher.notify_client("unknown", "Ignored.")
    assert dispatcher.take_notes("agent-1") == []
    assert dispatcher.take_notes("agent-2") == ["Console 2/B was closed."]
