# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""Build the pylsp server configuration from Spyder's preferences."""

from __future__ import annotations

# Standard library imports
import copy
import os

# Local imports
from spyder.config.lsp import PYTHON_CONFIG
from spyder.plugins.languageservices.providers.lsp.config import ServerConfig
from spyder.utils.introspection.module_completion import PREFERRED_MODULES

PYLSP_SERVER_NAME = "pylsp"
LOCALHOST = ("127.0.0.1", "localhost")
PRELOAD_MODULES = ", ".join(PREFERRED_MODULES)
FORMATTERS = ("autopep8", "yapf", "black", "ruff")


def _csv(value: str) -> list[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


def generate_pylsp_config(get_conf, interpreter: str) -> ServerConfig:
    """pylsp :class:`ServerConfig` for the current preferences.

    Parameters
    ----------
    get_conf: Callable[[option, default, section], Any]
        Reads the pylsp provider options (``section=None``) and other
        sections (``editor``, ``outline_explorer``, ``pythonpath_manager``,
        ``language_services``).
    interpreter: str
        Python interpreter jedi analyzes code with.
    """
    settings = copy.deepcopy(PYTHON_CONFIG["configurations"])
    plugins = settings["pylsp"]["plugins"]

    max_line_length = get_conf("flake8/max_line_length", 79)
    indent = get_conf("indent_chars", "*    *", section="editor").replace("*", "")
    tab_size = get_conf("tab_stop_width_spaces", 4, section="editor")
    indent_size = indent.count(" ") + indent.count("\t") * tab_size

    plugins["flake8"].update(
        {
            "enabled": get_conf("flake8", False),
            "filename": _csv(get_conf("flake8/filename", "")),
            "exclude": _csv(get_conf("flake8/exclude", "")),
            "extendSelect": _csv(get_conf("flake8/extendSelect", "")),
            "extendIgnore": _csv(get_conf("flake8/extendIgnore", "")),
            "indentSize": indent_size,
            "maxLineLength": max_line_length,
        }
    )
    plugins["pycodestyle"].update({"maxLineLength": max_line_length})
    plugins["pyflakes"].update({"enabled": get_conf("pyflakes", True)})

    ruff = {
        "enabled": get_conf("ruff", False),
        "exclude": _csv(get_conf("ruff/exclude", "")),
        "extendSelect": _csv(get_conf("ruff/extendSelect", "")),
        "extendIgnore": _csv(get_conf("ruff/extendIgnore", "")),
        "lineLength": max_line_length,
    }
    if get_conf("pydocstyle", False):
        if "D" not in ruff["extendSelect"]:
            ruff["extendSelect"].append("D")
        if "D" in ruff["extendIgnore"]:
            ruff["extendIgnore"].remove("D")
    convention = get_conf("pydocstyle/convention", "numpy")
    ruff["config"] = f"lint.pydocstyle.convention = '{convention}'"
    plugins["ruff"].update(ruff)
    plugins["no_linting"].update({"enabled": get_conf("no_linting", False)})

    formatter = get_conf("formatting", "black")
    for name in FORMATTERS:
        # ruff enables formatting with a dedicated key (spyder-ide/spyder#26138)
        key = "formatEnabled" if name == "ruff" else "enabled"
        plugins[name].update({key: name == formatter})
    plugins["black"]["line_length"] = max_line_length
    plugins["ruff"]["lineLength"] = max_line_length

    plugins["pyls_spyder"].update(
        {
            "enable_block_comments": get_conf(
                "show_comments", True, section="outline_explorer"
            ),
            "group_cells": get_conf("group_cells", True, section="outline_explorer"),
        }
    )

    plugins["jedi"].update(
        {
            "environment": interpreter,
            "extra_paths": get_conf(
                "spyder_pythonpath", [], section="pythonpath_manager"
            ),
            "prioritize_extra_paths": get_conf(
                "prioritize", False, section="pythonpath_manager"
            ),
            # Independent of the environment of the pylsp process
            "env_vars": os.environ.copy(),
        }
    )
    plugins["jedi_completion"].update(
        {
            "enabled": get_conf("code_completion", True),
            "include_params": get_conf(
                "enable_code_snippets", True, section="language_services"
            ),
        }
    )
    plugins["jedi_signature_help"].update(
        {"enabled": get_conf("jedi_signature_help", True)}
    )
    plugins["jedi_definition"].update(
        {
            "enabled": get_conf("jedi_definition", True),
            "follow_imports": get_conf("jedi_definition/follow_imports", True),
        }
    )
    plugins["preload"]["modules"] = get_conf("preload_modules", PRELOAD_MODULES)

    host = get_conf("advanced/host", "127.0.0.1")
    stdio = get_conf("advanced/stdio", False)
    if host in LOCALHOST and not stdio:
        args = "--host {host} --port {port} --tcp --check-parent-process"
    else:
        args = "--check-parent-process"

    return ServerConfig(
        name=PYLSP_SERVER_NAME,
        cmd=get_conf("advanced/module", "pylsp"),
        args=args,
        host=host,
        port=get_conf("advanced/port", 2087),
        stdio=stdio,
        external=get_conf("advanced/external", False),
        languages=("python",),
        configurations=settings,
        python_module=True,
    )
