# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright © Spyder Project Contributors
#
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)
# -----------------------------------------------------------------------------

"""
Tests for the dataframe editor.
"""

from __future__ import division

# Standard library imports
import os
import sys
from datetime import datetime
try:
    from unittest.mock import Mock, ANY
except ImportError:
    from mock import Mock, ANY  # Python 2

# Third party imports
from pandas import DataFrame, date_range, read_csv, concat
from qtpy.QtGui import QColor
from qtpy.QtCore import Qt, QTimer
import numpy
import pytest
from flaky import flaky

# Local imports
from spyder.utils.programs import is_module_installed
from spyder.utils.test import close_message_box
from spyder.widgets.variableexplorer import dataframeeditor
from spyder.widgets.variableexplorer.dataframeeditor import (
    DataFrameEditor, DataFrameModel)


# =============================================================================
# Constants
# =============================================================================
FILES_PATH = os.path.dirname(os.path.realpath(__file__))


# =============================================================================
# Utility functions
# =============================================================================
def colorclose(color, hsva_expected):
    """
    Compares HSV values which are stored as 16-bit integers.
    """
    hsva_actual = color.getHsvF()
    return all(abs(a-b) <= 2**(-16) for (a,b) in zip(hsva_actual, hsva_expected))

def data(dfm, i, j):
    return dfm.data(dfm.createIndex(i, j))

def bgcolor(dfm, i, j):
    return dfm.get_bgcolor(dfm.createIndex(i, j))


# =============================================================================
# Tests
# =============================================================================
def test_dataframemodel_basic():
    df = DataFrame({'colA': [1, 3], 'colB': ['c', 'a']})
    dfm = DataFrameModel(df)
    assert dfm.rowCount() == 2
    assert dfm.columnCount() == 3
    assert data(dfm, 0, 0) == '0'
    assert data(dfm, 0, 1) == '1'
    assert data(dfm, 0, 2) == 'c'
    assert data(dfm, 1, 0) == '1'
    assert data(dfm, 1, 1) == '3'
    assert data(dfm, 1, 2) == 'a'

def test_dataframemodel_sort():
    df = DataFrame({'colA': [1, 3], 'colB': ['c', 'a']})
    dfm = DataFrameModel(df)
    dfm.sort(2)
    assert data(dfm, 0, 0) == '1'
    assert data(dfm, 0, 1) == '3'
    assert data(dfm, 0, 2) == 'a'
    assert data(dfm, 1, 0) == '0'
    assert data(dfm, 1, 1) == '1'
    assert data(dfm, 1, 2) == 'c'

def test_dataframemodel_sort_is_stable():   # cf. issue 3010
    df = DataFrame([[2,14], [2,13], [2,16], [1,3], [2,9], [1,15], [1,17],
                    [2,2], [2,10], [1,6], [2,5], [2,8], [1,11], [1,1],
                    [1,12], [1,4], [2,7]])
    dfm = DataFrameModel(df)
    dfm.sort(2)
    dfm.sort(1)
    col2 = [data(dfm, i, 2) for i in range(len(df))]
    assert col2 == [str(x) for x in [1, 3, 4, 6, 11, 12, 15, 17,
                                     2, 5, 7, 8, 9, 10, 13, 14, 16]]

def test_dataframemodel_max_min_col_update():
    df = DataFrame([[1, 2.0], [2, 2.5], [3, 9.0]])
    dfm = DataFrameModel(df)
    assert dfm.max_min_col == [[3, 1], [9.0, 2.0]]

def test_dataframemodel_max_min_col_update_constant():
    df = DataFrame([[1, 2.0], [1, 2.0], [1, 2.0]])
    dfm = DataFrameModel(df)
    assert dfm.max_min_col == [[1, 0], [2.0, 1.0]]

def test_dataframemodel_with_timezone_aware_timestamps(): # cf. issue 2940
    df = DataFrame([x] for x in date_range('20150101', periods=5, tz='UTC'))
    dfm = DataFrameModel(df)
    assert dfm.max_min_col == [None]

