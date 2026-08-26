# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
#

"""Tests for collectionsdelegate.py."""

# Third-party imports
import numpy as np
import pandas as pd
from spyder_kernels.utils.nsview import get_size

# Local imports
from spyder.plugins.variableexplorer.widgets.collectionsdelegate import (
    CollectionsDelegate,
)
from spyder.plugins.variableexplorer.widgets import collectionsdelegate


class FakeCell:
    def __init__(self, value):
        self.value = value

    def data(self):
        return self.value


class FakeQModelIndex:
    def __init__(self, obj):
        self.obj = obj

    def row(self):
        return 0

    def sibling(self, row, column):
        if column == 1:
            return FakeCell("DataFrame")
        elif column == 2:
            return FakeCell(str(get_size(self.obj)))


def test_show_warning_dataframe(monkeypatch):
    """Test warning for large DataFrames."""
    monkeypatch.setattr(collectionsdelegate, "LARGE_ARRAY", 10)

    df = pd.DataFrame(np.random.rand(2, 6))
    delegate = CollectionsDelegate()
    assert delegate.show_warning(FakeQModelIndex(df))
