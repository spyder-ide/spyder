# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
#
"""Tests for outline explorer widget."""

# Test library imports
import pytest

# Local imports
from spyder.plugins.outlineexplorer.widgets import OutlineExplorerWidget


@pytest.fixture
def setup_outline_explorer(qtbot):
    """Set up outline_explorer."""
    widget = OutlineExplorerWidget(None)
    qtbot.addWidget(widget)
    return widget


def test_outline_explorer(qtbot):
    """Run outline_explorer."""
    outline_explorer = setup_outline_explorer
    assert outline_explorer


if __name__ == "__main__":
    pytest.main()
