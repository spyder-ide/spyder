# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
#

"""
Tests for explorer.py
"""

# Test library imports
import pytest

# Local imports
from spyder.plugins.explorer.widgets import (FileExplorerTest,
                                             ProjectExplorerTest)

@pytest.fixture
def setup_file_explorer(qtbot):
    """Set up FileExplorerTest."""
    widget = FileExplorerTest()
    qtbot.addWidget(widget)
    return widget

@pytest.fixture
def setup_project_explorer(qtbot):
    """Set up FileExplorerTest."""
    widget = ProjectExplorerTest()
    qtbot.addWidget(widget)
    return widget

def test_file_explorer(qtbot):
    """Run FileExplorerTest."""
    fe = setup_file_explorer(qtbot)
    fe.resize(640, 480)
    fe.show()
    assert fe

def test_project_explorer(qtbot):
    """Run ProjectExplorerTest."""
    pe = setup_project_explorer(qtbot)
    pe.resize(640, 480)
    pe.show()
    assert pe


if __name__ == "__main__":
    pytest.main()
