# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""Description of a language server and its (de)serialization."""

from __future__ import annotations

# Standard library imports
from dataclasses import asdict, dataclass, field, replace
from typing import Any

AUTO_LANGUAGES = "auto"
"""``languages`` value for auto-detection, see :class:`LanguageServerClientProvider`."""

RESTART_FIELDS = ("cmd", "args", "host", "port", "external", "stdio")
"""Fields whose change requires restarting the server."""


@dataclass(frozen=True)
class ServerConfig:
    """Everything needed to run or reach one language server."""

    name: str
    """Unique server name (configuration key)."""

    cmd: str = ""
    """Executable (or Python module when ``python_module`` is set)."""

    args: str = ""
    """Arguments. ``{host}`` and ``{port}`` are substituted."""

    host: str = "127.0.0.1"
    port: int = 2084
    stdio: bool = False
    """Talk to the server through its stdin/stdout instead of TCP."""

    external: bool = False
    """The server is already running. Connect to it instead of starting it."""

    languages: tuple[str, ...] | str = AUTO_LANGUAGES
    """LSP ``languageId``\\s served, or :data:`AUTO_LANGUAGES`."""

    configurations: dict[str, Any] = field(default_factory=dict)
    """Settings sent with ``workspace/didChangeConfiguration``."""

    initialization_options: dict[str, Any] | None = None

    python_module: bool = False
    """Run ``cmd`` as ``python -m cmd`` with the configured interpreter."""

    def __post_init__(self):
        if not self.name:
            raise ValueError("A server needs a name")
        if self.stdio and self.external:
            raise ValueError(
                f"Server {self.name!r} cannot use stdio and be external"
            )
        if self.languages != AUTO_LANGUAGES:
            object.__setattr__(self, "languages", tuple(self.languages))

    @property
    def auto_languages(self) -> bool:
        return self.languages == AUTO_LANGUAGES

    def needs_restart(self, other: ServerConfig) -> bool:
        """Whether switching from ``self`` to ``other`` restarts the server."""
        return any(
            getattr(self, name) != getattr(other, name)
            for name in RESTART_FIELDS
        )

    def to_conf(self) -> dict[str, Any]:
        """Configuration representation (JSON compatible)."""
        data = asdict(self)
        data.pop("name")
        if isinstance(data["languages"], tuple):
            data["languages"] = list(data["languages"])
        return data

    @classmethod
    def from_conf(cls, name: str, data: dict[str, Any]) -> ServerConfig:
        """Build from the configuration representation."""
        known = {f for f in cls.__dataclass_fields__ if f != "name"}
        unknown = set(data) - known
        if unknown:
            raise ValueError(
                f"Server {name!r} has unknown options: {sorted(unknown)}"
            )
        return cls(name=name, **data)

    def with_changes(self, **changes) -> ServerConfig:
        return replace(self, **changes)
