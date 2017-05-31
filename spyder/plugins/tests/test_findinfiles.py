# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright © Spyder Project Contributors
#
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)
# -----------------------------------------------------------------------------
"""Test scripts for `findinfiles` plugin."""

# Standard library imports
import re

# 3rd party imports
import pytest

# Local imports
from spyder.config.main import EXCLUDE_PATTERNS


def check_regex(patterns):
    """
    Check that regular expression patterns provided by compiling them.
    Return a list of booleans for each of the provided patterns.
    """
    checks = []
    for pattern in patterns:
        try:
            re.compile(pattern)
            is_valid = True
        except re.error:
            is_valid = False
        checks.append(is_valid)
    return checks


def test_exclude_patterns_are_valid_regex():
    checks = check_regex(EXCLUDE_PATTERNS)
    assert all(checks)


if __name__ == "__main__":
    pytest.main()
