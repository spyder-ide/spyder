# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright (c) 2025- Spyder Kernels Contributors
#
# Licensed under the terms of the MIT License
# (see spyder_kernels/__init__.py for details)
# -----------------------------------------------------------------------------

"""
Tests for commbase.py
"""

# Local imports
from spyder_kernels.comms.commbase import (
    stacksummary_from_json,
    stacksummary_to_json,
)


def test_stacksummary_roundtrip():
    """
    Test that roundtripping a JSON representation of a StackSummary works.
    """
    json = [
        {"filename": "f1", "lineno": 42, "name": "n1", "line": "l1"},
        {"filename": "f2", "lineno": 42, "name": "n2", "line": "l2"},
    ]
    stacksummary = stacksummary_from_json(json)
    assert stacksummary_to_json(stacksummary) == json
