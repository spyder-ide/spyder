# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""
Spyder MCP server subprocess.

This process exposes a Model Context Protocol endpoint over Streamable HTTP
and forwards tool listings and calls to Spyder through a JSON-RPC bridge on
its stdio (see ``bridge.py``). Running the HTTP server here, instead of in
Spyder, keeps its dependencies and event loop out of the GUI process, just
like it's done for the LSP servers.

Usage::

    SPYDER_MCP_TOKEN=<token> python -m spyder.plugins.mcpserver.server \
        --host 127.0.0.1 --port 8768

The process exits when its stdin is closed, i.e. when Spyder goes away.
"""

# Standard library imports
from __future__ import annotations

import argparse
import asyncio
import hmac
import logging
import os
import sys
import uuid

# Third-party imports
import mcp.types as types
from mcp.server.lowlevel import Server
from mcp_types.version import MODERN_PROTOCOL_VERSIONS
from starlette.responses import JSONResponse
from starlette.routing import Route
import uvicorn

# Local imports
from spyder.plugins.mcpserver.bridge import (
    CLIENT_ID_HEADER,
    CLIENT_NAME_HEADER,
    NOTES_PATH,
    BridgeError,
    BridgeMethods,
    JsonRpcPeer,
    TOKEN_ENV_VAR,
)

logger = logging.getLogger("spyder.mcpserver")

MCP_PATH = "/mcp"

# Key of Spyder's question in the input requests of a tool call result
QUESTION_KEY = "spyder_question"

# Seconds a tool call waits for its client to answer Spyder's question
# before taking it as cancelled
ANSWER_TIMEOUT = 30 * 60

INSTRUCTIONS = """\
This server controls a running Spyder IDE session.

Use the IPython console tools to run code in the user's live kernels: state
persists between calls, figures are returned as images and also shown in
Spyder's Plots pane. Prefer the variable listing tool over printing large
objects. Code you run is visible to the user in their console.
"""


# ---- Auth
# -----------------------------------------------------------------------------
class BearerTokenMiddleware:
    """ASGI middleware that rejects HTTP requests without the right token."""

    def __init__(self, app, token: str) -> None:
        self.app = app
        self.expected = f"Bearer {token}".encode()

    async def __call__(self, scope, receive, send):
        if scope["type"] == "http":
            headers = dict(scope.get("headers") or [])
            received = headers.get(b"authorization", b"")
            if not hmac.compare_digest(received, self.expected):
                await send(
                    {
                        "type": "http.response.start",
                        "status": 401,
                        "headers": [(b"content-type", b"text/plain")],
                    }
                )
                await send(
                    {"type": "http.response.body", "body": b"Unauthorized"}
                )
                return

        await self.app(scope, receive, send)


# ---- MCP server
# -----------------------------------------------------------------------------
def to_content(item: dict) -> types.ContentBlock:
    """Convert a bridge content dict to an MCP content block."""
    if item.get("type") == "image":
        return types.ImageContent(
            type="image", data=item["data"], mime_type=item["mimeType"]
        )
    return types.TextContent(type="text", text=item.get("text", ""))


def get_client(ctx) -> dict | None:
    """Identify the client of a request from its HTTP headers."""
    headers = getattr(getattr(ctx, "request", None), "headers", None)
    if headers is None:
        return None

    client_id = headers.get(CLIENT_ID_HEADER)
    if client_id:
        return {
            "id": client_id,
            "name": headers.get(CLIENT_NAME_HEADER) or client_id,
        }

    session_id = headers.get("mcp-session-id")
    if session_id:
        return {"id": f"mcp-session:{session_id}", "name": "External agent"}

    # The 2026-07-28 protocol has no sessions, so all the clients of the
    # same kind look the same
    params = getattr(getattr(ctx, "session", None), "client_params", None)
    info = getattr(params, "client_info", None)
    if info is not None and info.name:
        return {
            "id": f"mcp-client:{info.name}",
            "name": f"External agent ({info.title or info.name})",
        }
    return None


def can_ask_user(ctx) -> bool:
    """
    Whether the client of a request can ask its user (it supports form
    elicitation and, on protocols before 2026-07-28, can receive requests
    now).
    """
    session = getattr(ctx, "session", None)
    capabilities = getattr(session, "client_capabilities", None)
    if capabilities is None or getattr(
        capabilities, "elicitation", None
    ) is None:
        return False
    return bool(
        getattr(session, "can_send_request", False)
        or is_modern(ctx)
    )


def is_modern(ctx) -> bool:
    """
    Whether a request uses the 2026-07-28 protocol or a later one, where
    the server can't send requests to the client while a tool call runs.
    Instead, the call returns an "input required" result and the client
    makes it again with the answers.
    """
    return getattr(ctx, "protocol_version", None) in MODERN_PROTOCOL_VERSIONS


def question_schema(params: dict) -> dict:
    """Elicitation form schema for one of Spyder's questions."""
    choice = {
        "type": "string",
        "title": params.get("title") or "Choice",
        "enum": params["choices"],
    }
    if params.get("default") in params["choices"]:
        choice["default"] = params["default"]
    return {
        "type": "object",
        "properties": {"choice": choice},
        "required": ["choice"],
    }


