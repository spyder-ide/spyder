# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""External terminal API."""

# Standard library imports
from __future__ import annotations
from typing import TypedDict


class ExtTerminalPyConfiguration(TypedDict):
    """External terminal execution parameters for Python files."""

    # True if the external terminal is using custom arguments. False otherwise
    args_enabled: bool

    # Custom arguments to pass to the external terminal.
    args: str

    # True if the terminal should remain open once the execution finishes.
    # False otherwise.
    interact: bool

    # True if the terminal is using custom Python arguments. False otherwise.
    python_args_enabled: bool

    # Custom arguments to pass to the terminal.
    python_args: str


class ExtTerminalShConfiguration(TypedDict):
    """External terminal execution parameters for shell files."""

    # Path/name of the shell interpreter to use.
    interpreter: str

    # True if the shell interpreter is using custom arguments, False otherwise.
    interpreter_opts_enabled: bool

    # Custom arguments to pass to the shell interpreter.
    interpreter_opts: str

    # True if the shell script is using custom arguments, False otherwise.
    script_opts_enabled: bool

    # Custom arguments to pass to the shell script.
    script_opts: str

    # True if the terminal will be closed after execution, False otherwise.
    close_after_exec: bool
