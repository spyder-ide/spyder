# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""Tests for the MCP server subprocess, using a real MCP client."""

# Standard library imports
import asyncio
import os
import sys

# Third-party imports
import pytest

# Local imports
from spyder.plugins.mcpserver.bridge import (
    CLIENT_ID_HEADER,
    CLIENT_NAME_HEADER,
    NOTES_PATH,
    BridgeMethods,
    JsonRpcPeer,
    TOKEN_ENV_VAR,
)
from spyder.utils.misc import select_port

httpx2 = pytest.importorskip("httpx2")
pytest.importorskip("mcp")

from mcp.client.client import Client  # noqa: E402
from mcp.client.session import ClientSession  # noqa: E402
from mcp.client.streamable_http import streamable_http_client  # noqa: E402
import mcp.types as types  # noqa: E402

from spyder.plugins.mcpserver.server import QUESTION_KEY  # noqa: E402

TOKEN = "test-token"

TOOLS = [
    {
        "name": "echo",
        "description": "Echo the text.",
        "inputSchema": {
            "type": "object",
            "properties": {"text": {"type": "string"}},
        },
        "annotations": {"readOnlyHint": True, "destructiveHint": False},
    }
]


async def start_server():
    """Start the server subprocess with a fake Spyder end of the bridge."""
    env = dict(os.environ, **{TOKEN_ENV_VAR: TOKEN})
    process = await asyncio.create_subprocess_exec(
        sys.executable, "-m", "spyder.plugins.mcpserver.server",
        "--port", str(select_port(default_port=18768)),
        stdin=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.PIPE,
        env=env,
    )
    ready = asyncio.get_running_loop().create_future()
    clients = []

    async def write(data):
        process.stdin.write(data)
        await process.stdin.drain()

    async def list_tools(params):
        return TOOLS

    async def call_tool(params):
        clients.append(params.get("client"))
        text = params["arguments"]["text"]
        if text == "fail":
            raise RuntimeError("Tool failed")
        if text.startswith("ask"):
            # Spyder asks the user of the client that made the call, as
            # many times as "ask" is repeated
            answers = []
            for __ in range(text.count("ask")):
                answer = await peer.request(
                    BridgeMethods.AskUser,
                    {
                        "callId": params["callId"],
                        "message": "Which console?",
                        "choices": ["Console 1/A", "New console"],
                        "default": "New console",
                    },
                )
                await peer.notify(
                    BridgeMethods.ReportProgress,
                    {"callId": params["callId"], "message": "Running"},
                )
                answers.append(f"{answer['action']} {answer['choice']}")
            text = f"{params['canAskUser']} " + ", ".join(answers)
        return {
            "content": [
                {"type": "text", "text": text},
                {"type": "image", "data": "iVBORw0KGgo=",
                 "mimeType": "image/png"},
            ],
            "isError": False,
        }

    async def server_ready(params):
        ready.set_result(params["url"])

    notes = {"agent-2": ["The user opened a project."]}

    async def take_notes(params):
        return notes.pop(params["clientId"], [])

    peer = JsonRpcPeer(
        process.stdout.readline,
        write,
        {
            BridgeMethods.ListTools: list_tools,
            BridgeMethods.CallTool: call_tool,
            BridgeMethods.ServerReady: server_ready,
            BridgeMethods.TakeNotes: take_notes,
        },
    )
    peer_task = asyncio.create_task(peer.run())
    url = await asyncio.wait_for(ready, 30)
    return process, peer_task, url, clients


