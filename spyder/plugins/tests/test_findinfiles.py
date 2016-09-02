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

# Local imports
from spyder.config.main import EXCLUDE_PATTERNS


class TestFindInFilesPlugin:

    def check_regex(self, patterns):
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

    def test_include_patterns_are_valid_regex(self, qtbot):
        # qtawesome requires a QApplication to exist, so widgets import must
        # happen inside the test (or with fixtures)
        from spyder.plugins.findinfiles import FindInFiles
        patterns = FindInFiles.include_patterns()
        checks = self.check_regex(patterns)
        assert all(checks)

    def test_exclude_patterns_are_valid_regex(self):
        checks = self.check_regex(EXCLUDE_PATTERNS)
        assert all(checks)