def test_dataframemodel_with_categories(): # cf. issue 3308
    df = DataFrame({"id": [1, 2, 3, 4, 5, 6],
                    "raw_grade": ['a', 'b', 'b', 'a', 'a', 'e']})
    df["grade"] = df["raw_grade"].astype("category")
    dfm = DataFrameModel(df)
    assert dfm.max_min_col == [[6, 1], None, None]

def test_dataframemodel_get_bgcolor_with_numbers():
    df = DataFrame([[0, 10], [1, 20], [2, 40]])
    dfm = DataFrameModel(df)
    h0 = dataframeeditor.BACKGROUND_NUMBER_MINHUE
    dh = dataframeeditor.BACKGROUND_NUMBER_HUERANGE
    s = dataframeeditor.BACKGROUND_NUMBER_SATURATION
    v = dataframeeditor.BACKGROUND_NUMBER_VALUE
    a = dataframeeditor.BACKGROUND_NUMBER_ALPHA
    assert colorclose(bgcolor(dfm, 0, 1), (h0 + dh,         s, v, a))
    assert colorclose(bgcolor(dfm, 1, 1), (h0 + 1 / 2 * dh, s, v, a))
    assert colorclose(bgcolor(dfm, 2, 1), (h0,              s, v, a))
    assert colorclose(bgcolor(dfm, 0, 2), (h0 + dh,         s, v, a))
    assert colorclose(bgcolor(dfm, 1, 2), (h0 + 2 / 3 * dh, s, v, a))
    assert colorclose(bgcolor(dfm, 2, 2), (h0,              s, v, a))

def test_dataframemodel_get_bgcolor_with_numbers_using_global_max():
    df = DataFrame([[0, 10], [1, 20], [2, 40]])
    dfm = DataFrameModel(df)
    dfm.colum_avg(0)
    h0 = dataframeeditor.BACKGROUND_NUMBER_MINHUE
    dh = dataframeeditor.BACKGROUND_NUMBER_HUERANGE
    s = dataframeeditor.BACKGROUND_NUMBER_SATURATION
    v = dataframeeditor.BACKGROUND_NUMBER_VALUE
    a = dataframeeditor.BACKGROUND_NUMBER_ALPHA
    assert colorclose(bgcolor(dfm, 0, 1), (h0 + dh,           s, v, a))
    assert colorclose(bgcolor(dfm, 1, 1), (h0 + 39 / 40 * dh, s, v, a))
    assert colorclose(bgcolor(dfm, 2, 1), (h0 + 38 / 40 * dh, s, v, a))
    assert colorclose(bgcolor(dfm, 0, 2), (h0 + 30 / 40 * dh, s, v, a))
    assert colorclose(bgcolor(dfm, 1, 2), (h0 + 20 / 40 * dh, s, v, a))
    assert colorclose(bgcolor(dfm, 2, 2), (h0,                s, v, a))

def test_dataframemodel_get_bgcolor_for_index():
    df = DataFrame([[0]])
    dfm = DataFrameModel(df)
    h, s, v, dummy = QColor(dataframeeditor.BACKGROUND_NONNUMBER_COLOR).getHsvF()
    a = dataframeeditor.BACKGROUND_INDEX_ALPHA
    assert colorclose(bgcolor(dfm, 0, 0), (h, s, v, a))

def test_dataframemodel_get_bgcolor_with_string():
    df = DataFrame([['xxx']])
    dfm = DataFrameModel(df)
    h, s, v, dummy = QColor(dataframeeditor.BACKGROUND_NONNUMBER_COLOR).getHsvF()
    a = dataframeeditor.BACKGROUND_STRING_ALPHA
    assert colorclose(bgcolor(dfm, 0, 1), (h, s, v, a))

