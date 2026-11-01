# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""
MCP server plugin API.

The MCP server exposes to AI agents the plugin methods marked with
:func:`spyder.api.plugins.expose`, so plugins usually don't need to use this
module. It's for tools that only make sense for MCP, which can be registered
directly with :meth:`MCPServer.register_tool`::

    @on_plugin_available(plugin=Plugins.MCPServer)
    def on_mcp_server_available(self):
        mcp_server = self.get_plugin(Plugins.MCPServer)
        mcp_server.register_tool(
            MCPTool(
                name="my_plugin_do_something",
                description="Do something useful.",
                handler=self._do_something,
                read_only=True,
            )
        )

Handlers always run in the main Qt thread. They receive a :class:`ToolCall`
and can either return the result right away (a string, a content dict or a
list of them) or return ``None`` and call :meth:`ToolCall.reply` later, e.g.
from a kernel callback.

Plugins that start agents
-------------------------
Plugins that run agent sessions in Spyder (e.g. in a terminal pane) use the
MCP server plugin to connect them and tell them apart:

* :meth:`MCPServer.start_server` starts the server for the plugin's
  sessions, even if the user didn't enable it, and
  :meth:`MCPServer.get_connection_info` gives the URL and HTTP headers that
  each session must send. The ``X-Spyder-Client-Id`` header identifies the
  session in tool calls, so exposed methods see it as their
  :func:`spyder.api.plugins.current_caller`.
* :meth:`MCPServer.register_client` lists a session before its first tool
  call, so it gets notes about what happens in Spyder from the start (see
  :meth:`MCPServer.notify_clients` and :meth:`MCPServer.get_notes_url`).
* :meth:`MCPServer.set_client_argument` sets default tool arguments for a
  session (e.g. the ``console_id`` it works in), and
  :meth:`MCPServer.register_argument_asker` asks the user for an argument
  when a session calls a tool without it.
"""

# Standard library imports
from __future__ import annotations

import base64
from collections.abc import Callable
from dataclasses import dataclass, field
import logging
from typing import Any, Union

# Local imports
from spyder.api.plugins.exposed import (  # noqa: F401
    CallContext,
    ExposedCallError,
)

logger = logging.getLogger(__name__)

Content = dict
ToolResult = Union[str, Content, list]

# Maximum length of text results, to avoid filling the agent's context.
MAX_OUTPUT_CHARS = 50000


# ---- Content helpers
# -----------------------------------------------------------------------------
def text_content(text: str) -> Content:
    """Create a text content block."""
    return {"type": "text", "text": text}


def image_content(data: bytes | str, mime_type: str = "image/png") -> Content:
    """
    Create an image content block.

    ``data`` can be raw bytes or an already base64-encoded string.
    """
    if isinstance(data, bytes):
        data = base64.b64encode(data).decode("ascii")
    return {"type": "image", "data": data, "mimeType": mime_type}


def truncate(text: str, max_chars: int = MAX_OUTPUT_CHARS) -> str:
    """Keep the start and end of ``text`` if it's too long."""
    if len(text) <= max_chars:
        return text

    half = max_chars // 2
    skipped = len(text) - 2 * half
    return (
        f"{text[:half]}\n\n[... {skipped} characters omitted ...]\n\n"
        f"{text[-half:]}"
    )


def svg_to_png(svg: str | bytes) -> bytes:
    """
    Render an SVG image to PNG.

    Agents can't read SVG images, so this is used to send them figures.
    """
    from qtconsole.svg import svg_to_image
    from qtpy.QtCore import QBuffer, QByteArray, QIODevice

    image = svg_to_image(svg)
    data = QByteArray()
    buffer = QBuffer(data)
    buffer.open(QIODevice.WriteOnly)
    image.save(buffer, "PNG")
    return bytes(data)


def _normalize_content(result: ToolResult) -> list[Content]:
    if isinstance(result, (str, dict)):
        result = [result]
    return [
        text_content(item) if isinstance(item, str) else item
        for item in result
    ]


# ---- Tools
# -----------------------------------------------------------------------------
class ToolError(Exception):
    """Raise from a tool handler to report an error to the agent."""


class ToolCall:
    """
    A single call to a tool, passed to its handler.

    Parameters
    ----------
    arguments : dict
        Arguments sent by the agent, following the tool's input schema.
    on_done : Callable
        Function called with ``(content, is_error)`` once the call finishes.
    """

    def __init__(
        self,
        arguments: dict,
        on_done: Callable[[list[Content], bool], None],
    ) -> None:
        self.arguments = arguments
        self._on_done = on_done
        self.finished = False

    def reply(self, result: ToolResult) -> None:
        """Finish the call successfully with ``result``."""
        self._finish(_normalize_content(result), False)

    def error(self, message: str) -> None:
        """Finish the call with an error message for the agent."""
        self._finish([text_content(message)], True)

    def _finish(self, content: list[Content], is_error: bool) -> None:
        if self.finished:
            logger.debug("Tool call already finished, ignoring result")
            return
        self.finished = True
        self._on_done(content, is_error)


@dataclass
class MCPTool:
    """
    A tool exposed to AI agents through the MCP server.

    Parameters
    ----------
    name : str
        Unique tool name. Prefix it with the plugin name to avoid clashes.
    description : str
        What the tool does and when to use it. Agents rely on this text to
        pick tools, so be specific.
    handler : Callable
        Function called in the main Qt thread with a :class:`ToolCall`.
    input_schema : dict
        JSON schema for the tool arguments.
    title : str, optional
        Human-readable name.
    read_only : bool
        Whether the tool doesn't modify any state.
    destructive : bool
        Whether the tool may make changes that can't be undone.
    plugin : str, optional
        Name of the plugin that provides the tool. Its tools are only listed
        while the plugin is available.
    """

    name: str
    description: str
    handler: Callable[[ToolCall], ToolResult | None]
    input_schema: dict = field(
        default_factory=lambda: {"type": "object", "properties": {}}
    )
    title: str | None = None
    read_only: bool = False
    destructive: bool = False
    plugin: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Return the MCP tool definition sent to agents."""
        tool = {
            "name": self.name,
            "description": self.description,
            "inputSchema": self.input_schema,
            "annotations": {
                "readOnlyHint": self.read_only,
                "destructiveHint": self.destructive,
            },
        }
        if self.title:
            tool["title"] = self.title
        return tool

    def call(self, call: ToolCall) -> None:
        """Run the handler, finishing ``call`` if it returns a result."""
        try:
            result = self.handler(call)
        except (ToolError, ExposedCallError) as error:
            call.error(str(error))
        except Exception as error:
            logger.exception("Error running MCP tool %s", self.name)
            call.error(f"Internal error in tool {self.name}: {error!r}")
        else:
            if result is not None:
                call.reply(result)
