# -*- coding: utf-8 -*-
#
# Copyright © 2009- The Spyder Development Team
# Licensed under the terms of the MIT License

"""
Tests for dataframeeditor.py
"""

# Third party imports
from pandas import DataFrame, date_range
import pytest

# Local imports
from spyderlib.widgets.variableexplorer.dataframeeditor import DataFrameModel


# --- Tests
# -----------------------------------------------------------------------------
def test_dataframemodel_basic():
    df = DataFrame({'colA': [1, 3], 'colB': ['c', 'a']})
    dfm = DataFrameModel(df)
    assert dfm.rowCount() == 2
    assert dfm.columnCount() == 3
    assert dfm.data(dfm.createIndex(0, 0)) == '0'
    assert dfm.data(dfm.createIndex(0, 1)) == '1'
    assert dfm.data(dfm.createIndex(0, 2)) == 'c'
    assert dfm.data(dfm.createIndex(1, 0)) == '1'
    assert dfm.data(dfm.createIndex(1, 1)) == '3'
    assert dfm.data(dfm.createIndex(1, 2)) == 'a'
    
def test_dataframemodel_sort():
    df = DataFrame({'colA': [1, 3], 'colB': ['c', 'a']})
    dfm = DataFrameModel(df)
    dfm.sort(2)
    assert dfm.data(dfm.createIndex(0, 0)) == '1'
    assert dfm.data(dfm.createIndex(0, 1)) == '3'
    assert dfm.data(dfm.createIndex(0, 2)) == 'a'
    assert dfm.data(dfm.createIndex(1, 0)) == '0'
    assert dfm.data(dfm.createIndex(1, 1)) == '1'
    assert dfm.data(dfm.createIndex(1, 2)) == 'c'

def test_dataframemodel_sort_is_stable():   # cf. issue 3010
    df = DataFrame([[2,14], [2,13], [2,16], [1,3], [2,9], [1,15], [1,17],
                    [2,2], [2,10], [1,6], [2,5], [2,8], [1,11], [1,1],
                    [1,12], [1,4], [2,7]])
    dfm = DataFrameModel(df)
    dfm.sort(2)
    dfm.sort(1)
    col2 = [dfm.data(dfm.createIndex(i, 2)) for i in range(len(df))]
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


if __name__ == "__main__":
    pytest.main()
