# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""
Turn the methods plugins mark with ``@expose`` into MCP tools.

The tool's description comes from the method's docstring and its input
schema from the method's type hints, with the parameter descriptions taken
from the ``Parameters`` section of the docstring.
"""

# Standard library imports
from __future__ import annotations

from collections.abc import Callable
from concurrent.futures import Future
from dataclasses import dataclass
import inspect
import json
import logging
import re
import types
import typing
from typing import Any, Literal, Union

# Local imports
from spyder.api.plugins.exposed import (
    ExposedCallError,
    ExposedSpec,
    Image,
    get_exposed_methods,
)
from spyder.plugins.mcpserver.api import (
    Content,
    MCPTool,
    ToolCall,
    ToolError,
    image_content,
    svg_to_png,
    text_content,
    truncate,
)

logger = logging.getLogger(__name__)

SIMPLE_TYPES = {
    str: "string",
    bool: "boolean",
    int: "integer",
    float: "number",
    dict: "object",
    list: "array",
}


@dataclass
class ExposedToolInfo:
    """Description of an exposed method as an MCP tool."""

    name: str
    description: str
    input_schema: dict
    required: set[str]
    parameters: set[str]
    read_only: bool
    destructive: bool

    def to_dict(self) -> dict[str, Any]:
        """Tool definition, without the parts that depend on the instance."""
        return {
            "name": self.name,
            "description": self.description,
            "inputSchema": self.input_schema,
            "readOnly": self.read_only,
            "destructive": self.destructive,
        }


# ---- Collection
# -----------------------------------------------------------------------------
def tools_from_plugin(plugin: Any, plugin_name: str | None = None):
    """
    Create MCP tools for the exposed methods of ``plugin``.

    Methods that can't be turned into tools (e.g. because of unsupported
    argument types) are skipped with an error in the log.

    Returns
    -------
    list[MCPTool]
    """
    tools = []
    for attr_name, (func, spec) in get_exposed_methods(type(plugin)).items():
        try:
            info = describe_exposed(func, spec)
        except TypeError as error:
            logger.error("Can't expose %s to agents: %s", attr_name, error)
            continue
        tools.append(
            make_tool(getattr(plugin, attr_name), info, plugin_name)
        )
    return tools


def describe_exposed(func: Callable, spec: ExposedSpec) -> ExposedToolInfo:
    """
    Describe an exposed function (unbound method) as an MCP tool.

    Raises
    ------
    TypeError
        If the function can't be turned into a tool, e.g. because it has no
        docstring or its arguments have unsupported types.
    """
    qualname = func.__qualname__
    summary, param_docs = parse_docstring(func.__doc__)
    description = spec.description or summary
    if not description:
        raise TypeError(f"{qualname} needs a docstring")

    params = list(inspect.signature(func).parameters.values())
    if params and params[0].name in ("self", "cls"):
        params = params[1:]

    for param in params:
        if param.kind in (param.VAR_POSITIONAL, param.VAR_KEYWORD):
            raise TypeError(f"{qualname} can't take *args or **kwargs")
        if param.kind is param.POSITIONAL_ONLY:
            raise TypeError(f"{qualname} can't take positional-only arguments")

    annotations = _get_annotations(func, [param.name for param in params])

    properties = {}
    required = set()
    for param in params:
        if param.name not in annotations:
            raise TypeError(
                f"Parameter {param.name!r} of {qualname} needs a type hint"
            )
        try:
            schema = annotation_to_schema(annotations[param.name])
        except TypeError as error:
            raise TypeError(
                f"Parameter {param.name!r} of {qualname}: {error}"
            ) from None

        if param.name in param_docs:
            schema["description"] = param_docs[param.name]

        if param.default is param.empty:
            required.add(param.name)
        elif param.default is not None:
            try:
                json.dumps(param.default)
            except TypeError:
                pass
            else:
                schema["default"] = param.default

        properties[param.name] = schema

    input_schema = {"type": "object", "properties": properties}
    if required:
        input_schema["required"] = sorted(required)

    return ExposedToolInfo(
        name=spec.name or func.__name__,
        description=description,
        input_schema=input_schema,
        required=required,
        parameters=set(properties),
        read_only=spec.read_only,
        destructive=spec.destructive,
    )


def make_tool(
    method: Callable, info: ExposedToolInfo, plugin_name: str | None = None
) -> MCPTool:
    """Create an MCP tool that calls a bound exposed ``method``."""

    def handler(call: ToolCall):
        arguments = dict(call.arguments)
        unknown = sorted(set(arguments) - info.parameters)
        if unknown:
            raise ToolError(f"Unknown arguments: {', '.join(unknown)}")
        missing = sorted(info.required - set(arguments))
        if missing:
            raise ToolError(f"Missing arguments: {', '.join(missing)}")

        result = method(**arguments)
        if isinstance(result, Future):
            result.add_done_callback(
                lambda future: _finish_from_future(call, info.name, future)
            )
            return None
        return result_to_content(result)

    return MCPTool(
        name=info.name,
        description=info.description,
        handler=handler,
        input_schema=info.input_schema,
        read_only=info.read_only,
        destructive=info.destructive,
        plugin=plugin_name,
    )


def _finish_from_future(call: ToolCall, name: str, future: Future) -> None:
    try:
        value = future.result()
    except ExposedCallError as error:
        call.error(str(error))
    except Exception as error:
        logger.error("Error running MCP tool %s", name, exc_info=error)
        call.error(f"Internal error in tool {name}: {error!r}")
    else:
        call.reply(result_to_content(value))


# ---- Results
# -----------------------------------------------------------------------------
def result_to_content(value: Any) -> list[Content]:
    """
    Convert the value returned by an exposed method to MCP content.

    Strings are sent as text and other data as JSON. Images, also when
    they're inside lists or dicts, are sent as image content after the text,
    and replaced by ``"<image N>"`` in the JSON.
    """
    if value is None:
        return [text_content("Done.")]
    if isinstance(value, str):
        return [text_content(truncate(value))]

    images: list[Image] = []

    def replace_images(item):
        if isinstance(item, Image):
            images.append(item)
            return f"<image {len(images)}>"
        if isinstance(item, dict):
            return {key: replace_images(val) for key, val in item.items()}
        if isinstance(item, (list, tuple)):
            return [replace_images(val) for val in item]
        return item

    data = replace_images(value)
    content = []
    if not isinstance(value, Image):
        text = json.dumps(data, indent=2, default=str, ensure_ascii=False)
        content.append(text_content(truncate(text)))
    content.extend(_image_to_content(image) for image in images)
    return content


def _image_to_content(image: Image) -> Content:
    # Agents can't read SVG images
    if image.mime_type == "image/svg+xml":
        return image_content(svg_to_png(image.data))
    return image_content(image.data, image.mime_type)


# ---- Schemas
# -----------------------------------------------------------------------------
def annotation_to_schema(annotation: Any) -> dict:
    """
    Convert a type hint to a JSON schema.

    Supported types are ``str``, ``int``, ``float``, ``bool``, ``dict``,
    ``list[...]``, ``Literal[...]`` and unions of them, including optional
    ones (e.g. ``str | None``).

    Raises
    ------
    TypeError
        If the type isn't supported.
    """
    if annotation in SIMPLE_TYPES:
        return {"type": SIMPLE_TYPES[annotation]}

    origin = typing.get_origin(annotation)
    args = typing.get_args(annotation)

    if origin is list:
        schema = {"type": "array"}
        if args:
            schema["items"] = annotation_to_schema(args[0])
        return schema

    if origin is dict:
        return {"type": "object"}

    if origin is Literal:
        schema = {"enum": list(args)}
        value_types = {type(arg) for arg in args}
        if len(value_types) == 1 and type(args[0]) in SIMPLE_TYPES:
            schema["type"] = SIMPLE_TYPES[type(args[0])]
        return schema

    if origin in (Union, types.UnionType):
        # Optional values are expressed by not requiring the parameter
        options = [arg for arg in args if arg is not type(None)]
        if len(options) == 1:
            return annotation_to_schema(options[0])
        return {"anyOf": [annotation_to_schema(arg) for arg in options]}

    raise TypeError(f"type {annotation!r} is not supported in JSON schemas")


def _get_annotations(func: Callable, names: list[str]) -> dict[str, Any]:
    """
    Get the type hints of the parameters ``names`` of ``func``.

    Only those are evaluated, so the return annotation can refer to names
    that are only imported for type checking.
    """
    try:
        import annotationlib  # Python 3.14+
    except ImportError:
        annotations = inspect.get_annotations(func)
    else:
        annotations = annotationlib.get_annotations(
            func, format=annotationlib.Format.FORWARDREF
        )

    resolved = {}
    for name in names:
        if name not in annotations:
            continue
        annotation = annotations[name]
        source = getattr(annotation, "__forward_arg__", annotation)
        if isinstance(source, str):
            try:
                annotation = eval(source, func.__globals__)
            except Exception as error:
                raise TypeError(
                    f"Can't resolve the type hint of {name!r} of "
                    f"{func.__qualname__}: {error}"
                ) from None
        resolved[name] = annotation
    return resolved


def parse_docstring(docstring: str | None) -> tuple[str, dict[str, str]]:
    """
    Parse a numpydoc docstring.

    Returns
    -------
    description : str
        Text before the first section.
    parameters : dict
        Description of each parameter in the ``Parameters`` section.
    """
    if not docstring:
        return "", {}

    lines = inspect.cleandoc(docstring).splitlines()

    # Split the docstring in sections, which are a title underlined by dashes
    sections = {"": []}
    current = ""
    index = 0
    while index < len(lines):
        line = lines[index]
        following = lines[index + 1] if index + 1 < len(lines) else ""
        if line.strip() and re.fullmatch(r"\s*-{3,}\s*", following):
            current = line.strip().lower()
            sections[current] = []
            index += 2
            continue
        sections[current].append(line)
        index += 1

    description = _clean_text("\n".join(sections[""]))

    parameters = {}
    name = None
    for line in sections.get("parameters", []):
        if not line.strip():
            continue
        if not line.startswith((" ", "\t")):
            match = re.match(r"\*{0,2}(\w+)", line)
            name = match.group(1) if match else None
            if name is not None:
                parameters[name] = ""
        elif name is not None:
            text = line.strip()
            parameters[name] = f"{parameters[name]} {text}".strip()

    parameters = {
        name: _clean_text(text) for name, text in parameters.items()
    }
    return description, parameters


def _clean_text(text: str) -> str:
    """
    Make docstring text easier to read for agents: unwrap the lines of each
    paragraph (except list items) and simplify reST markup.
    """
    paragraphs = []
    for paragraph in re.split(r"\n\s*\n", text.strip()):
        lines = []
        for line in paragraph.splitlines():
            line = line.strip()
            if lines and not re.match(r"([-*]|\d+\.)\s", line):
                lines[-1] = f"{lines[-1]} {line}"
            else:
                lines.append(line)
        paragraphs.append("\n".join(lines))

    text = "\n\n".join(paragraphs)
    text = re.sub(r":\w+:`~?([^`]+)`", r"`\1`", text)
    return text.replace("``", "`")
