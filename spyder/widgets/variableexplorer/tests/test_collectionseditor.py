# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License

"""
Tests for collectionseditor.py
"""


# Third party imports
import pandas
import pytest

# Local imports
from spyder.widgets.variableexplorer.collectionseditor import CollectionsModel

# Helper functions
def data(cm, i, j):
    return cm.data(cm.createIndex(i, j))

# --- Tests
# -----------------------------------------------------------------------------

def test_collectionsmodel_with_two_ints():
    coll = {'x': 1, 'y': 2}
    cm = CollectionsModel(None, coll)
    assert cm.rowCount() == 2
    assert cm.columnCount() == 4
    # dict is unordered, so first row might be x or y
    assert data(cm, 0, 0) in {'x', 'y'}
    if data(cm, 0, 0) == 'x':
        row_with_x = 0
        row_with_y = 1
    else:
        row_with_x = 1
        row_with_y = 0
    assert data(cm, row_with_x, 1) == 'int'
    assert data(cm, row_with_x, 2) == '1'
    assert data(cm, row_with_x, 3) == '1'
    assert data(cm, row_with_y, 0) == 'y'
    assert data(cm, row_with_y, 1) == 'int'
    assert data(cm, row_with_y, 2) == '1'
    assert data(cm, row_with_y, 3) == '2'

def test_collectionsmodel_with_datetimeindex():
    # Regression test for issue #3380
    rng = pandas.date_range('10/1/2016', periods=25, freq='bq')
    coll = {'rng': rng}
    cm = CollectionsModel(None, coll)
    assert data(cm, 0, 0) == 'rng'
    assert data(cm, 0, 3) == rng.summary()


if __name__ == "__main__":
    pytest.main()
