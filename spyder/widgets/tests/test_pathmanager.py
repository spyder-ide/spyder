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
from qtpy.QtCore import Qt, QTimer
from qtpy.QtWidgets import QMessageBox, QPushButton
from collections import OrderedDict

# Local imports
from spyder.utils.programs import is_module_installed
from spyder.widgets import pathmanager as pathmanager_mod

PATHS = OrderedDict([(p, True) for p in sys.path[:-10]])
ROPATHS = tuple(sys.path[-10:])
WPATHS = OrderedDict([('p1', True), ('p2', True), ('p3', True)])
WROPATHS = ('p4', 'p5', 'p6')

SPATHS = OrderedDict([('/spam', True), ('/bar', True)])
SROPATHS = ('/foo',)


@pytest.fixture
def pathmanager(qtbot, request):
    """Set up PathManager."""
    paths, read_only_paths = request.param
    widget = pathmanager_mod.PathManager(
        None,
        paths=paths,
        read_only_paths=read_only_paths)
    qtbot.addWidget(widget)
    return widget


@pytest.mark.parametrize('pathmanager', [(PATHS, ROPATHS)], indirect=True)
def test_pathmanager(pathmanager, qtbot):
    """Run PathManager test"""
    pathmanager.show()
    assert pathmanager


@pytest.mark.parametrize('pathmanager', [(PATHS, ROPATHS)], indirect=True)
def test_check_uncheck_path(pathmanager):
    """
    Test that checking and unchecking a path in the PathManager correctly
    update the not active path list.
    """
    # Assert that all paths are checked.
    for row in range(pathmanager.listwidget.count()):
        assert pathmanager.listwidget.item(row).checkState() == Qt.Checked


@pytest.mark.skipif(os.name != 'nt' or not is_module_installed('win32con'),
                    reason=("This feature is not applicable for Unix "
                            "systems and pywin32 is needed"))
@pytest.mark.parametrize('pathmanager', [(WPATHS, WROPATHS)], indirect=True)
def test_export_to_PYTHONPATH(pathmanager, mocker):
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

    expected_pathlist = list(WPATHS) + list(WROPATHS)

    # Assert that PYTHONPATH is synchronized correctly with Spyder's path list
    pathmanager.export_pythonpath()
    env = get_user_env()
    assert env['PYTHONPATH'] == expected_pathlist

    # Uncheck 'path2' and assert that it is removed from PYTHONPATH when it
    # is synchronized with Spyder's path list
    pathmanager.listwidget.item(1).setCheckState(Qt.Unchecked)
    pathmanager.export_pythonpath()
    expected_pathlist.pop(1)
    env = get_user_env()
    assert env['PYTHONPATH'] == expected_pathlist

    # Mock the dialog window and answer "No" to clear contents of PYTHONPATH
    # before adding Spyder's path list
    mocker.patch.object(pathmanager_mod.QMessageBox, 'question',
                        return_value=pathmanager_mod.QMessageBox.No)

    # Uncheck 'path3' and assert that it is kept in PYTHONPATH when it
    # is synchronized with Spyder's path list
    pathmanager.listwidget.item(2).setCheckState(Qt.Unchecked)
    pathmanager.export_pythonpath()
    p3 = expected_pathlist.pop(1)
    expected_pathlist.insert(0, p3)
    env = get_user_env()
    assert env['PYTHONPATH'] == expected_pathlist

    # Restore PYTHONPATH to its original state
    env['PYTHONPATH'] = original_pathlist
    set_user_env(listdict2envdict(env))


@pytest.mark.parametrize('pathmanager', [(PATHS, ROPATHS)], indirect=True)
def test_invalid_directories(qtbot, pathmanager):
    """Check [site/dist]-packages are invalid paths."""
    if os.name == 'nt':
        paths = ['/lib/site-packages/foo',
                 '/lib/dist-packages/foo']
    else:
        paths = ['/lib/python3.6/site-packages/foo',
                 '/lib/python3.6/dist-packages/foo']

    def interact_message_box():
        child = pathmanager.findChild(QMessageBox)
        qtbot.keyPress(child, Qt.Key_Enter)

    for path in paths:
        timer = QTimer()
        timer.setSingleShot(True)
        timer.timeout.connect(interact_message_box)
        timer.start(300)
        assert not pathmanager.check_path(path)
        pathmanager.add_path(path)


