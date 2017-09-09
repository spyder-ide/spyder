# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License

"""
Tests for dataframeeditor.py
"""

from __future__ import division

# Standard library imports
try:
    from unittest.mock import Mock
except ImportError:
    from mock import Mock # Python 2
import os

# Third party imports
from pandas import DataFrame, date_range, MultiIndex, read_csv
from qtpy.QtGui import QColor
from qtpy.QtCore import Qt
import numpy
import pytest

# Local imports
from spyder.utils.programs import is_module_installed
from spyder.widgets.variableexplorer import dataframeeditor
from spyder.widgets.variableexplorer.dataframeeditor import (
    DataFrameEditor, DataFrameModel)

FILES_PATH = os.path.dirname(os.path.realpath(__file__))

# Helper functions
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


# --- Tests
# -----------------------------------------------------------------------------


def test_dataframe_simpleindex():
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
    assert data_header(header, 0, 1) == 'foo'


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
    assert header.headerData(1, Qt.Horizontal,
                             Qt.DisplayRole) == "Unieke_Idcode"
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

def test_dataframemodel_with_format_percent_d_and_nan():
    """
    Test DataFrameModel with format `%d` and dataframe containing NaN

    Regression test for issue 4139.
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

def test_dataframeeditor_with_datetimeindex():
    rng = date_range('20150101', periods=3)
    editor = DataFrameEditor(None)
    editor.setup_and_check(rng)
    dfm = editor.dataModel
    assert dfm.rowCount() == 3
    assert dfm.columnCount() == 1
    assert data(dfm, 0, 0) == '2015-01-01 00:00:00'
    assert data(dfm, 1, 0) == '2015-01-02 00:00:00'
    assert data(dfm, 2, 0) == '2015-01-03 00:00:00'


if __name__ == "__main__":
    pytest.main()
