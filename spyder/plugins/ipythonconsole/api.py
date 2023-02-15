# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""Spyder IPythonConsole API."""

# Standard library imports
from __future__ import annotations
from typing import TypedDict

# Third-party imports
from typing_extensions import NotRequired  # Available from Python 3.11


class IPythonConsolePyConfiguration(TypedDict):
    """IPythonConsole python execution parameters."""

    # True if the execution is using the current console. False otherwise
    current: bool

    # If True, then the console will start a debugging session if an error
    # occurs. False otherwise.
    post_mortem: bool

    # True if the console is using custom Python arguments. False otherwise.
    python_args_enabled: bool

    # Custom arguments to pass to the console.
    python_args: str

    # If True, then the console will clear all variables before execution.
    # False otherwise.
    clear_namespace: bool

    # If True, then the console will reuse the current namespace. If False,
    # then it will use an empty one.
    console_namespace: bool

    # If True, then the console will enter in debug mode.
    debug: NotRequired[bool]
