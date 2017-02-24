# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
#

"""
Tests for pathmanager.py
"""
# Standard library imports
import sys

# Test library imports
import pytest

# Local imports
from spyder.widgets.pathmanager import PathManager

@pytest.fixture
def setup_pathmanager(qtbot, parent=None, pathlist=None, ro_pathlist=None,
                      sync=True):
    """Set up PathManager."""
    widget = PathManager(None, pathlist=pathlist, ro_pathlist=ro_pathlist)
    qtbot.addWidget(widget)
    return widget

def test_pathmanager(qtbot):
    """Run PathManager test"""
    pathmanager = setup_pathmanager(qtbot, None, pathlist=sys.path[:-10],
                                    ro_pathlist=sys.path[-10:])
    pathmanager.show()
    assert pathmanager


if __name__ == "__main__":
    pytest.main()
