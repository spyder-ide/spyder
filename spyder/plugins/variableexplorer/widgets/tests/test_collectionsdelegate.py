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


class MockEditor:
    def __init__(self):
        self.rejected = False

    def reject(self):
        self.rejected = True


def test_close_all_editors():
    """Test all tracked non-modal editors are closed."""
    delegate = CollectionsDelegate()

    editor_1 = MockEditor()
    editor_2 = MockEditor()
    delegate._editors = {
        id(editor_1): {"editor": editor_1},
        id(editor_2): {"editor": editor_2},
    }

    delegate.close_all_editors()

    assert editor_1.rejected
    assert editor_2.rejected
    assert not delegate._editors


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
