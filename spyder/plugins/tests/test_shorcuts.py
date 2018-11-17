# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
#

"""
Tests for shortcuts.py
"""

import os

# Test library imports
import pytest

# Local imports
from spyder.plugins.shortcuts import ShortcutsTable

@pytest.fixture
def shortcuts(qtbot):
    """Set up shortcuts."""
    widget = ShortcutsTable()
    qtbot.addWidget(widget)
    return widget


@pytest.mark.skipif(not os.name == 'nt', reason="It segfaults too much on Linux")
def test_shortcuts(shortcuts):
    """Run shortcuts table."""
    shortcuts.show()
    shortcuts.check_shortcuts()
    assert shortcuts


if __name__ == "__main__":
    pytest.main()
