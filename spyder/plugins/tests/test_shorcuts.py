# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
#

"""
Tests for shortcuts.py
"""

# Test library imports
import pytest

# Local imports
from spyder.plugins.shortcuts import ShortcutsTable

@pytest.fixture
def setup_shorcuts(qtbot):
    """Set up shortcuts."""
    widget = ShortcutsTable()
    qtbot.addWidget(widget)
    return widget

def test_shortcuts(qtbot):
    """Run shortcuts table."""
    shortcuts = setup_shorcuts(qtbot)
    shortcuts.show()
    shortcuts.check_shortcuts()
    assert shortcuts


if __name__ == "__main__":
    pytest.main()
