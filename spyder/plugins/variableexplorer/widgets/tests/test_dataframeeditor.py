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
from pandas import (DataFrame, date_range, read_csv, concat, Index, RangeIndex,
                    DatetimeIndex, MultiIndex, CategoricalIndex)
from qtpy.QtGui import QColor
from qtpy.QtCore import Qt, QTimer
import numpy
import pytest
from flaky import flaky

# Local imports
from spyder.utils.programs import is_module_installed
from spyder.utils.test import close_message_box
from spyder.plugins.variableexplorer.widgets import dataframeeditor
from spyder.plugins.variableexplorer.widgets.dataframeeditor import (
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

def data_header(dfh, i, j, role=Qt.DisplayRole):
    return dfh.data(dfh.createIndex(i, j), role)

def data_index(dfi, i, j, role=Qt.DisplayRole):
    return dfi.data(dfi.createIndex(i, j), role)

def generate_pandas_indexes():
    """ Creates a dictionnary of many possible pandas indexes """
    return {
        'Index': Index(list('ABCDEFGHIJKLMNOPQRST')),
        'RangeIndex': RangeIndex(0, 20),
        'Float64Index': Index([i/10 for i in range(20)]),
        'DatetimeIndex': DatetimeIndex(start='2017-01-01', periods=20,
                                       freq='D'),
        'MultiIndex': MultiIndex.from_product(
            [list('ABCDEFGHIJ'), ('foo', 'bar')], names=['first', 'second']),
        'CategoricalIndex': CategoricalIndex(list('abcaadaccbbacabacccb'),
                                             categories=['a', 'b', 'c']),
        }



# =============================================================================
# Tests
# =============================================================================

def test_dataframe_simpleindex(qtbot):
    """Test to validate proper creation and handling of a simpleindex."""
    df = DataFrame(numpy.random.randn(6, 6))
    editor = DataFrameEditor(None)
    editor.setup_and_check(df)
    header = editor.table_header.model()
    assert header.headerData(0, Qt.Horizontal,
                             Qt.DisplayRole) == "0"
    assert header.headerData(1, Qt.Horizontal,
                             Qt.DisplayRole) == "1"
    assert header.headerData(5, Qt.Horizontal,
                             Qt.DisplayRole) == "5"


def test_dataframe_simpleindex_custom_columns():
    """Test to validate proper creation and handling of custom simpleindex."""
    df = DataFrame(numpy.random.randn(10, 5),
                   columns=['a', 'b', 'c', 'd', 'e'])
    editor = DataFrameEditor(None)
    editor.setup_and_check(df)
    header = editor.table_header.model()
    assert header.headerData(0, Qt.Horizontal,
                             Qt.DisplayRole) == "a"
    assert header.headerData(1, Qt.Horizontal,
                             Qt.DisplayRole) == "b"
    assert header.headerData(4, Qt.Horizontal,
                             Qt.DisplayRole) == "e"


def test_dataframe_multiindex():
    """Test to validate proper creation and handling of a multiindex."""
    arrays = [numpy.array(['bar', 'bar', 'baz', 'baz',
                           'foo', 'foo', 'qux', 'qux']),
              numpy.array(['one', 'two', 'one', 'two',
                           'one', 'two', 'one', 'two'])]
    tuples = list(zip(*arrays))
    index = MultiIndex.from_tuples(tuples, names=['first', 'second'])
    df = DataFrame(numpy.random.randn(6, 6), index=index[:6],
                   columns=index[:6])
    editor = DataFrameEditor(None)
    editor.setup_and_check(df)
    header = editor.table_header.model()
    assert header.headerData(0, Qt.Horizontal,
                             Qt.DisplayRole) == 0
    assert data_header(header, 0, 0) == 'bar'
    assert data_header(header, 1, 0) == 'one'
    assert data_header(header, 0, 1) == 'bar'
    assert data_header(header, 1, 1) == 'two'
    assert data_header(header, 0, 2) == 'baz'
    assert data_header(header, 1, 2) == 'one'
    assert data_header(header, 0, 3) == 'baz'
    assert data_header(header, 1, 3) == 'two'
    assert data_header(header, 0, 4) == 'foo'
    assert data_header(header, 1, 4) == 'one'
    assert data_header(header, 0, 5) == 'foo'
    assert data_header(header, 1, 5) == 'two'


def test_header_bom():
    """Test for BOM data in the headers."""
    df = read_csv(os.path.join(FILES_PATH, 'issue_2514.csv'))
    editor = DataFrameEditor(None)
    editor.setup_and_check(df)
    header = editor.table_header.model()
    assert header.headerData(0, Qt.Horizontal,
                             Qt.DisplayRole) == "Date (MMM-YY)"


@pytest.mark.skipif(is_module_installed('pandas', '<0.19'),
                    reason="It doesn't work for Pandas 0.19-")
def test_header_encoding():
    """Test for header encoding handling."""
    df = read_csv(os.path.join(FILES_PATH, 'issue_3896.csv'))
    editor = DataFrameEditor(None)
    editor.setup_and_check(df)
    header = editor.table_header.model()
    assert header.headerData(0, Qt.Horizontal,
                             Qt.DisplayRole) == "Unnamed: 0"
    assert "Unieke_Idcode" in header.headerData(1, Qt.Horizontal,
                                                Qt.DisplayRole)
    assert header.headerData(2, Qt.Horizontal,
                             Qt.DisplayRole) == "a"
    assert header.headerData(3, Qt.Horizontal,
                             Qt.DisplayRole) == "b"
    assert header.headerData(4, Qt.Horizontal,
                             Qt.DisplayRole) == "c"
    assert header.headerData(5, Qt.Horizontal,
                             Qt.DisplayRole) == "d"


def test_dataframemodel_basic():
    df = DataFrame({'colA': [1, 3], 'colB': ['c', 'a']})
    dfm = DataFrameModel(df)
    assert dfm.rowCount() == 2
    assert dfm.columnCount() == 2
    assert data(dfm, 0, 0) == '1'
    assert data(dfm, 0, 1) == 'c'
    assert data(dfm, 1, 0) == '3'
    assert data(dfm, 1, 1) == 'a'

def test_dataframemodel_sort():
    """Validate the data in the model."""
    df = DataFrame({'colA': [1, 3], 'colB': ['c', 'a']})
    dfm = DataFrameModel(df)
    dfm.sort(1)
    assert data(dfm, 0, 0) == '3'
    assert data(dfm, 1, 0) == '1'
    assert data(dfm, 0, 1) == 'a'
    assert data(dfm, 1, 1) == 'c'

def test_dataframemodel_sort_is_stable():   # cf. issue 3010
    """Validate the sort function."""
    df = DataFrame([[2,14], [2,13], [2,16], [1,3], [2,9], [1,15], [1,17],
                    [2,2], [2,10], [1,6], [2,5], [2,8], [1,11], [1,1],
                    [1,12], [1,4], [2,7]])
    dfm = DataFrameModel(df)
    dfm.sort(1)
    dfm.sort(0)
    col2 = [data(dfm, i, 1) for i in range(len(df))]
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
    assert colorclose(bgcolor(dfm, 0, 0), (h0 + dh,         s, v, a))
    assert colorclose(bgcolor(dfm, 1, 0), (h0 + 1 / 2 * dh, s, v, a))
    assert colorclose(bgcolor(dfm, 2, 0), (h0,              s, v, a))
    assert colorclose(bgcolor(dfm, 0, 1), (h0 + dh,         s, v, a))
    assert colorclose(bgcolor(dfm, 1, 1), (h0 + 2 / 3 * dh, s, v, a))
    assert colorclose(bgcolor(dfm, 2, 1), (h0,              s, v, a))

def test_dataframemodel_get_bgcolor_with_numbers_using_global_max():
    df = DataFrame([[0, 10], [1, 20], [2, 40]])
    dfm = DataFrameModel(df)
    dfm.colum_avg(0)
    h0 = dataframeeditor.BACKGROUND_NUMBER_MINHUE
    dh = dataframeeditor.BACKGROUND_NUMBER_HUERANGE
    s = dataframeeditor.BACKGROUND_NUMBER_SATURATION
    v = dataframeeditor.BACKGROUND_NUMBER_VALUE
    a = dataframeeditor.BACKGROUND_NUMBER_ALPHA
    assert colorclose(bgcolor(dfm, 0, 0), (h0 + dh,           s, v, a))
    assert colorclose(bgcolor(dfm, 1, 0), (h0 + 39 / 40 * dh, s, v, a))
    assert colorclose(bgcolor(dfm, 2, 0), (h0 + 38 / 40 * dh, s, v, a))
    assert colorclose(bgcolor(dfm, 0, 1), (h0 + 30 / 40 * dh, s, v, a))
    assert colorclose(bgcolor(dfm, 1, 1), (h0 + 20 / 40 * dh, s, v, a))
    assert colorclose(bgcolor(dfm, 2, 1), (h0,                s, v, a))

def test_dataframemodel_get_bgcolor_with_string():
    """Validate the color of the cell when a string is the data."""
    df = DataFrame([['xxx']])
    dfm = DataFrameModel(df)
    h, s, v, dummy = QColor(dataframeeditor.BACKGROUND_NONNUMBER_COLOR).getHsvF()
    a = dataframeeditor.BACKGROUND_STRING_ALPHA
    assert colorclose(bgcolor(dfm, 0, 0), (h, s, v, a))

def test_dataframemodel_get_bgcolor_with_object():
    df = DataFrame([[None]])
    dfm = DataFrameModel(df)
    h, s, v, dummy = QColor(dataframeeditor.BACKGROUND_NONNUMBER_COLOR).getHsvF()
    a = dataframeeditor.BACKGROUND_MISC_ALPHA
    assert colorclose(bgcolor(dfm, 0, 0), (h, s, v, a))


def test_dataframemodel_get_bgcolor_with_missings():
    """
    Test that df bg colors are correct for missing values of various types.

    The types `bool`, `object`, `datetime`, and `timedelta` are omitted,
    because missings have no different background there yet.
    """
    df = DataFrame({'int': [1, None], 'float': [.1, None],
                    'complex': [1j, None], 'string': ['a', None]})
    df['category'] = df['string'].astype('category')
    dfm = DataFrameModel(df)
    h, s, v, __ = QColor(dataframeeditor.BACKGROUND_NONNUMBER_COLOR).getHsvF()
    alpha = dataframeeditor.BACKGROUND_MISC_ALPHA
    for idx, column in enumerate(df.columns):
        assert not colorclose(bgcolor(dfm, 0, idx), (h, s, v, alpha)), \
            'Wrong bg color for value of type ' + column
        assert colorclose(bgcolor(dfm, 1, idx), (h, s, v, alpha)), \
            'Wrong bg color for missing of type ' + column


def test_dataframemodel_with_format_percent_d_and_nan():
    """
    Test DataFrameModel with format `%d` and dataframe containing NaN

    Regression test for issue #4139.
    """
    np_array = numpy.zeros(2)
    np_array[1] = numpy.nan
    dataframe = DataFrame(np_array)
    dfm = DataFrameModel(dataframe, format='%d')
    assert data(dfm, 0, 0) == '0'
    assert data(dfm, 1, 0) == 'nan'

def test_change_format_emits_signal(qtbot, monkeypatch):
    mockQInputDialog = Mock()
    mockQInputDialog.getText = lambda parent, title, label, mode, text: ('%10.3e', True)
    monkeypatch.setattr('spyder.plugins.variableexplorer.widgets.dataframeeditor.QInputDialog', mockQInputDialog)
    df = DataFrame([[0]])
    editor = DataFrameEditor(None)
    editor.setup_and_check(df)
    with qtbot.waitSignal(editor.sig_option_changed) as blocker:
        editor.change_format()
    assert blocker.args == ['dataframe_format', '%10.3e']

def test_change_format_with_format_not_starting_with_percent(qtbot, monkeypatch):
    mockQInputDialog = Mock()
    mockQInputDialog.getText = lambda parent, title, label, mode, text: ('xxx%f', True)
    monkeypatch.setattr('spyder.plugins.variableexplorer.widgets.dataframeeditor'
                        '.QInputDialog', mockQInputDialog)
    monkeypatch.setattr('spyder.plugins.variableexplorer.widgets.dataframeeditor'
                        '.QMessageBox.critical', Mock())
    df = DataFrame([[0]])
    editor = DataFrameEditor(None)
    editor.setup_and_check(df)
    with qtbot.assertNotEmitted(editor.sig_option_changed):
        editor.change_format()


def test_dataframeeditor_with_various_indexes():
    for rng_name, rng in generate_pandas_indexes().items():
        editor = DataFrameEditor(None)
        editor.setup_and_check(rng)
        dfm = editor.dataModel
        assert dfm.rowCount() == 20
        assert dfm.columnCount() == 1
        header = editor.table_header.model()
        assert header.headerData(0, Qt.Horizontal,
                                 Qt.DisplayRole) == "0"

        if rng_name == "Index":
            assert data(dfm, 0, 0) == 'A'
            assert data(dfm, 1, 0) == 'B'
            assert data(dfm, 2, 0) == 'C'
            assert data(dfm, 19, 0) == 'T'
        elif rng_name == "RangeIndex":
            assert data(dfm, 0, 0) == '0'
            assert data(dfm, 1, 0) == '1'
            assert data(dfm, 2, 0) == '2'
            assert data(dfm, 19, 0) == '19'
        elif rng_name == "Float64Index":
            assert data(dfm, 0, 0) == '0'
            assert data(dfm, 1, 0) == '0.1'
            assert data(dfm, 2, 0) == '0.2'
            assert data(dfm, 19, 0) == '1.9'
        elif rng_name == "DatetimeIndex":
            assert data(dfm, 0, 0) == '2017-01-01 00:00:00'
            assert data(dfm, 1, 0) == '2017-01-02 00:00:00'
            assert data(dfm, 2, 0) == '2017-01-03 00:00:00'
            assert data(dfm, 19, 0) == '2017-01-20 00:00:00'
        elif rng_name == "MultiIndex":
            assert data(dfm, 0, 0) == "('A', 'foo')"
            assert data(dfm, 1, 0) == "('A', 'bar')"
            assert data(dfm, 2, 0) == "('B', 'foo')"
            assert data(dfm, 19, 0) == "('J', 'bar')"
        elif rng_name == "CategoricalIndex":
            assert data(dfm, 0, 0) == 'a'
            assert data(dfm, 1, 0) == 'b'
            assert data(dfm, 2, 0) == 'c'
            assert data(dfm, 19, 0) == 'b'

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
    editor.dataModel.sort(0)
    assert [data(dfm, row, 0) for row in range(len(df))] == ['1', '3', '2']
    assert [data(dfm, row, 1) for row in range(len(df))] == ['4', '6', '5']
    editor.dataModel.sort(1)
    assert [data(dfm, row, 0) for row in range(len(df))] == ['1', '2', '3']
    assert [data(dfm, row, 1) for row in range(len(df))] == ['4', '5', '6']


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
    editor.dataModel.sort(0)
    assert data(dfm, 0, 0) == 'int64'
    assert data(dfm, 1, 0) == 'category'


def test_dataframemodel_set_data_overflow(monkeypatch):
    """
    Test that entry of an overflowing integer is caught and handled properly.

    Unit regression test for issue #6114 .
    """
    MockQMessageBox = Mock()
    attr_to_patch = ('spyder.plugins.variableexplorer.widgets' +
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
        index = model.createIndex(2, 0)
        assert not model.setData(index, str(int(2 ** bit_exponent)))
        MockQMessageBox.critical.assert_called_with(ANY, "Error", ANY)
        assert MockQMessageBox.critical.call_count == idx
        try:
            assert numpy.sum(test_df[0].values ==
                             model.df.values) == len(test_df)
        except AttributeError:
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
    attr_to_patch = ('spyder.plugins.variableexplorer.widgets' +
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
        try:
            assert numpy.sum(expected_df[0].values ==
                             dialog.get_value().values) == len(expected_df)
        except AttributeError:
            assert numpy.sum(
                    expected_df[0].as_matrix() ==
                    dialog.get_value().as_matrix()) == len(expected_df)


def test_dataframemodel_set_data_complex(monkeypatch):
    """
    Test that editing complex dtypes is handled gracefully in df editor.

    Unit regression test for issue #6115 .
    """
    MockQMessageBox = Mock()
    attr_to_patch = ('spyder.plugins.variableexplorer.widgets' +
                     '.dataframeeditor.QMessageBox')
    monkeypatch.setattr(attr_to_patch, MockQMessageBox)

    test_params = [(1, numpy.complex128), (2, numpy.complex64), (3, complex)]

    for count, complex_type in test_params:
        test_df = DataFrame(numpy.arange(10, 15), dtype=complex_type)
        model = DataFrameModel(test_df.copy())
        index = model.createIndex(2, 0)
        assert not model.setData(index, '42')
        MockQMessageBox.critical.assert_called_with(ANY, "Error", ANY)
        assert MockQMessageBox.critical.call_count == count
        try:
            assert numpy.sum(test_df[0].values ==
                             model.df.values) == len(test_df)
        except AttributeError:
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
    attr_to_patch = ('spyder.plugins.variableexplorer.widgets' +
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
        try:
            assert numpy.sum(test_df[0].values ==
                             dialog.get_value().values) == len(test_df)
        except AttributeError:
            assert numpy.sum(test_df[0].as_matrix() ==
                             dialog.get_value().as_matrix()) == len(test_df)


def test_dataframemodel_set_data_bool(monkeypatch):
    """Test that bools are editible in df and false-y strs are detected."""
    MockQMessageBox = Mock()
    attr_to_patch = ('spyder.plugins.variableexplorer.widgets' +
                     '.dataframeeditor.QMessageBox')
    monkeypatch.setattr(attr_to_patch, MockQMessageBox)

    test_params = [numpy.bool_, numpy.bool, bool]
    test_strs = ['foo', 'false', 'f', '0', '0.', '0.0', '', ' ']
    expected_df = DataFrame([1, 0, 0, 0, 0, 0, 0, 0, 0], dtype=bool)

    for bool_type in test_params:
        test_df = DataFrame([0, 1, 1, 1, 1, 1, 1, 1, 0], dtype=bool_type)
        model = DataFrameModel(test_df.copy())
        for idx, test_str in enumerate(test_strs):
            assert model.setData(model.createIndex(idx, 0), test_str)
            assert not MockQMessageBox.critical.called
        try:
            assert numpy.sum(expected_df[0].values ==
                             model.df.values[:, 0]) == len(expected_df)
        except AttributeError:
            assert numpy.sum(expected_df[0].as_matrix() ==
                             model.df.as_matrix()[:, 0]) == len(expected_df)


@flaky(max_runs=3)
@pytest.mark.no_xvfb
@pytest.mark.skipif(sys.platform == 'darwin', reason="It fails on macOS")
def test_dataframeeditor_edit_bool(qtbot, monkeypatch):
    """Test that bools are editible in df and false-y strs are detected."""
    MockQMessageBox = Mock()
    attr_to_patch = ('spyder.plugins.variableexplorer.widgets' +
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
        try:
            assert (numpy.sum(expected_df[0].values ==
                              dialog.get_value().values[:, 0]) ==
                    len(expected_df))
        except AttributeError:
            assert (numpy.sum(expected_df[0].as_matrix() ==
                              dialog.get_value().as_matrix()[:, 0]) ==
                    len(expected_df))


def test_non_ascii_index():
    """
    Test that there are no errors when displaying a dataframe with
    a non-ascii index and header.
    """
    df = read_csv(os.path.join(FILES_PATH, 'issue_5833.csv'), index_col=0)
    editor = DataFrameEditor(None)
    editor.setup_and_check(df)

    index = editor.table_index.model()
    header = editor.table_header.model()
    dfm = editor.model()

    assert header.headerData(0, Qt.Horizontal,
                             Qt.DisplayRole) == "кодирование"
    assert data_index(index, 0, 0) == 'пример'
    assert data(dfm, 0, 0) == 'файла'


def test_no_convert_strings_to_unicode():
    """
    Test that we don't apply any conversion to strings in headers,
    indexes or data.
    """
    df = read_csv(os.path.join(FILES_PATH, 'issue_5833.csv'), index_col=0,
                  encoding='koi8_r')
    editor = DataFrameEditor(None)
    editor.setup_and_check(df)

    index = editor.table_index.model()
    header = editor.table_header.model()
    dfm = editor.model()

    assert header.headerData(0, Qt.Horizontal,
                             Qt.DisplayRole) != u"кодирование"
    assert data_index(index, 0, 0) != u'пример'
    assert data(dfm, 0, 0) != u'файла'


if __name__ == "__main__":
    pytest.main()