def test_dataframemodel_get_bgcolor_with_object():
    df = DataFrame([[None]])
    dfm = DataFrameModel(df)
    h, s, v, dummy = QColor(dataframeeditor.BACKGROUND_NONNUMBER_COLOR).getHsvF()
    a = dataframeeditor.BACKGROUND_MISC_ALPHA
    assert colorclose(bgcolor(dfm, 0, 1), (h, s, v, a))

def test_dataframemodel_with_format_percent_d_and_nan():
    """
    Test DataFrameModel with format `%d` and dataframe containing NaN

    Regression test for issue #4139.
    """
    np_array = numpy.zeros(2)
    np_array[1] = numpy.nan
    dataframe = DataFrame(np_array)
    dfm = DataFrameModel(dataframe, format='%d')
    assert data(dfm, 0, 1) == '0'
    assert data(dfm, 1, 1) == 'nan'

def test_change_format_emits_signal(qtbot, monkeypatch):
    mockQInputDialog = Mock()
    mockQInputDialog.getText = lambda parent, title, label, mode, text: ('%10.3e', True)
    monkeypatch.setattr('spyder.widgets.variableexplorer.dataframeeditor.QInputDialog', mockQInputDialog)
    df = DataFrame([[0]])
    editor = DataFrameEditor(None)
    editor.setup_and_check(df)
    with qtbot.waitSignal(editor.sig_option_changed) as blocker:
        editor.change_format()
    assert blocker.args == ['dataframe_format', '%10.3e']

def test_change_format_with_format_not_starting_with_percent(qtbot, monkeypatch):
    mockQInputDialog = Mock()
    mockQInputDialog.getText = lambda parent, title, label, mode, text: ('xxx%f', True)
    monkeypatch.setattr('spyder.widgets.variableexplorer.dataframeeditor'
                        '.QInputDialog', mockQInputDialog)
    monkeypatch.setattr('spyder.widgets.variableexplorer.dataframeeditor'
                        '.QMessageBox.critical', Mock())
    df = DataFrame([[0]])
    editor = DataFrameEditor(None)
    editor.setup_and_check(df)
    with qtbot.assertNotEmitted(editor.sig_option_changed):
        editor.change_format()

def test_header_bom():
    df = read_csv(os.path.join(FILES_PATH, 'issue_2514.csv'))
    editor = DataFrameEditor(None)
    editor.setup_and_check(df)
    model = editor.dataModel
    assert model.headerData(1, orientation=Qt.Horizontal) == "Date (MMM-YY)"

@pytest.mark.skipif(is_module_installed('pandas', '<0.19'),
                    reason="It doesn't work for Pandas 0.19-")
def test_header_encoding():
    df = read_csv(os.path.join(FILES_PATH, 'issue_3896.csv'))
    editor = DataFrameEditor(None)
    editor.setup_and_check(df)
    model = editor.dataModel
    assert model.headerData(0, orientation=Qt.Horizontal) == "Index"
    assert model.headerData(1, orientation=Qt.Horizontal) == "Unnamed: 0"
    assert model.headerData(2, orientation=Qt.Horizontal) == "Unieke_Idcode"
    assert model.headerData(3, orientation=Qt.Horizontal) == "a"
    assert model.headerData(4, orientation=Qt.Horizontal) == "b"
    assert model.headerData(5, orientation=Qt.Horizontal) == "c"
    assert model.headerData(6, orientation=Qt.Horizontal) == "d"

def test_dataframeeditor_with_datetimeindex():
    rng = date_range('20150101', periods=3)
    editor = DataFrameEditor(None)
    editor.setup_and_check(rng)
    dfm = editor.dataModel
    assert dfm.rowCount() == 3
    assert dfm.columnCount() == 2
    assert data(dfm, 0, 1) == '2015-01-01 00:00:00'
    assert data(dfm, 1, 1) == '2015-01-02 00:00:00'
    assert data(dfm, 2, 1) == '2015-01-03 00:00:00'

