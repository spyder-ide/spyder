# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)
"""
Profiler Plugin.
"""
# Standard library imports
import sys

# PEP 589 and 544 are available from Python 3.8 onwards
if sys.version_info >= (3, 8):
    from typing import TypedDict
else:
    from typing_extensions import TypedDict


class ProfilerPyConfiguration(TypedDict):
    """Profiler execution parameters for Python files."""

    # True if the script is using custom arguments. False otherwise
    args_enabled: bool
    # Custom arguments to pass to the script when profiling.
    args: str