def to_answer(response) -> dict:
    """Spyder's answer from an elicitation result (or its wire dict)."""
    if response is None:
        return {"action": "cancel", "choice": None}
    if isinstance(response, dict):
        action = response.get("action")
        content = response.get("content")
    else:
        action = getattr(response, "action", None)
        content = getattr(response, "content", None)
    return {
        "action": action or "cancel",
        "choice": (content or {}).get("choice"),
    }


class RunningCall:
    """
    A tool call that Spyder is running.

    With the 2026-07-28 protocol, it outlives the request that started it
    when Spyder asks the client's user something: the request returns the
    question, and the call goes on when the client makes it again with the
    answer.
    """

    def __init__(self, call_id: str, ctx, client: dict | None) -> None:
        self.call_id = call_id
        self.ctx = ctx
        self.client = client
        self.task: asyncio.Task | None = None
        self.progress = 0
        self.question: dict | None = None
        self.answer: asyncio.Future | None = None
        self.asked = asyncio.Event()
        self.expiry: asyncio.TimerHandle | None = None

    def ask(self, params: dict) -> asyncio.Future:
        """Ask the client's user a question, answered in a later request."""
        self.question = params
        self.answer = asyncio.get_running_loop().create_future()
        self.asked.set()
        return self.answer

    def give_answer(self, answer: dict) -> None:
        if self.expiry is not None:
            self.expiry.cancel()
            self.expiry = None
        if self.answer is not None and not self.answer.done():
            self.answer.set_result(answer)
        self.question = self.answer = None


