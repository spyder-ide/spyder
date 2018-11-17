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

# Test library imports
import pytest
from qtpy.QtCore import Qt

# Local imports
from spyder.py3compat import PY3
from spyder.widgets import pathmanager as pathmanager_mod
from spyder.utils.programs import is_module_installed


@pytest.fixture
def pathmanager(qtbot, request):
    """Set up PathManager."""
    pathlist, ro_pathlist = request.param
    widget = pathmanager_mod.PathManager(None, pathlist=pathlist,
                                         ro_pathlist=ro_pathlist)
    qtbot.addWidget(widget)
    return widget


@pytest.mark.parametrize('pathmanager',
                         [(sys.path[:-10], sys.path[-10:])],
                         indirect=True)
def test_pathmanager(pathmanager, qtbot):
    """Run PathManager test"""
    pathmanager.show()
    assert pathmanager


@pytest.mark.parametrize('pathmanager',
                         [(sys.path[:-10], sys.path[-10:])],
                         indirect=True)
def test_check_uncheck_path(pathmanager):
    """
    Test that checking and unchecking a path in the PathManager correctly
    update the not active path list.
    """
    # Assert that all paths are checked.
    for row in range(pathmanager.listwidget.count()):
        assert pathmanager.listwidget.item(row).checkState() == Qt.Checked

    # Uncheck a path and assert that it is added to the not active path list.
    pathmanager.listwidget.item(3).setCheckState(Qt.Unchecked)
    assert pathmanager.not_active_pathlist != []

    # Check an uncheked path and assert that it is removed from the not active
    # path list.
    pathmanager.listwidget.item(3).setCheckState(Qt.Checked)
    assert pathmanager.not_active_pathlist == []


@pytest.mark.skipif(os.name != 'nt' or not is_module_installed('win32con'),
                    reason=("This feature is not applicable for Unix "
                            "systems and pywin32 is needed"))
@pytest.mark.parametrize('pathmanager',
                         [(['path1', 'path2', 'path3'], ['path4', 'path5', 'path6'])],
                         indirect=True)
def test_synchronize_with_PYTHONPATH(pathmanager, mocker):
    # Import here to prevent an ImportError when testing on unix systems
    from spyder.utils.environ import (get_user_env, set_user_env,
                                      listdict2envdict)

    # Store PYTHONPATH original state
    env = get_user_env()
    original_pathlist = env.get('PYTHONPATH', [])

    # Mock the dialog window and answer "Yes" to clear contents of PYTHONPATH
    # before adding Spyder's path list
    mocker.patch.object(pathmanager_mod.QMessageBox, 'question',
                        return_value=pathmanager_mod.QMessageBox.Yes)

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

    # Mock the dialog window and answer "No" to clear contents of PYTHONPATH
    # before adding Spyder's path list
    mocker.patch.object(pathmanager_mod.QMessageBox, 'question',
                        return_value=pathmanager_mod.QMessageBox.No)

    # Uncheck 'path3' and assert that it is kept in PYTHONPATH when it
    # is synchronized with Spyder's path list
    pathmanager.listwidget.item(2).setCheckState(Qt.Unchecked)
    pathmanager.synchronize()
    expected_pathlist = ['path3', 'path1', 'path4', 'path5', 'path6']
    env = get_user_env()
    assert env['PYTHONPATH'] == expected_pathlist

    # Restore PYTHONPATH to its original state
    env['PYTHONPATH'] = original_pathlist
    set_user_env(listdict2envdict(env))


if __name__ == "__main__":
    pytest.main([os.path.basename(__file__)])
