# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""External console API."""

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


class ExtConsolePyConfiguration(TypedDict):
    """External console execution parameters for Python files."""

    # True if the external console is using custom arguments. False otherwise
    args_enabled: bool
    # Custom arguments to pass to the external console.
    args: str
    # True if the console should remain open once the execution finishes.
    # False otherwise.
    interact: bool
    # True if the console is using custom Python arguments. False otherwise.
    python_args_enabled: bool
    # Custom arguments to pass to the console.
    python_args: str