def test_dataframeeditor_with_OutOfBoundsDatetime():  # Test for #6177
    df = DataFrame([{'DATETIME': datetime.strptime("9999-1-1T00:00",
                                                   "%Y-%m-%dT%H:%M")}])
    model = DataFrameModel(df)
    try:
        model.get_value(0, 0)
    except Exception:
        assert False

@pytest.mark.skipif(not os.name == 'nt',
                    reason="It segfaults too much on Linux")
def test_sort_dataframe_with_duplicate_column(qtbot):
    df = DataFrame({'A': [1, 3, 2], 'B': [4, 6, 5]})
    df = concat((df, df.A), axis=1)
    editor = DataFrameEditor(None)
    editor.setup_and_check(df)
    dfm = editor.dataModel
    QTimer.singleShot(1000, lambda: close_message_box(qtbot))
    editor.dataModel.sort(1)
    assert [data(dfm, row, 1) for row in range(len(df))] == ['1', '3', '2']
    assert [data(dfm, row, 2) for row in range(len(df))] == ['4', '6', '5']
    editor.dataModel.sort(2)
    assert [data(dfm, row, 1) for row in range(len(df))] == ['1', '2', '3']
    assert [data(dfm, row, 2) for row in range(len(df))] == ['4', '5', '6']


@pytest.mark.skipif(not os.name == 'nt',
                    reason="It segfaults too much on Linux")
def test_sort_dataframe_with_category_dtypes(qtbot):  # cf. issue 5361
    df = DataFrame({'A': [1, 2, 3, 4],
                    'B': ['a', 'b', 'c', 'd']})
    df = df.astype(dtype={'B': 'category'})
    df_cols = df.dtypes
    editor = DataFrameEditor(None)
    editor.setup_and_check(df_cols)
    dfm = editor.dataModel
    QTimer.singleShot(1000, lambda: close_message_box(qtbot))
    editor.dataModel.sort(1)
    assert data(dfm, 0, 1) == 'int64'
    assert data(dfm, 1, 1) == 'category'


def test_dataframemodel_set_data_overflow(monkeypatch):
    """
    Test that entry of an overflowing integer is caught and handled properly.

    Unit regression test for issue #6114 .
    """
    MockQMessageBox = Mock()
    attr_to_patch = ('spyder.widgets.variableexplorer' +
                     '.dataframeeditor.QMessageBox')
    monkeypatch.setattr(attr_to_patch, MockQMessageBox)

    # Numpy doesn't raise the OverflowError for ints smaller than 64 bits
    if not os.name == 'nt':
        int32_bit_exponent = 66
    else:
        int32_bit_exponent = 34
    test_parameters = [(1, numpy.int32, int32_bit_exponent),
                       (2, numpy.int64, 66)]

    for idx, int_type, bit_exponent in test_parameters:
        test_df = DataFrame(numpy.arange(7, 11), dtype=int_type)
        model = DataFrameModel(test_df.copy())
        index = model.createIndex(2, 1)
        assert not model.setData(index, str(int(2 ** bit_exponent)))
        MockQMessageBox.critical.assert_called_with(ANY, "Error", ANY)
        assert MockQMessageBox.critical.call_count == idx
        assert numpy.sum(test_df[0].as_matrix() ==
                         model.df.as_matrix()) == len(test_df)


