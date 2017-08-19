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
from qtpy.QtCore import Qt

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


def test_check_uncheck_path(qtbot):
    """
    Test that checking and unchecking a path in the PathManager correctly
    update the not active path list.
    """
    pathmanager = setup_pathmanager(qtbot, None, pathlist=sys.path[:-10],
                                    ro_pathlist=sys.path[-10:])

    # Assert that all paths are checked.
    for row in range(pathmanager.listwidget.count()):
        assert pathmanager.listwidget.item(row).checkState() == Qt.Checked

    # Uncheck a path and assert that it is added to the not active path list.
    pathmanager.listwidget.item(3).setCheckState(Qt.Unchecked)
    assert pathmanager.not_active_pathlist == [sys.path[3]]

    # Check an uncheked path and assert that it is removed from the not active
    # path list.
    pathmanager.listwidget.item(3).setCheckState(Qt.Checked)
    assert pathmanager.not_active_pathlist == []


if __name__ == "__main__":
    import os
    pytest.main([os.path.basename(__file__)])
