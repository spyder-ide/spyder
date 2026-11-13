# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""Tests for turning exposed plugin methods into MCP tools."""

# Standard library imports
from __future__ import annotations

import base64
from concurrent.futures import Future
import json
from typing import Literal, Optional

# Third-party imports
import pytest

# Local imports
from spyder.api.plugins import ExposedCallError, Image, expose
from spyder.plugins.mcpserver.api import ToolCall
from spyder.plugins.mcpserver.exposed import (
    annotation_to_schema,
    parse_docstring,
    result_to_content,
    tools_from_plugin,
)

PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChw"
    "GA60e6kgAAAABJRU5ErkJggg=="
)


class FakePlugin:
    """Plugin with exposed methods."""

    def __init__(self):
        self.futures: list[Future] = []

    @expose(read_only=True)
    def greet(self, name: str, times: int = 1, loud: bool = False) -> str:
        """
        Greet someone.

        It can greet several times in a row,
        also loudly.

        Parameters
        ----------
        name : str
            Who to greet.
        times : int, optional
            How many times
            to greet.
        loud : bool
            Whether to shout.

        Returns
        -------
        str
            The greeting.
        """
        greeting = " ".join([f"Hello {name}"] * times)
        return greeting.upper() if loud else greeting

    @expose(name="get_data", destructive=True)
    def data(self, kind: Literal["image", "none", "dict"]) -> object:
        """Return some data."""
        if kind == "image":
            return Image(PNG)
        if kind == "none":
            return None
        return {"values": [1, 2], "plot": Image(PNG), "label": "x"}

    @expose
    def later(self) -> Future:
        """Finish later."""
        future = Future()
        self.futures.append(future)
        return future

    @expose
    def fail(self) -> None:
        """Always fails."""
        raise ExposedCallError("Can't do that, try something else.")

    @expose
    def crash(self) -> None:
        """Has a bug."""
        raise ValueError("bug")


class Results:
    """Collect the results of tool calls."""

    def __init__(self):
        self.calls = []

    def call(self, tool, **arguments):
        tool.call(
            ToolCall(
                arguments,
                lambda content, is_error: self.calls.append(
                    (content, is_error)
                ),
            )
        )
        return self.calls[-1] if self.calls else None


@pytest.fixture
def tools():
    plugin = FakePlugin()
    tools = {tool.name: tool for tool in tools_from_plugin(plugin, "fake")}
    tools["_plugin"] = plugin
    return tools


def test_tool_definitions(tools):
    greet = tools["greet"].to_dict()
    assert greet["description"] == (
        "Greet someone.\n\nIt can greet several times in a row, also loudly."
    )
    assert greet["annotations"] == {
        "readOnlyHint": True,
        "destructiveHint": False,
    }
    assert greet["inputSchema"] == {
        "type": "object",
        "properties": {
            "name": {"type": "string", "description": "Who to greet."},
            "times": {
                "type": "integer",
                "description": "How many times to greet.",
                "default": 1,
            },
            "loud": {
                "type": "boolean",
                "description": "Whether to shout.",
                "default": False,
            },
        },
        "required": ["name"],
    }

    data = tools["get_data"]
    assert data.destructive and not data.read_only
    assert data.plugin == "fake"
    assert data.input_schema["properties"]["kind"] == {
        "enum": ["image", "none", "dict"],
        "type": "string",
    }


def test_call_results(tools):
    results = Results()

    content, is_error = results.call(tools["greet"], name="Spyder", times=2)
    assert not is_error
    assert content == [{"type": "text", "text": "Hello Spyder Hello Spyder"}]

    content, _ = results.call(tools["get_data"], kind="none")
    assert content == [{"type": "text", "text": "Done."}]

    content, _ = results.call(tools["get_data"], kind="image")
    assert content == [
        {
            "type": "image",
            "data": base64.b64encode(PNG).decode(),
            "mimeType": "image/png",
        }
    ]

    # Images inside data are sent after it, replaced by placeholders
    content, _ = results.call(tools["get_data"], kind="dict")
    assert json.loads(content[0]["text"]) == {
        "values": [1, 2],
        "plot": "<image 1>",
        "label": "x",
    }
    assert content[1]["type"] == "image"


def test_call_errors(tools):
    results = Results()

    content, is_error = results.call(tools["fail"])
    assert is_error
    assert content[0]["text"] == "Can't do that, try something else."

    content, is_error = results.call(tools["crash"])
    assert is_error
    assert "Internal error in tool crash" in content[0]["text"]

    content, is_error = results.call(tools["greet"])
    assert is_error
    assert content[0]["text"] == "Missing arguments: name"

    content, is_error = results.call(tools["greet"], name="x", age=3)
    assert is_error
    assert content[0]["text"] == "Unknown arguments: age"


def test_call_future(tools):
    """Methods can return a future to finish the call later."""
    results = Results()
    plugin = tools["_plugin"]

    assert results.call(tools["later"]) is None
    plugin.futures[0].set_result(["a", "b"])
    content, is_error = results.calls[0]
    assert not is_error
    assert json.loads(content[0]["text"]) == ["a", "b"]

    results.call(tools["later"])
    plugin.futures[1].set_exception(ExposedCallError("Too late."))
    content, is_error = results.calls[1]
    assert is_error
    assert content[0]["text"] == "Too late."


def test_unsupported_methods_are_skipped(caplog):
    class Plugin:

        @expose
        def no_docstring(self, value: int) -> None:
            pass

        @expose
        def no_hint(self, value) -> None:
            """Missing type hint."""

        @expose
        def bad_type(self, value: object) -> None:
            """Unsupported type."""

        @expose
        def kwargs(self, **values: int) -> None:
            """Unsupported **kwargs."""

        @expose
        def ok(self, value: Optional[list[float]] = None) -> None:
            """Supported."""

    tools = tools_from_plugin(Plugin())
    assert [tool.name for tool in tools] == ["ok"]
    assert tools[0].input_schema["properties"]["value"] == {
        "type": "array",
        "items": {"type": "number"},
    }
    for name in ["no_docstring", "no_hint", "bad_type", "kwargs"]:
        assert f"Can't expose {name}" in caplog.text


def test_annotation_to_schema():
    assert annotation_to_schema(str | None) == {"type": "string"}
    assert annotation_to_schema(dict[str, int]) == {"type": "object"}
    assert annotation_to_schema(int | str) == {
        "anyOf": [{"type": "integer"}, {"type": "string"}]
    }
    assert annotation_to_schema(Literal[1, "a"]) == {"enum": [1, "a"]}
    with pytest.raises(TypeError):
        annotation_to_schema(tuple[int, int])


def test_parse_docstring_markup():
    description, parameters = parse_docstring(
        """
        Use :meth:`list_consoles` and ``code``.

        - First item
        - Second item

        Parameters
        ----------
        **kwargs
            Extra options.
        """
    )
    assert description == (
        "Use `list_consoles` and `code`.\n\n- First item\n- Second item"
    )
    assert parameters == {"kwargs": "Extra options."}


def test_svg_images_are_converted(qtbot):
    svg = (
        b'<svg xmlns="http://www.w3.org/2000/svg" width="4" height="4">'
        b'<rect width="4" height="4"/></svg>'
    )
    content = result_to_content(Image(svg, "image/svg+xml"))
    assert content[0]["mimeType"] == "image/png"
    assert base64.b64decode(content[0]["data"]).startswith(b"\x89PNG")
