# -*- coding: utf-8 -*-
#
# Copyright © 2009- The Spyder Development Team
# Licensed under the terms of the MIT License

"""
Tests for dataframeeditor.py
"""

# Third party imports
from pandas import DataFrame
import pytest

# Local imports
from spyder.widgets.variableexplorer.dataframeeditor import DataFrameModel


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


if __name__ == "__main__":
    pytest.main()

