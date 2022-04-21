# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright (c) 2009- Spyder Project Contributors
#
# Distributed under the terms of the MIT License
# (see spyder/__init__.py for details)
# -----------------------------------------------------------------------------


"""
spyder.plugins.editor.api
=========================

API to interact with some features of Editor and CodeEditor.
"""

# Standard library imports
from __future__ import annotations
import sys
from typing import List

# PEP 589 and 544 are available from Python 3.8 onwards
if sys.version_info >= (3, 8):
    from typing import TypedDict
else:
    from typing_extensions import TypedDict

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
