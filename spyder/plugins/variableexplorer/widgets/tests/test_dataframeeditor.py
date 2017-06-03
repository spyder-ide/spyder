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
from pandas import DataFrame, date_range, read_csv
from qtpy.QtGui import QColor
from qtpy.QtCore import Qt
import numpy
import pytest

# Local imports
from spyder.utils.programs import is_module_installed
from spyder.plugins.variableexplorer.widgets import dataframeeditor
from spyder.plugins.variableexplorer.widgets.viewers.dataframe import (
    DataFrameEditor, DataFrameModel)
from spyder.py3compat import PY2

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

# --- Tests
# -----------------------------------------------------------------------------

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

    Regression test for issue 4139.
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
    monkeypatch.setattr('spyder.plugins.variableexplorer.widgets.viewers.dataframe.QInputDialog', mockQInputDialog)
    df = DataFrame([[0]])
    editor = DataFrameEditor(None)
    editor.setup_and_check(df)
    with qtbot.waitSignal(editor.sig_option_changed) as blocker:
        editor.change_format()
    assert blocker.args == ['dataframe_format', '%10.3e']

def test_change_format_with_format_not_starting_with_percent(qtbot, monkeypatch):
    mockQInputDialog = Mock()
    mockQInputDialog.getText = lambda parent, title, label, mode, text: ('xxx%f', True)
    monkeypatch.setattr('spyder.plugins.variableexplorer.widgets.viewers.dataframe'
                        '.QInputDialog', mockQInputDialog)
    monkeypatch.setattr('spyder.plugins.variableexplorer.widgets.viewers.dataframe'
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


if __name__ == "__main__":
    pytest.main()
