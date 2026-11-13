# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""Build the pyrefly server configuration from Spyder's preferences."""

from __future__ import annotations

# Local imports
from spyder.plugins.languageservices.providers.lsp.config import ServerConfig
from spyder.utils.programs import get_binary_path

PYREFLY_SERVER_NAME = "pyrefly"


def generate_pyrefly_config(get_conf, interpreter: str) -> ServerConfig:
    """pyrefly :class:`ServerConfig` for the current preferences.

    ``get_conf(option, default, section=None)`` reads the pyrefly provider
    options (``section=None``) and the ``pythonpath_manager`` section.
    ``interpreter`` is the Python whose packages pyrefly analyzes code
    against. The settings are the ``python`` section pyrefly requests
    through ``workspace/configuration``, so a change does not restart the
    server.
    """
    settings = {
        "python": {
            "pythonPath": interpreter,
            "pyrefly": {
                "extraSearchPaths": list(
                    get_conf("spyder_pythonpath", [], section="pythonpath_manager")
                ),
                "typeCheckingMode": get_conf("type_checking_mode", "auto"),
            },
        }
    }
    return ServerConfig(
        name=PYREFLY_SERVER_NAME,
        cmd=get_binary_path("pyrefly"),
        args="lsp",
        stdio=True,
        languages=("python",),
        configurations=settings,
    )