@pytest.mark.parametrize('pathmanager', [(SPATHS, SROPATHS)], indirect=True)
def test_remove_item_and_reply_no(qtbot, pathmanager):
    """Check that the item is not removed after answering 'No'."""
    pathmanager.show()
    count = pathmanager.count()

    def interact_message_box():
        messagebox = pathmanager.findChild(QMessageBox)
        buttons = messagebox.findChildren(QPushButton)
        for button in buttons:
            if 'no' in button.text().lower():
                qtbot.mouseClick(button, Qt.LeftButton)
                break

    timer = QTimer()
    timer.setSingleShot(True)
    timer.timeout.connect(interact_message_box)
    timer.start(100)
    qtbot.mouseClick(pathmanager.remove_button, Qt.LeftButton)

    # Back to main thread
    assert pathmanager.count() == count


@pytest.mark.parametrize('pathmanager', [(SPATHS, SROPATHS)], indirect=True)
def test_remove_item_and_reply_yes(qtbot, pathmanager):
    """Check that the item is indeed removed after answering 'Yes'."""
    pathmanager.show()
    count = pathmanager.count()

    def interact_message_box():
        messagebox = pathmanager.findChild(QMessageBox)
        buttons = messagebox.findChildren(QPushButton)
        for button in buttons:
            if 'yes' in button.text().lower():
                qtbot.mouseClick(button, Qt.LeftButton)
                break

    timer = QTimer()
    timer.setSingleShot(True)
    timer.timeout.connect(interact_message_box)
    timer.start(100)
    qtbot.mouseClick(pathmanager.remove_button, Qt.LeftButton)

    # Back to main thread
    assert pathmanager.count() == (count - 1)


@pytest.mark.parametrize('pathmanager', [(None, ())], indirect=True)
def test_add_repeated_item(qtbot, pathmanager, tmpdir):
    """
    Check behavior when an unchecked item that is already on the list is added.
    The checkbox should then be checked and if replying 'yes' to the question,
    then the item should be moved to the top.
    """
    pathmanager.show()
    dir1 = str(tmpdir.mkdir("foo"))
    dir2 = str(tmpdir.mkdir("bar"))
    dir3 = str(tmpdir.mkdir("spam"))
    pathmanager.add_path(dir1)
    pathmanager.add_path(dir2)
    pathmanager.add_path(dir3)
    pathmanager.set_row_check_state(1, Qt.Unchecked)
    assert not all(pathmanager.get_path_dict().values())

    def interact_message_box():
        messagebox = pathmanager.findChild(QMessageBox)
        buttons = messagebox.findChildren(QPushButton)
        for button in buttons:
            if 'yes' in button.text().lower():
                qtbot.mouseClick(button, Qt.LeftButton)
                break

    timer = QTimer()
    timer.setSingleShot(True)
    timer.timeout.connect(interact_message_box)
    timer.start(500)
    pathmanager.add_path(dir2)
    print(pathmanager.get_path_dict())

    # Back to main thread
    assert pathmanager.count() == 3
    assert list(pathmanager.get_path_dict().keys())[0] == dir2
    assert all(pathmanager.get_path_dict().values())


@pytest.mark.parametrize('pathmanager', [(SPATHS, SROPATHS)], indirect=True)
def test_buttons_state(qtbot, pathmanager, tmpdir):
    """Check buttons are enabled/disabled based on items and position."""
    pathmanager.show()
    assert not pathmanager.button_ok.isEnabled()
    assert not pathmanager.movetop_button.isEnabled()
    assert not pathmanager.moveup_button.isEnabled()
    assert pathmanager.movebottom_button.isEnabled()
    assert pathmanager.movedown_button.isEnabled()

    pathmanager.set_current_row(1)
    assert not pathmanager.button_ok.isEnabled()
    assert pathmanager.movetop_button.isEnabled()
    assert pathmanager.moveup_button.isEnabled()
    assert not pathmanager.movebottom_button.isEnabled()
    assert not pathmanager.movedown_button.isEnabled()

    # Check adding a path updates the ok button
    path = tmpdir.mkdir("bloop")
    pathmanager.add_path(str(path))
    assert pathmanager.button_ok.isEnabled()
    assert not pathmanager.movetop_button.isEnabled()
    assert not pathmanager.moveup_button.isEnabled()

    # Check bottom state
    pathmanager.movebottom_button.animateClick()
    qtbot.waitUntil(pathmanager.movetop_button.isEnabled)
    assert pathmanager.movetop_button.isEnabled()
    assert pathmanager.moveup_button.isEnabled()
    assert not pathmanager.movebottom_button.isEnabled()
    assert not pathmanager.movedown_button.isEnabled()
    assert pathmanager.current_row() == 2

    # Check delete and ok button
    pathmanager.remove_path(True)
    assert not pathmanager.button_ok.isEnabled()


if __name__ == "__main__":
    pytest.main([os.path.basename(__file__)])
