# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""
JSON-RPC 2.0 peer used to talk between Spyder and the MCP server subprocess.

Messages are newline-delimited JSON objects sent over the subprocess stdio.
Both ends can send requests and notifications, so the same class is used on
the Spyder side and in the subprocess.

This module must not import Qt, since it's also used by the subprocess.
"""

# Standard library imports
from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
import itertools
import json
import logging
import sys
from typing import Any

logger = logging.getLogger(__name__)

Handler = Callable[[dict], Awaitable[Any]]

# Environment variable used to pass the auth token to the server subprocess
TOKEN_ENV_VAR = "SPYDER_MCP_TOKEN"


# ---- Bridge methods
# -----------------------------------------------------------------------------
# HTTP headers clients send to say who they are, e.g. each agent session
# started from Spyder. Clients without them are identified by their MCP
# session.
# Endpoint where clients get their notes (what happened in Spyder since
# their last tool call) outside of tool calls, e.g. from agent hooks
NOTES_PATH = "/spyder/notes"

CLIENT_ID_HEADER = "X-Spyder-Client-Id"
CLIENT_NAME_HEADER = "X-Spyder-Client-Name"


class BridgeMethods:
    """Methods exchanged between Spyder and the MCP server subprocess."""

    # Subprocess -> Spyder (requests)
    ListTools = "spyder/listTools"
    CallTool = "spyder/callTool"
    TakeNotes = "spyder/takeNotes"

    # Subprocess -> Spyder (notifications)
    ServerReady = "server/ready"

    # Spyder -> subprocess, for a tool call that is running: ask the user of
    # the client that made it (request) or report progress (notification)
    AskUser = "server/askUser"
    ReportProgress = "server/reportProgress"


class BridgeError(Exception):
    """Error returned by the other end of the bridge."""

    def __init__(self, message: str, code: int = -32000):
        super().__init__(message)
        self.code = code


# ---- Peer
# -----------------------------------------------------------------------------
class JsonRpcPeer:
    """
    Minimal JSON-RPC 2.0 peer over a line-based stream.

    Parameters
    ----------
    readline : Callable
        Coroutine function returning the next line as bytes, or ``b""`` on
        EOF.
    write : Callable
        Coroutine function that writes bytes to the other end.
    handlers : dict
        Mapping from method names to coroutine functions taking the request
        params. Their return value is sent back as the result for requests
        and ignored for notifications.
    """

    def __init__(
        self,
        readline: Callable[[], Awaitable[bytes]],
        write: Callable[[bytes], Awaitable[None]],
        handlers: dict[str, Handler] | None = None,
    ) -> None:
        self._readline = readline
        self._write = write
        self._handlers = handlers or {}
        self._ids = itertools.count(1)
        self._pending: dict[int, asyncio.Future] = {}
        self._write_lock = asyncio.Lock()
        self._tasks: set[asyncio.Task] = set()

    @classmethod
    def from_stdio(cls, handlers: dict[str, Handler] | None = None):
        """
        Create a peer over this process' stdin and stdout.

        This is meant for subprocesses started by Spyder. Nothing else may
        write to stdout afterwards, so ``sys.stdout`` is redirected to stderr.
        """
        stdin = sys.stdin.buffer
        stdout = sys.stdout.buffer
        sys.stdout = sys.stderr

        async def readline() -> bytes:
            # Reading in a thread is portable, unlike connect_read_pipe on
            # Windows
            return await asyncio.to_thread(stdin.readline)

        async def write(data: bytes) -> None:
            stdout.write(data)
            stdout.flush()

        return cls(readline, write, handlers)

    # ---- Public API
    def set_handler(self, method: str, handler: Handler) -> None:
        """Handle requests or notifications of ``method`` with ``handler``."""
        self._handlers[method] = handler

    async def request(self, method: str, params: dict | None = None) -> Any:
        """Send a request and wait for its result."""
        msg_id = next(self._ids)
        future = asyncio.get_running_loop().create_future()
        self._pending[msg_id] = future
        try:
            await self._send(
                {"jsonrpc": "2.0", "id": msg_id, "method": method,
                 "params": params or {}}
            )
            return await future
        finally:
            self._pending.pop(msg_id, None)

    async def notify(self, method: str, params: dict | None = None) -> None:
        """Send a notification (no response expected)."""
        await self._send(
            {"jsonrpc": "2.0", "method": method, "params": params or {}}
        )

    async def run(self) -> None:
        """Read and dispatch messages until the stream reaches EOF."""
        try:
            while True:
                line = await self._readline()
                if not line:
                    break
                line = line.strip()
                if not line:
                    continue

                try:
                    message = json.loads(line)
                except ValueError:
                    logger.error("Invalid bridge message: %r", line[:200])
                    continue

                self._dispatch(message)
        finally:
            for future in self._pending.values():
                if not future.done():
                    future.set_exception(
                        BridgeError("Bridge connection closed")
                    )

    # ---- Private API
    async def _send(self, message: dict) -> None:
        data = json.dumps(message).encode("utf-8") + b"\n"
        async with self._write_lock:
            await self._write(data)

    def _dispatch(self, message: dict) -> None:
        if "method" in message:
            # Run handlers as tasks so a slow one doesn't block the read loop
            task = asyncio.ensure_future(self._handle_incoming(message))
            self._tasks.add(task)
            task.add_done_callback(self._tasks.discard)
        elif "id" in message:
            future = self._pending.get(message["id"])
            if future is None or future.done():
                return

            if "error" in message:
                error = message["error"]
                future.set_exception(
                    BridgeError(error.get("message", ""), error.get("code"))
                )
            else:
                future.set_result(message.get("result"))

    async def _handle_incoming(self, message: dict) -> None:
        method = message["method"]
        msg_id = message.get("id")
        handler = self._handlers.get(method)

        if handler is None:
            if msg_id is not None:
                await self._send_error(
                    msg_id, f"Method not found: {method}", -32601
                )
            return

        try:
            result = await handler(message.get("params") or {})
        except Exception as error:
            if msg_id is None:
                logger.exception("Error handling notification %s", method)
            else:
                await self._send_error(msg_id, str(error) or repr(error))
            return

        if msg_id is not None:
            await self._send(
                {"jsonrpc": "2.0", "id": msg_id, "result": result}
            )

    async def _send_error(
        self, msg_id: int, message: str, code: int = -32000
    ) -> None:
        await self._send(
            {"jsonrpc": "2.0", "id": msg_id,
             "error": {"code": code, "message": message}}
        )
