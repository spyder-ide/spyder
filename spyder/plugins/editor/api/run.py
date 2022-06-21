# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""Spyder Editor-specific run schemas."""

# Standard library imports
from __future__ import annotations

import sys
from enum import IntEnum
from datetime import datetime
from typing import Tuple, List

# PEP 589 and 544 are available from Python 3.8 onwards
if sys.version_info >= (3, 8):
    from typing import TypedDict
else:
    from typing_extensions import TypedDict

# Support PEP 655 (available from Python 3.11 onwards)
from typing_extensions import NotRequired

# Local imports
from spyder.plugins.run.api import Context


class EditorRunConfiguration(TypedDict):
    """Editor supported run configuration schema."""

    # Name of the plugin that is extending the editor supported run
    # configurations
    origin: str

    # Filename extension for which the editor should be able to provide
    # run configurations.
    extension: str

    # List of contexts for which the editor should produce run configurations.
    contexts: List[Context]


class FileRun(TypedDict):
    """Schema emitted by the editor for the `File` run context."""

    # File path to the file to execute. It is responsibility of the
    # executor to load and correctly interpret the file.
    path: str


class SelectionRun(TypedDict):
    """Schema emitted by the editor for the `Selection` run context."""

    # File path to the file that contains the selection to execute.
    path: str

    # Actual selection text to execute.
    selection: str

    # Encoding of the text.
    encoding: str

    # Selection start and end in (line, column) format
    line_col_bounds: Tuple[Tuple[int, int], Tuple[int, int]]

    # Selection start and end in characters
    character_bounds: Tuple[int, int]


class CellRun(TypedDict):
    """Schema emitted by the editor for the `Cell` run context."""

    # File path to the file that contains the selection to execute.
    path: str

    # Actual cell text to execute.
    cell: str

    # Name of the cell.
    cell_name: str

    # Encoding of the text.
    encoding: str

    # Selection start and end in (line, column) format
    line_col_bounds: Tuple[Tuple[int, int], Tuple[int, int]]

    # Selection start and end in characters
    character_bounds: Tuple[int, int]

    # True if the text should be copied over.
    copy: bool
