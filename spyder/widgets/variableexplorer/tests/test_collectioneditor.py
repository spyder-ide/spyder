# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License

"""
Tests for collectionseditor.py
"""

# Standard library imports
try:
    from unittest.mock import Mock
except ImportError:
    from mock import Mock # Python 2

# Third party imports
import pandas
import pytest

# Local imports
from spyder.widgets.variableexplorer.collectionseditor import (
    CollectionsEditorTableView)

# --- Tests
# -----------------------------------------------------------------------------

def test_create_dataframeeditor_with_correct_format(qtbot, monkeypatch):
    MockDataFrameEditor = Mock()
    mockDataFrameEditor_instance = MockDataFrameEditor()
    monkeypatch.setattr('spyder.widgets.variableexplorer.collectionseditor.DataFrameEditor',
                        MockDataFrameEditor)
    df = pandas.DataFrame(['foo', 'bar'])
    editor = CollectionsEditorTableView(None, {'df': df})
    editor.set_dataframe_format('%10d')
    editor.delegate.createEditor(None, None, editor.model.createIndex(0, 3))
    mockDataFrameEditor_instance.dataModel.set_format.assert_called_once_with('%10d')


if __name__ == "__main__":
    pytest.main()
