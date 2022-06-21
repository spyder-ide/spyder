# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""Spyder IPythonConsole API."""

# Standard library imports
from __future__ import annotations

import sys
from typing import Any, Set, List, Union, Optional, Type, Dict

# PEP 589 and 544 are available from Python 3.8 onwards
if sys.version_info >= (3, 8):
    from typing import TypedDict
else:
    from typing_extensions import TypedDict

# Support PEP 655 (available from Python 3.11 onwards)
from typing_extensions import NotRequired

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
    # If True, then the console will re use the current namespace. If False,
    # then it will create a new one.
    console_namespace: bool
