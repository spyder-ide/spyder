# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""Build the ruff server configuration from Spyder's preferences."""

from __future__ import annotations

# Third party imports
from ruff import find_ruff_bin

# Local imports
from spyder.plugins.languageservices.providers.lsp.config import ServerConfig

RUFF_SERVER_NAME = "ruff"


def _csv(value: str) -> list[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


def generate_ruff_config(get_conf) -> ServerConfig:
    """ruff :class:`ServerConfig` for the current preferences.

    ``get_conf(option, default, section=None)`` reads the ruff provider
    options (``section=None``) and the ``editor`` section. The settings go
    in the initialization options, so a change restarts the server.
    """
    extend_select = _csv(get_conf("extend_select", ""))
    settings = {
        "lineLength": get_conf("line_length", 79, section="editor"),
        "lint": {
            "enable": bool(get_conf("lint", True)),
            "extendSelect": extend_select,
            "ignore": _csv(get_conf("ignore", "")),
        },
    }
    if get_conf("pydocstyle", False):
        if "D" not in extend_select:
            extend_select.append("D")
        # Inline configuration takes precedence over project files, so it
        # only carries what has no dedicated setting.
        settings["configuration"] = {
            "lint": {
                "pydocstyle": {
                    "convention": get_conf("pydocstyle/convention", "numpy")
                }
            }
        }
    return ServerConfig(
        name=RUFF_SERVER_NAME,
        cmd=find_ruff_bin(),
        args="server",
        stdio=True,
        languages=("python",),
        initialization_options={"settings": settings},
    )