def create_mcp_server(peer: JsonRpcPeer) -> Server:
    """Create the MCP server forwarding tools to Spyder through ``peer``."""

    async def on_list_tools(ctx, params) -> types.ListToolsResult:
        tools = await peer.request(BridgeMethods.ListTools)
        return types.ListToolsResult(
            tools=[types.Tool.model_validate(tool) for tool in tools]
        )

    # Tool calls running, so Spyder can ask their client's user or report
    # progress while they run
    calls: dict[str, RunningCall] = {}

    def error_result(text: str) -> types.CallToolResult:
        return types.CallToolResult(
            content=[types.TextContent(type="text", text=text)],
            is_error=True,
        )

    def forget(call: RunningCall) -> None:
        if calls.get(call.call_id) is call:
            del calls[call.call_id]
        if call.expiry is not None:
            call.expiry.cancel()

    def expire(call: RunningCall) -> None:
        """The client didn't come back with an answer, so give up on it."""
        call.expiry = None
        call.give_answer({"action": "cancel", "choice": None})
        # Nobody is waiting for the result anymore
        forget(call)

    async def on_call_tool(
        ctx, params
    ) -> types.CallToolResult | types.InputRequiredResult:
        client = get_client(ctx)
        if params.request_state is not None:
            # The client answers a question Spyder asked during the call
            call = calls.get(params.request_state)
            if call is None or call.client != client:
                return error_result(
                    "Spyder no longer waits for an answer to this call."
                )
            call.ctx = ctx
            responses = params.input_responses or {}
            call.give_answer(to_answer(responses.get(QUESTION_KEY)))
        else:
            call = RunningCall(uuid.uuid4().hex, ctx, client)
            calls[call.call_id] = call
            call.task = asyncio.ensure_future(
                peer.request(
                    BridgeMethods.CallTool,
                    {
                        "name": params.name,
                        "arguments": params.arguments or {},
                        "client": client,
                        "callId": call.call_id,
                        "canAskUser": can_ask_user(ctx),
                    },
                )
            )
            # Its result is dropped if the client never comes back
            call.task.add_done_callback(
                lambda task: task.cancelled() or task.exception()
            )

        asked = asyncio.ensure_future(call.asked.wait())
        try:
            await asyncio.wait(
                {call.task, asked}, return_when=asyncio.FIRST_COMPLETED
            )
        except asyncio.CancelledError:
            # The client went away
            call.task.cancel()
            forget(call)
            raise
        finally:
            asked.cancel()

        if not call.task.done():
            # Spyder asks the user, so the client has to come back with
            # the answer
            call.asked.clear()
            call.expiry = asyncio.get_running_loop().call_later(
                ANSWER_TIMEOUT, expire, call
            )
            return types.InputRequiredResult(
                input_requests={
                    QUESTION_KEY: types.ElicitRequest(
                        params=types.ElicitRequestFormParams(
                            message=call.question["message"],
                            requested_schema=question_schema(call.question),
                        )
                    )
                },
                request_state=call.call_id,
            )

        forget(call)
        try:
            result = call.task.result()
        except BridgeError as error:
            return error_result(str(error))

        return types.CallToolResult(
            content=[to_content(item) for item in result["content"]],
            is_error=result.get("isError", False),
        )

    async def on_ask_user(params: dict) -> dict:
        """
        Ask the user of the client that made a tool call to choose one of
        ``choices`` (an elicitation form).
        """
        call = calls.get(params["callId"])
        if call is None or not can_ask_user(call.ctx):
            return {"action": "cancel", "choice": None}

        if is_modern(call.ctx):
            return await call.ask(params)

        ctx = call.ctx
        result = await ctx.session.elicit_form(
            params["message"],
            question_schema(params),
            related_request_id=ctx.request_id,
        )
        return to_answer(result)

    async def on_report_progress(params: dict) -> None:
        """Report progress of a tool call, if its client asked for it."""
        call = calls.get(params["callId"])
        if call is None:
            return
        call.progress += 1
        try:
            await call.ctx.session.report_progress(
                call.progress, message=params.get("message")
            )
        except Exception:
            # E.g. the request that the progress was for is done because
            # the client has to answer a question
            logger.debug("Couldn't report progress", exc_info=True)

    peer.set_handler(BridgeMethods.AskUser, on_ask_user)
    peer.set_handler(BridgeMethods.ReportProgress, on_report_progress)

    return Server(
        "spyder",
        title="Spyder IDE",
        instructions=INSTRUCTIONS,
        on_list_tools=on_list_tools,
        on_call_tool=on_call_tool,
    )


async def serve(host: str, port: int, token: str) -> None:
    peer = JsonRpcPeer.from_stdio()
    server = create_mcp_server(peer)

    async def notes_endpoint(request) -> JSONResponse:
        """Notes for a client (``?client=<id>``), which are then forgotten."""
        client_id = request.query_params.get("client")
        notes = []
        if client_id:
            notes = await peer.request(
                BridgeMethods.TakeNotes, {"clientId": client_id}
            )
        return JSONResponse({"notes": notes})

    mcp_app = server.streamable_http_app(
        streamable_http_path=MCP_PATH, host=host
    )
    mcp_app.router.routes.insert(
        0, Route(NOTES_PATH, notes_endpoint, methods=["GET"])
    )
    app = BearerTokenMiddleware(mcp_app, token)
    config = uvicorn.Config(
        app, host=host, port=port, log_level="warning", lifespan="on"
    )
    http_server = uvicorn.Server(config)

    http_task = asyncio.create_task(http_server.serve())
    bridge_task = asyncio.create_task(peer.run())

    # Tell Spyder where we are once the socket is listening
    while not http_server.started:
        if http_task.done():
            # Startup failed (e.g. port already in use)
            await http_task
            raise SystemExit(1)
        await asyncio.sleep(0.05)

    await peer.notify(
        BridgeMethods.ServerReady, {"url": f"http://{host}:{port}{MCP_PATH}"}
    )

    # Spyder closed our stdin (or died), so shut down
    await bridge_task
    http_server.should_exit = True
    await http_task


def main() -> None:
    parser = argparse.ArgumentParser(description="Spyder MCP server")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, required=True)
    parser.add_argument("--debug", action="store_true")
    args = parser.parse_args()

    logging.basicConfig(
        stream=sys.stderr,
        level=logging.DEBUG if args.debug else logging.WARNING,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    token = os.environ.pop(TOKEN_ENV_VAR, "")
    if not token:
        sys.exit(f"The {TOKEN_ENV_VAR} environment variable must be set")

    asyncio.run(serve(args.host, args.port, token))


if __name__ == "__main__":
    main()