def test_server():
    """Test listing and calling tools, and auth, through the server."""

    async def run():
        process, peer_task, url, clients = await start_server()

        try:
            # Requests without the token are rejected
            async with httpx2.AsyncClient() as http:
                response = await http.post(url, json={})
                assert response.status_code == 401

            headers = {"Authorization": f"Bearer {TOKEN}"}
            async with httpx2.AsyncClient(headers=headers) as http:
                async with streamable_http_client(
                    url, http_client=http
                ) as streams:
                    read, write = streams[0], streams[1]
                    async with ClientSession(read, write) as session:
                        await session.initialize()

                        result = await session.list_tools()
                        assert [t.name for t in result.tools] == ["echo"]
                        assert result.tools[0].annotations.read_only_hint

                        result = await session.call_tool(
                            "echo", {"text": "hello"}
                        )
                        assert not result.is_error
                        assert result.content[0].text == "hello"
                        assert result.content[1].type == "image"

                        result = await session.call_tool(
                            "echo", {"text": "fail"}
                        )
                        assert result.is_error
                        assert "Tool failed" in result.content[0].text

            # Clients without their own id are told apart by MCP session
            assert clients[0]["id"].startswith("mcp-session:")
            assert clients[0]["name"] == "External agent"

            # Clients started by Spyder say who they are
            headers.update(
                {
                    CLIENT_ID_HEADER: "agent-2",
                    CLIENT_NAME_HEADER: "Agent 2",
                }
            )
            async with httpx2.AsyncClient(headers=headers) as http:
                async with streamable_http_client(
                    url, http_client=http
                ) as streams:
                    async with ClientSession(
                        streams[0], streams[1]
                    ) as session:
                        await session.initialize()
                        await session.call_tool("echo", {"text": "hi"})
            assert clients[-1] == {"id": "agent-2", "name": "Agent 2"}

            # With the 2026-07-28 protocol, which has no sessions, clients
            # without their own id are told apart by kind
            headers = {"Authorization": f"Bearer {TOKEN}"}
            async with httpx2.AsyncClient(headers=headers) as http:
                async with Client(
                    streamable_http_client(url, http_client=http),
                    mode="auto",
                    client_info=types.Implementation(
                        name="some-agent", title="Some Agent", version="1"
                    ),
                ) as client:
                    assert client.protocol_version == "2026-07-28"
                    await client.call_tool("echo", {"text": "hi"})
                    async with Client(
                        streamable_http_client(url, http_client=http),
                        mode="auto",
                    ) as other:
                        await other.call_tool("echo", {"text": "hi"})
            assert clients[-2] == {
                "id": "mcp-client:some-agent",
                "name": "External agent (Some Agent)",
            }
            assert clients[-1]["id"] != clients[-2]["id"]
        finally:
            # The server exits when its stdin is closed
            process.stdin.close()
            assert await asyncio.wait_for(process.wait(), 10) == 0
            await peer_task

    asyncio.run(run())


def test_ask_user():
    """Spyder can ask the user of the client that made a tool call."""

    async def run():
        process, peer_task, url, clients = await start_server()
        questions = []

        async def answer(context, params):
            questions.append(params)
            choices = params.requested_schema["properties"]["choice"]["enum"]
            return types.ElicitResult(
                action="accept", content={"choice": choices[1]}
            )

        async def decline(context, params):
            return types.ElicitResult(action="decline")

        try:
            headers = {"Authorization": f"Bearer {TOKEN}"}
            for callback, expected in [
                (answer, "True accept New console"),
                (decline, "True decline None"),
                # Clients that can't show forms aren't asked
                (None, "False cancel None"),
            ]:
                async with httpx2.AsyncClient(headers=headers) as http:
                    async with streamable_http_client(
                        url, http_client=http
                    ) as streams:
                        async with ClientSession(
                            streams[0],
                            streams[1],
                            elicitation_callback=callback,
                        ) as session:
                            await session.initialize()
                            result = await session.call_tool(
                                "echo", {"text": "ask"}
                            )
                            assert result.content[0].text == expected

            assert questions[0].message == "Which console?"
            choice = questions[0].requested_schema["properties"]["choice"]
            assert choice["default"] == "New console"

            # With the 2026-07-28 protocol, the call returns the question
            # and the client makes it again with the answer
            for callback, text, expected in [
                (answer, "ask", "True accept New console"),
                (
                    answer,
                    "askask",
                    "True accept New console, accept New console",
                ),
                (decline, "ask", "True decline None"),
                (None, "ask", "False cancel None"),
            ]:
                async with httpx2.AsyncClient(headers=headers) as http:
                    async with Client(
                        streamable_http_client(url, http_client=http),
                        mode="auto",
                        elicitation_callback=callback,
                    ) as client:
                        assert client.protocol_version == "2026-07-28"
                        result = await client.call_tool("echo", {"text": text})
                        assert result.content[0].text == expected

                        # Answers to calls Spyder doesn't know are refused
                        result = await client.call_tool(
                            "echo",
                            {"text": text},
                            request_state="unknown",
                            input_responses={
                                QUESTION_KEY: types.ElicitResult(
                                    action="accept",
                                    content={"choice": "New console"},
                                )
                            },
                        )
                        assert result.is_error
        finally:
            process.stdin.close()
            assert await asyncio.wait_for(process.wait(), 10) == 0
            await peer_task

    asyncio.run(run())


def test_notes_endpoint():
    """Clients get their notes from Spyder, once, with the token."""

    async def run():
        process, peer_task, url, clients = await start_server()
        notes_url = url.rsplit("/", 1)[0] + NOTES_PATH
        try:
            async with httpx2.AsyncClient() as http:
                response = await http.get(notes_url, params={"client": "x"})
                assert response.status_code == 401

            headers = {"Authorization": f"Bearer {TOKEN}"}
            async with httpx2.AsyncClient(headers=headers) as http:
                for expected in [["The user opened a project."], []]:
                    response = await http.get(
                        notes_url, params={"client": "agent-2"}
                    )
                    assert response.json() == {"notes": expected}
        finally:
            process.stdin.close()
            assert await asyncio.wait_for(process.wait(), 10) == 0
            await peer_task

    asyncio.run(run())