@flaky(max_runs=3)
@pytest.mark.no_xvfb
@pytest.mark.skipif(sys.platform == 'darwin', reason="It fails on macOS")
def test_dataframeeditor_edit_overflow(qtbot, monkeypatch):
    """
    Test that entry of an overflowing integer is caught and handled properly.

    Integration regression test for issue #6114 .
    """
    MockQMessageBox = Mock()
    attr_to_patch = ('spyder.widgets.variableexplorer' +
                     '.dataframeeditor.QMessageBox')
    monkeypatch.setattr(attr_to_patch, MockQMessageBox)

    # Numpy doesn't raise the OverflowError for ints smaller than 64 bits
    if not os.name == 'nt':
        int32_bit_exponent = 66
    else:
        int32_bit_exponent = 34
    test_parameters = [(1, numpy.int32, int32_bit_exponent),
                       (2, numpy.int64, 66)]
    expected_df = DataFrame([5, 6, 7, 3, 4])

    for idx, int_type, bit_exponet in test_parameters:
        test_df = DataFrame(numpy.arange(0, 5), dtype=int_type)
        dialog = DataFrameEditor()
        assert dialog.setup_and_check(test_df, 'Test Dataframe')
        dialog.show()
        qtbot.waitForWindowShown(dialog)
        view = dialog.dataTable

        qtbot.keyClick(view, Qt.Key_Right)
        qtbot.keyClicks(view, '5')
        qtbot.keyClick(view, Qt.Key_Down)
        qtbot.keyClick(view, Qt.Key_Space)
        qtbot.keyClick(view.focusWidget(), Qt.Key_Backspace)
        qtbot.keyClicks(view.focusWidget(), str(int(2 ** bit_exponet)))
        qtbot.keyClick(view.focusWidget(), Qt.Key_Down)
        MockQMessageBox.critical.assert_called_with(ANY, "Error", ANY)
        assert MockQMessageBox.critical.call_count == idx
        qtbot.keyClicks(view, '7')
        qtbot.keyClick(view, Qt.Key_Up)
        qtbot.keyClicks(view, '6')
        qtbot.keyClick(view, Qt.Key_Down)
        qtbot.wait(200)
        dialog.accept()
        qtbot.wait(500)
        assert numpy.sum(expected_df[0].as_matrix() ==
                         dialog.get_value().as_matrix()) == len(expected_df)


def test_dataframemodel_set_data_complex(monkeypatch):
    """
    Test that editing complex dtypes is handled gracefully in df editor.

    Unit regression test for issue #6115 .
    """
    MockQMessageBox = Mock()
    attr_to_patch = ('spyder.widgets.variableexplorer' +
                     '.dataframeeditor.QMessageBox')
    monkeypatch.setattr(attr_to_patch, MockQMessageBox)

    test_params = [(1, numpy.complex128), (2, numpy.complex64), (3, complex)]

    for count, complex_type in test_params:
        test_df = DataFrame(numpy.arange(10, 15), dtype=complex_type)
        model = DataFrameModel(test_df.copy())
        index = model.createIndex(2, 1)
        assert not model.setData(index, '42')
        MockQMessageBox.critical.assert_called_with(ANY, "Error", ANY)
        assert MockQMessageBox.critical.call_count == count
        assert numpy.sum(test_df[0].as_matrix() ==
                         model.df.as_matrix()) == len(test_df)


@flaky(max_runs=3)
@pytest.mark.no_xvfb
@pytest.mark.skipif(sys.platform == 'darwin', reason="It fails on macOS")
def test_dataframeeditor_edit_complex(qtbot, monkeypatch):
    """
    Test that editing complex dtypes is handled gracefully in df editor.

    Integration regression test for issue #6115 .
    """
    MockQMessageBox = Mock()
    attr_to_patch = ('spyder.widgets.variableexplorer' +
                     '.dataframeeditor.QMessageBox')
    monkeypatch.setattr(attr_to_patch, MockQMessageBox)

    test_params = [(1, numpy.complex128), (2, numpy.complex64), (3, complex)]

    for count, complex_type in test_params:
        test_df = DataFrame(numpy.arange(10, 15), dtype=complex_type)
        dialog = DataFrameEditor()
        assert dialog.setup_and_check(test_df, 'Test Dataframe')
        dialog.show()
        qtbot.waitForWindowShown(dialog)
        view = dialog.dataTable

        qtbot.keyClick(view, Qt.Key_Right)
        qtbot.keyClick(view, Qt.Key_Down)
        qtbot.keyClick(view, Qt.Key_Space)
        qtbot.keyClick(view.focusWidget(), Qt.Key_Backspace)
        qtbot.keyClicks(view.focusWidget(), "42")
        qtbot.keyClick(view.focusWidget(), Qt.Key_Down)
        MockQMessageBox.critical.assert_called_with(ANY, "Error", ANY)
        assert MockQMessageBox.critical.call_count == count * 2 - 1
        qtbot.keyClick(view, Qt.Key_Down)
        qtbot.keyClick(view, '1')
        qtbot.keyClick(view.focusWidget(), Qt.Key_Down)
        MockQMessageBox.critical.assert_called_with(
            ANY, "Error", ("Editing dtype {0!s} not yet supported."
                           .format(type(test_df.iloc[1, 0]).__name__)))
        assert MockQMessageBox.critical.call_count == count * 2
        qtbot.wait(200)
        dialog.accept()
        qtbot.wait(500)
        assert numpy.sum(test_df[0].as_matrix() ==
                         dialog.get_value().as_matrix()) == len(test_df)


