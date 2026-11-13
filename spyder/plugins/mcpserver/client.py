# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""
Client that runs the MCP server subprocess and answers its requests.

All the communication with the subprocess happens in a dedicated asyncio
thread (managed by AsyncDispatcher), while tools always run in the main Qt
thread.
"""

# Standard library imports
from __future__ import annotations

import asyncio
from collections import deque
from collections.abc import Callable
from concurrent.futures import Future
import logging
import os
import sys

# Third-party imports
from qtpy.QtCore import QObject, Signal

# Local imports
from spyder.api.asyncdispatcher import AsyncDispatcher, DispatcherFuture
from spyder.config.base import get_debug_level
from spyder.plugins.mcpserver.api import CallContext, MCPTool
from spyder.plugins.mcpserver.bridge import (
    BridgeMethods,
    JsonRpcPeer,
    TOKEN_ENV_VAR,
)

logger = logging.getLogger(__name__)

# Lines of the server's output kept to report why it exited
OUTPUT_TAIL = 30

# Global loop name for AsyncDispatcher in the MCP client.
_MCP_LOOP = "mcp"

# Maximum time a tool call can take before giving up on it.
TOOL_CALL_TIMEOUT = 30 * 60


class MCPServerClient(QObject):
    """Start the MCP server subprocess and route its requests to Spyder."""

    _sig_resolve = Signal(object, object)
    """Resolve a future with a value in the main Qt thread."""

    sig_server_ready = Signal(str)
    """
    This signal is emitted when the server is accepting connections.

    Parameters
    ----------
    url : str
        URL of the MCP endpoint.
    """

    sig_server_stopped = Signal(int)
    """
    This signal is emitted when the server process exits.

    Parameters
    ----------
    returncode : int
        Exit code of the process.
    """

    def __init__(
        self,
        parent,
        get_tools: Callable[[], dict[str, MCPTool]],
        call_tool: Callable[[str, dict, dict | None, Callable], None],
        take_notes: Callable[[str], list[str]] | None = None,
    ) -> None:
        """
        Parameters
        ----------
        get_tools : Callable
            Function that returns the tools available to agents, by name. It's
            called in the main Qt thread for every request.
        call_tool : Callable
            Function called in the main Qt thread with the ``name``,
            ``arguments`` and ``client`` of a tool call, and a function to
            call with ``(content, is_error)`` when it finishes.
        take_notes : Callable, optional
            Function called in the main Qt thread with a client id, that
            returns the notes for that client and forgets them.
        """
        super().__init__(parent)
        self._get_tools = get_tools
        self._call_tool = call_tool
        self._take_notes = take_notes or (lambda client_id: [])
        self._process: asyncio.subprocess.Process | None = None
        self.url: str | None = None

        # Whether the server is starting (its process is created
        # asynchronously) or being stopped on purpose
        self._starting = False
        self._stopping = False
        self._output: deque[str] = deque(maxlen=OUTPUT_TAIL)

        self.exited_unexpectedly = False
        """Whether the server's last exit wasn't requested with stop."""

        self._peer: JsonRpcPeer | None = None
        self._sig_resolve.connect(self._resolve)

    # ---- Public API
    # -------------------------------------------------------------------------
    @property
    def is_running(self) -> bool:
        return self._process is not None and self._process.returncode is None

    def start(self, host: str, port: int, token: str) -> None:
        """
        Start the server subprocess, unless it's running or starting (e.g.
        if several clients ask for it at once).
        """
        if self.is_running or self._starting:
            return
        self._starting = True
        self._stopping = False
        self._run(host, port, token)

    def stop(self) -> None:
        """Stop the server subprocess."""
        if not self.is_running:
            return
        self._stopping = True
        try:
            self._stop().result(timeout=5)
        except Exception:
            logger.exception("Error stopping the MCP server")

    # ---- Asyncio side
    # -------------------------------------------------------------------------
    @AsyncDispatcher(loop=_MCP_LOOP)
    async def _run(self, host: str, port: int, token: str) -> None:
        args = [
            sys.executable, "-m", "spyder.plugins.mcpserver.server",
            "--host", host,
            "--port", str(port),
        ]
        if get_debug_level() > 0:
            args.append("--debug")

        # Pass the token through the environment so it's not visible in the
        # process list
        env = dict(os.environ, **{TOKEN_ENV_VAR: token})

        logger.info("Starting MCP server: %s", " ".join(args))
        try:
            self._process = await asyncio.create_subprocess_exec(
                *args,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=env,
            )
        except OSError:
            logger.exception("Could not start the MCP server")
            self._starting = False
            self.exited_unexpectedly = True
            self.sig_server_stopped.emit(-1)
            return
        finally:
            self._starting = False

        process = self._process
        self._output.clear()

        async def write(data: bytes) -> None:
            process.stdin.write(data)
            await process.stdin.drain()

        peer = JsonRpcPeer(
            process.stdout.readline,
            write,
            {
                BridgeMethods.ListTools: self._handle_list_tools,
                BridgeMethods.CallTool: self._handle_call_tool,
                BridgeMethods.TakeNotes: self._handle_take_notes,
                BridgeMethods.ServerReady: self._handle_server_ready,
            },
        )
        self._peer = peer

        await asyncio.gather(peer.run(), self._log_stderr(process))
        returncode = await process.wait()
        self.url = None
        self.exited_unexpectedly = not self._stopping
        if self.exited_unexpectedly:
            logger.error(
                "The MCP server exited unexpectedly with code %s. Its last "
                "output was:\n%s",
                returncode,
                "\n".join(self._output) or "(none)",
            )
        else:
            logger.info("MCP server exited with code %s", returncode)
        self.sig_server_stopped.emit(returncode)

    @AsyncDispatcher(loop=_MCP_LOOP)
    async def _stop(self) -> None:
        process = self._process
        if process is None or process.returncode is not None:
            return

        # The server exits on its own when its stdin is closed
        process.stdin.close()
        try:
            await asyncio.wait_for(process.wait(), timeout=3)
        except asyncio.TimeoutError:
            process.kill()
            await process.wait()

    async def _log_stderr(self, process: asyncio.subprocess.Process) -> None:
        while line := await process.stderr.readline():
            text = line.decode(errors="replace").rstrip()
            self._output.append(text)
            logger.debug("[server] %s", text)

    async def _handle_server_ready(self, params: dict) -> None:
        self.url = params["url"]
        logger.info("MCP server listening at %s", self.url)
        self.sig_server_ready.emit(self.url)

    async def _handle_list_tools(self, params: dict) -> list[dict]:
        return await self._run_in_qt(
            lambda done: done(
                [tool.to_dict() for tool in self._get_tools().values()]
            )
        )

    async def _handle_take_notes(self, params: dict) -> list[str]:
        return await self._run_in_qt(
            lambda done: done(self._take_notes(params["clientId"]))
        )

    async def _handle_call_tool(self, params: dict) -> dict:
        name = params["name"]
        arguments = params.get("arguments") or {}
        client = params.get("client")
        context = _ServerCallContext(
            self, params.get("callId"), bool(params.get("canAskUser"))
        )

        def call_tool(done: Callable) -> None:
            logger.debug("Calling MCP tool %s(%s)", name, arguments)
            self._call_tool(
                name,
                arguments,
                client,
                lambda content, is_error: done(
                    {"content": content, "isError": is_error}
                ),
                context,
            )

        try:
            return await asyncio.wait_for(
                self._run_in_qt(call_tool), TOOL_CALL_TIMEOUT
            )
        except asyncio.TimeoutError:
            raise TimeoutError(f"Tool {name} didn't finish in time") from None

    @AsyncDispatcher(loop=_MCP_LOOP)
    async def _ask_user(
        self,
        call_id: str,
        message: str,
        choices: list[str],
        title: str,
        default: str | None,
        future: Future,
    ) -> None:
        choice = None
        try:
            answer = await self._peer.request(
                BridgeMethods.AskUser,
                {
                    "callId": call_id,
                    "message": message,
                    "choices": choices,
                    "title": title,
                    "default": default,
                },
            )
            if answer.get("action") == "accept":
                choice = answer.get("choice")
        except Exception:
            logger.debug("Could not ask the client's user", exc_info=True)
        self._sig_resolve.emit(future, choice)

    @AsyncDispatcher(loop=_MCP_LOOP)
    async def _report_progress(self, call_id: str, message: str) -> None:
        try:
            await self._peer.notify(
                BridgeMethods.ReportProgress,
                {"callId": call_id, "message": message},
            )
        except Exception:
            logger.debug("Could not report progress", exc_info=True)

    def _resolve(self, future: Future, value) -> None:
        if not future.done():
            future.set_result(value)

    async def _run_in_qt(self, func: Callable[[Callable], None]):
        """
        Run ``func(done)`` in the Qt main thread and wait until it calls
        ``done(result)``, which can happen later from a Qt callback.
        """
        loop = asyncio.get_running_loop()
        result = loop.create_future()

        def done(value) -> None:
            loop.call_soon_threadsafe(_set_result, result, value)

        @AsyncDispatcher.QtSlot
        def run(_future) -> None:
            try:
                func(done)
            except Exception as error:
                loop.call_soon_threadsafe(_set_exception, result, error)

        trigger = DispatcherFuture()
        trigger.set_result(None)
        trigger.connect(run)

        return await result


def _set_result(future: asyncio.Future, value) -> None:
    if not future.done():
        future.set_result(value)


def _set_exception(future: asyncio.Future, error: Exception) -> None:
    if not future.done():
        future.set_exception(error)


class _ServerCallContext(CallContext):
    """Context of a tool call made through the MCP server subprocess."""

    def __init__(
        self, client: MCPServerClient, call_id: str | None, can_ask_user: bool
    ) -> None:
        self._client = client
        self._call_id = call_id
        self.can_ask_user = can_ask_user and call_id is not None

    def ask_user(
        self,
        message: str,
        choices: list[str],
        title: str = "",
        default: str | None = None,
    ) -> Future:
        if not self.can_ask_user:
            return super().ask_user(message, choices, title, default)
        future: Future = Future()
        self._client._ask_user(
            self._call_id, message, choices, title, default, future
        )
        return future

    def report_progress(self, message: str) -> None:
        if self._call_id is not None:
            self._client._report_progress(self._call_id, message)
