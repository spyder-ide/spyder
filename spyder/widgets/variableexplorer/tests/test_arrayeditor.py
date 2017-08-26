# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License

"""
Tests for arrayeditor.py
"""

# Stdlib imports
import os

# Third party imports
import numpy as np
from numpy.testing import assert_array_equal
import pytest
from qtpy.QtCore import Qt

# Local imports
from spyder.widgets.variableexplorer.arrayeditor import ArrayEditor


def launch_arrayeditor(data, title="", xlabels=None, ylabels=None):
    """Helper routine to launch an arrayeditor and return its result"""
    dlg = ArrayEditor()
    assert dlg.setup_and_check(data, title, xlabels=xlabels, ylabels=ylabels)
    dlg.show()
    dlg.accept()  # trigger slot connected to OK button
    return dlg.get_value()

def setup_arrayeditor(qbot, data, title="", xlabels=None, ylabels=None):
    """Setups an arrayeditor."""
    dlg = ArrayEditor()
    dlg.setup_and_check(data, title, xlabels=xlabels, ylabels=ylabels)    
    dlg.show()
    qbot.addWidget(dlg)
    return dlg

# --- Tests
# -----------------------------------------------------------------------------
def test_arrayeditor_format(qtbot):
    """Changes the format of the array and validates its selected content."""
    arr = np.array([1, 2, 3], dtype=np.float32)
    dlg = setup_arrayeditor(qtbot, arr, "test array float32")
    qtbot.keyClick(dlg.arraywidget.view, Qt.Key_Down, modifier=Qt.ShiftModifier)
    qtbot.keyClick(dlg.arraywidget.view, Qt.Key_Down, modifier=Qt.ShiftModifier)
    contents = dlg.arraywidget.view._sel_to_text(dlg.arraywidget.view.selectedIndexes())
    assert contents == "1\n2\n"
    dlg.arraywidget.view.model().set_format("%.18e")
    assert dlg.arraywidget.view.model().get_format() == "%.18e"
    qtbot.keyClick(dlg.arraywidget.view, Qt.Key_Down, modifier=Qt.ShiftModifier)
    qtbot.keyClick(dlg.arraywidget.view, Qt.Key_Down, modifier=Qt.ShiftModifier)
    contents = dlg.arraywidget.view._sel_to_text(dlg.arraywidget.view.selectedIndexes())
    assert contents == "1.000000000000000000e+00\n2.000000000000000000e+00\n"
    

def test_arrayeditor_with_string_array(qtbot):
    arr = np.array(["kjrekrjkejr"])
    assert arr == launch_arrayeditor(arr, "string array")


def test_arrayeditor_with_unicode_array(qtbot):
    arr = np.array([u"ñññéáíó"])
    assert arr == launch_arrayeditor(arr, "unicode array")


def test_arrayeditor_with_masked_array(qtbot):
    arr = np.ma.array([[1, 0], [1, 0]], mask=[[True, False], [False, False]])
    assert_array_equal(arr, launch_arrayeditor(arr, "masked array"))


def test_arrayeditor_with_record_array(qtbot):
    arr = np.zeros((2, 2), {'names': ('red', 'green', 'blue'),
                           'formats': (np.float32, np.float32, np.float32)})
    assert_array_equal(arr, launch_arrayeditor(arr, "record array"))


@pytest.mark.skipif(not os.name == 'nt', reason="It segfaults sometimes on Linux")
def test_arrayeditor_with_record_array_with_titles(qtbot):
    arr = np.array([(0, 0.0), (0, 0.0), (0, 0.0)],
                   dtype=[(('title 1', 'x'), '|i1'),
                          (('title 2', 'y'), '>f4')])
    assert_array_equal(arr, launch_arrayeditor(arr, "record array with titles"))


def test_arrayeditor_with_float_array(qtbot):
    arr = np.random.rand(5, 5)
    assert_array_equal(arr, launch_arrayeditor(arr, "float array",
                                      xlabels=['a', 'b', 'c', 'd', 'e']))


def test_arrayeditor_with_complex_array(qtbot):
    arr = np.round(np.random.rand(5, 5)*10)+\
                   np.round(np.random.rand(5, 5)*10)*1j
    assert_array_equal(arr, launch_arrayeditor(arr, "complex array",
                                      xlabels=np.linspace(-12, 12, 5),
                                      ylabels=np.linspace(-12, 12, 5)))


def test_arrayeditor_with_bool_array(qtbot):
    arr_in = np.array([True, False, True])
    arr_out = launch_arrayeditor(arr_in, "bool array")
    assert arr_in is arr_out

def test_arrayeditor_with_int8_array(qtbot):
    arr = np.array([1, 2, 3], dtype="int8")
    assert_array_equal(arr, launch_arrayeditor(arr, "int array"))


def test_arrayeditor_with_float16_array(qtbot):
    arr = np.zeros((5,5), dtype=np.float16)
    assert_array_equal(arr, launch_arrayeditor(arr, "float16 array"))


def test_arrayeditor_with_3d_array(qtbot):
    arr = np.zeros((3,3,4))
    arr[0,0,0]=1
    arr[0,0,1]=2
    arr[0,0,2]=3
    assert_array_equal(arr, launch_arrayeditor(arr, "3D array"))


def test_arrayeditor_edit_1d_array(qtbot):
    exp_arr = np.array([1, 0, 2, 3, 4])
    arr = np.arange(0, 5)
    dlg = ArrayEditor()
    assert dlg.setup_and_check(arr, '1D array', xlabels=None, ylabels=None)
    dlg.show()
    qtbot.waitForWindowShown(dlg)
    view = dlg.arraywidget.view

    qtbot.keyPress(view, Qt.Key_Down)
    qtbot.keyPress(view, Qt.Key_Up)
    qtbot.keyClicks(view, '1')
    qtbot.keyPress(view, Qt.Key_Down)
    qtbot.keyClicks(view, '0')
    qtbot.keyPress(view, Qt.Key_Down)
    qtbot.keyPress(view, Qt.Key_Return)
    assert np.sum(exp_arr == dlg.get_value()) == 5


def test_arrayeditor_edit_2d_array(qtbot):
    arr = np.ones((3, 3))
    exp_arr = arr.copy()
    exp_arr[1, 1] = 3
    exp_arr[2, 2] = 0
    dlg = ArrayEditor()
    assert dlg.setup_and_check(arr, '2D array', xlabels=None, ylabels=None)
    dlg.show()
    qtbot.waitForWindowShown(dlg)
    view = dlg.arraywidget.view

    qtbot.keyPress(view, Qt.Key_Down)
    qtbot.keyPress(view, Qt.Key_Right)
    qtbot.keyClicks(view, '3')
    qtbot.keyPress(view, Qt.Key_Down)
    qtbot.keyPress(view, Qt.Key_Right)
    qtbot.keyClicks(view, '0')
    qtbot.keyPress(view, Qt.Key_Left)
    qtbot.keyPress(view, Qt.Key_Return)

    assert np.sum(exp_arr == dlg.get_value()) == 9


if __name__ == "__main__":
    pytest.main()