def test_dataframemodel_set_data_bool(monkeypatch):
    """Test that bools are editible in df and false-y strs are detected."""
    MockQMessageBox = Mock()
    attr_to_patch = ('spyder.widgets.variableexplorer' +
                     '.dataframeeditor.QMessageBox')
    monkeypatch.setattr(attr_to_patch, MockQMessageBox)

    test_params = [numpy.bool_, numpy.bool, bool]
    test_strs = ['foo', 'false', 'f', '0', '0.', '0.0', '', ' ']
    expected_df = DataFrame([1, 0, 0, 0, 0, 0, 0, 0, 0], dtype=bool)

    for bool_type in test_params:
        test_df = DataFrame([0, 1, 1, 1, 1, 1, 1, 1, 0], dtype=bool_type)
        model = DataFrameModel(test_df.copy())
        for idx, test_str in enumerate(test_strs):
            assert model.setData(model.createIndex(idx, 1), test_str)
            assert not MockQMessageBox.critical.called
        assert numpy.sum(expected_df[0].as_matrix() ==
                         model.df.as_matrix()[:, 0]) == len(expected_df)


@flaky(max_runs=3)
@pytest.mark.no_xvfb
@pytest.mark.skipif(sys.platform == 'darwin', reason="It fails on macOS")
def test_dataframeeditor_edit_bool(qtbot, monkeypatch):
    """Test that bools are editible in df and false-y strs are detected."""
    MockQMessageBox = Mock()
    attr_to_patch = ('spyder.widgets.variableexplorer' +
                     '.dataframeeditor.QMessageBox')
    monkeypatch.setattr(attr_to_patch, MockQMessageBox)

    test_params = [numpy.bool_, numpy.bool, bool]
    test_strs = ['foo', 'false', 'f', '0', '0.', '0.0', '', ' ']
    expected_df = DataFrame([1, 0, 0, 0, 0, 0, 0, 0, 0], dtype=bool)

    for bool_type in test_params:
        test_df = DataFrame([0, 1, 1, 1, 1, 1, 1, 1, 0], dtype=bool_type)
        dialog = DataFrameEditor()
        assert dialog.setup_and_check(test_df, 'Test Dataframe')
        dialog.show()
        qtbot.waitForWindowShown(dialog)
        view = dialog.dataTable

        qtbot.keyClick(view, Qt.Key_Right)
        for test_str in test_strs:
            qtbot.keyClick(view, Qt.Key_Space)
            qtbot.keyClick(view.focusWidget(), Qt.Key_Backspace)
            qtbot.keyClicks(view.focusWidget(), test_str)
            qtbot.keyClick(view.focusWidget(), Qt.Key_Down)
            assert not MockQMessageBox.critical.called
        qtbot.wait(200)
        dialog.accept()
        qtbot.wait(500)
        assert (numpy.sum(expected_df[0].as_matrix() ==
                          dialog.get_value().as_matrix()[:, 0]) ==
                len(expected_df))


if __name__ == "__main__":
    pytest.main()
