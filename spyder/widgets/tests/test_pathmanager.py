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
import os
# Standard library imports
try:
    from unittest.mock import patch
except ImportError:
    from mock import patch  # Python 2

# Test library imports
import pytest
from qtpy import PYQT4
from qtpy.QtCore import Qt
from qtpy.QtWidgets import QMessageBox

# Local imports
from spyder.py3compat import PY3
from spyder.widgets.pathmanager import PathManager


@pytest.fixture
def setup_pathmanager(qtbot, parent=None, pathlist=None, ro_pathlist=None,
                      sync=True):
    """Set up PathManager."""
    widget = PathManager(None, pathlist=pathlist, ro_pathlist=ro_pathlist)
    qtbot.addWidget(widget)
    return widget


@pytest.mark.skipif(PY3 and PYQT4, reason="It segfaults frequently")
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


@patch.object(QMessageBox, 'question', return_value=QMessageBox.Yes)
def test_synchronize_with_PYTHONPATH(qtbot):
    if os.name != 'nt':
        return

    pathmanager = setup_pathmanager(qtbot, None,
                                    pathlist=['path1', 'path2', 'path3'],
                                    ro_pathlist=['path4', 'path5', 'path6'])

    from spyder.utils.environ import (get_user_env, set_user_env,
                                      listdict2envdict)

    # Store PYTHONPATH original state
    env = get_user_env()
    original_pathlist = env['PYTHONPATH']

    # Assert that PYTHONPATH is synchronized correctly with Spyder's path list
    pathmanager.synchronize()
    expected_pathlist = ['path1', 'path2', 'path3', 'path4', 'path5', 'path6']
    env = get_user_env()
    assert env['PYTHONPATH'] == expected_pathlist

    # Uncheck 'path2' and assert that it is removed from PYTHONPATH when it
    # is synchronized with Spyder's path list
    pathmanager.listwidget.item(1).setCheckState(Qt.Unchecked)
    pathmanager.synchronize()
    expected_pathlist = ['path1', 'path3', 'path4', 'path5', 'path6']
    env = get_user_env()
    assert env['PYTHONPATH'] == expected_pathlist

    # Restore PYTHONPATH to its original state
    env['PYTHONPATH'] = original_pathlist
    set_user_env(listdict2envdict(env))


if __name__ == "__main__":
    import os
    pytest.main([os.path.basename(__file__)])
