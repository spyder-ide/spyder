# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""
Dispatch tool calls from MCP clients (e.g. agent sessions).

Calls run on behalf of their client (see
:func:`spyder.api.plugins.exposed.calling_as`), with the default arguments
set for that client (e.g. the console a session works in). When a client
calls a tool that changes state without giving an argument that has an
asker, and it has no default for it, the asker is used to ask the user.
"""

# Standard library imports
from __future__ import annotations

from collections.abc import Callable
from concurrent.futures import Future
import logging
from typing import Any

# Local imports
from spyder.api.plugins.exposed import Caller, ExposedCallError, calling_as
from spyder.plugins.mcpserver.api import (
    CallContext,
    Content,
    MCPTool,
    text_content,
)
from spyder.plugins.mcpserver.focus import call_tool_keeping_focus

logger = logging.getLogger(__name__)

OnDone = Callable[[list[Content], bool], None]

ArgumentAsker = Callable[[Caller, MCPTool, CallContext], Any]
"""
Function that asks the user for the value of an argument of a tool call
from a client. It returns the value, a future resolved with it, or ``None``
(or a future resolved with ``None``) to call the tool without it. It can
raise (or resolve with) an :class:`ExposedCallError` to cancel the call.

The :class:`CallContext` lets it ask the question through the client (e.g.
in the agent's interface, where the user is looking) when the client
supports it, or report that the call is waiting for the user.
"""


class ToolDispatcher:
    """Run tool calls on behalf of their clients."""

    def __init__(self, get_tools: Callable[[], dict[str, MCPTool]]) -> None:
        self._get_tools = get_tools
        self._clients: dict[str, Caller] = {}
        self._client_arguments: dict[str, dict[str, Any]] = {}
        self._askers: dict[str, ArgumentAsker] = {}

        # Number of calls running for each client
        self._running: dict[str, int] = {}

        # Notes for each client about what happened in Spyder since its
        # last call (e.g. the user opened a project)
        self._notes: dict[str, list[str]] = {}

        # Called with each call's caller, tool and arguments before it runs
        self._call_observer: Callable | None = None

    # ---- Clients
    def get_clients(self) -> list[Caller]:
        """
        Return the clients that have called tools or were registered with
        :meth:`register_client`.
        """
        return list(self._clients.values())

    def register_client(self, client_id: str, name: str) -> None:
        """
        Register a client before it calls any tool (e.g. an agent session
        started by a plugin), so it gets notes from the start.
        """
        self._clients[client_id] = Caller(client_id, name)

    def unregister_client(self, client_id: str) -> None:
        """Forget a client, e.g. when its session ends."""
        self._clients.pop(client_id, None)
        self._notes.pop(client_id, None)
        self._client_arguments.pop(client_id, None)

    def get_running_calls(self, client_id: str) -> int:
        """Number of tool calls of a client that are running."""
        return self._running.get(client_id, 0)

    # ---- Notes
    def notify_clients(self, message: str, exclude: str | None = None) -> None:
        """
        Leave a note for all clients (except ``exclude``, e.g. the one that
        caused it) about something that happened in Spyder. They get it with
        their next tool call's result, or with :meth:`take_notes`.
        """
        for client_id in self._clients:
            if client_id != exclude:
                self._notes.setdefault(client_id, []).append(message)

    def notify_client(self, client_id: str, message: str) -> None:
        """Leave a note for one client (see :meth:`notify_clients`)."""
        if client_id in self._clients:
            self._notes.setdefault(client_id, []).append(message)

    def set_call_observer(
        self, observer: Callable[[Caller, MCPTool, dict], None] | None
    ) -> None:
        """
        Call ``observer`` with the caller, tool and arguments (with the
        client's defaults and the user's answers) of each call from a client
        before it runs, e.g. to know which consoles each client uses.
        """
        self._call_observer = observer

    def take_notes(self, client_id: str) -> list[str]:
        """Return the notes for a client and forget them."""
        return self._notes.pop(client_id, [])

    def set_client_argument(
        self, client_id: str, name: str, value: Any
    ) -> None:
        """
        Set the value of argument ``name`` used when the client doesn't give
        one, or remove it if ``value`` is ``None``.
        """
        arguments = self._client_arguments.setdefault(client_id, {})
        if value is None:
            arguments.pop(name, None)
        else:
            arguments[name] = value

    def get_client_argument(self, client_id: str, name: str) -> Any:
        return self._client_arguments.get(client_id, {}).get(name)

    def get_busy_clients(self) -> set[str]:
        """
        Ids of the clients with tool calls running, including calls waiting
        for the user to answer an asker.
        """
        return {
            client_id
            for client_id, count in self._running.items()
            if count > 0
        }

    def register_argument_asker(
        self, name: str, asker: ArgumentAsker | None
    ) -> None:
        """Set (or remove, with ``None``) the asker for argument ``name``."""
        if asker is None:
            self._askers.pop(name, None)
        else:
            self._askers[name] = asker

    # ---- Calls
    def call(
        self,
        name: str,
        arguments: dict,
        client: dict | None,
        on_done: OnDone,
        context: CallContext | None = None,
    ) -> None:
        """
        Call tool ``name`` from ``client`` (a dict with its ``id`` and
        ``name``, or ``None``) in the main Qt thread.

        ``context`` lets askers reach the client while the call runs.
        """
        context = context or CallContext()
        tool = self._get_tools().get(name)
        if tool is None:
            on_done([text_content(f"Unknown tool: {name}")], True)
            return

        caller = None
        if client and client.get("id"):
            caller = Caller(client["id"], client.get("name") or client["id"])
            self._clients[caller.id] = caller

            # Track the call until it finishes, and add the client's notes
            # to its result
            self._running[caller.id] = self._running.get(caller.id, 0) + 1
            client_done = on_done

            def on_done(content, is_error, _client_id=caller.id):
                self._running[_client_id] -= 1
                notes = self.take_notes(_client_id)
                if notes:
                    content = [text_content(format_notes(notes))] + list(
                        content
                    )
                client_done(content, is_error)

        arguments = dict(arguments)
        to_ask = []
        for argument in tool.input_schema.get("properties", {}):
            if argument in arguments or caller is None:
                continue
            default = self.get_client_argument(caller.id, argument)
            if default is not None:
                arguments[argument] = default
            elif argument in self._askers and not tool.read_only:
                to_ask.append(argument)

        self._ask(tool, caller, arguments, to_ask, on_done, context)

    def _ask(
        self, tool, caller, arguments, to_ask, on_done, context
    ) -> None:
        if not to_ask:
            if self._call_observer is not None and caller is not None:
                try:
                    self._call_observer(caller, tool, arguments)
                except Exception:
                    logger.debug("Error observing a call", exc_info=True)
            with calling_as(caller, context):
                call_tool_keeping_focus(tool, arguments, on_done)
            return

        argument = to_ask[0]

        def got(value):
            if value is not None:
                arguments[argument] = value
            self._ask(tool, caller, arguments, to_ask[1:], on_done, context)

        def failed(error):
            if isinstance(error, ExposedCallError):
                on_done([text_content(str(error))], True)
            else:
                logger.error(
                    "Error asking for %s", argument, exc_info=error
                )
                on_done(
                    [text_content(f"Internal error asking for {argument}")],
                    True,
                )

        try:
            result = self._askers[argument](caller, tool, context)
        except Exception as error:
            failed(error)
            return

        if not isinstance(result, Future):
            got(result)
            return

        def on_answer(future):
            try:
                value = future.result()
            except Exception as error:
                failed(error)
            else:
                got(value)

        result.add_done_callback(on_answer)


def format_notes(notes: list[str]) -> str:
    """Notes for a client, as text for it."""
    return "Since your last call, in Spyder:\n" + "\n".join(
        f"- {note}" for note in notes
    )
