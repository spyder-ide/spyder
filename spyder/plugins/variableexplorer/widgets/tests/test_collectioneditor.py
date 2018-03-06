# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License

"""
Tests for collectionseditor.py
"""

# Standard library imports
import os  # Example module for testing display inside collecitoneditor
import copy
import datetime
try:
    from unittest.mock import Mock, ANY
except ImportError:
    from mock import Mock, ANY  # Python 2

# Third party imports
import pandas
import pytest
from flaky import flaky

# Local imports
from spyder.plugins.variableexplorer.widgets.collectionseditor import (
    CollectionsEditorTableView, CollectionsModel, CollectionsEditor,
    LARGE_NROWS, ROWS_TO_LOAD)
from spyder.plugins.variableexplorer.widgets.tests.test_dataframeeditor import \
    generate_pandas_indexes

# Helper functions
def data(cm, i, j):
    return cm.data(cm.createIndex(i, j))

def data_table(cm, n_rows, n_cols):
    return [[data(cm, i, j) for i in range(n_rows)] for j in range(n_cols)]

# --- Tests
# -----------------------------------------------------------------------------

def test_create_dataframeeditor_with_correct_format(qtbot, monkeypatch):
    MockDataFrameEditor = Mock()
    mockDataFrameEditor_instance = MockDataFrameEditor()
    monkeypatch.setattr('spyder.plugins.variableexplorer.widgets.collectionseditor.DataFrameEditor',
                        MockDataFrameEditor)
    df = pandas.DataFrame(['foo', 'bar'])
    editor = CollectionsEditorTableView(None, {'df': df})
    qtbot.addWidget(editor)
    editor.set_dataframe_format('%10d')
    editor.delegate.createEditor(None, None, editor.model.createIndex(0, 3))
    mockDataFrameEditor_instance.dataModel.set_format.assert_called_once_with('%10d')

def test_accept_sig_option_changed_from_dataframeeditor(qtbot, monkeypatch):
    df = pandas.DataFrame(['foo', 'bar'])
    editor = CollectionsEditorTableView(None, {'df': df})
    qtbot.addWidget(editor)
    editor.set_dataframe_format('%10d')
    assert editor.model.dataframe_format == '%10d'
    editor.delegate.createEditor(None, None, editor.model.createIndex(0, 3))
    dataframe_editor = next(iter(editor.delegate._editors.values()))['editor']
    qtbot.addWidget(dataframe_editor)
    dataframe_editor.sig_option_changed.emit('dataframe_format', '%5f')
    assert editor.model.dataframe_format == '%5f'

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

def test_collectionsmodel_with_index():
    # Regression test for issue #3380, modified for #3758
    for rng_name, rng in generate_pandas_indexes().items():
        coll = {'rng': rng}
        cm = CollectionsModel(None, coll)
        assert data(cm, 0, 0) == 'rng'
        assert data(cm, 0, 1) == rng_name
        assert data(cm, 0, 2) == '(20,)' or data(cm, 0, 2) == '(20L,)'
        assert data(cm, 0, 3) == rng.summary()

def test_shows_dataframeeditor_when_editing_index(qtbot, monkeypatch):
    for rng_name, rng in generate_pandas_indexes().items():
        MockDataFrameEditor = Mock()
        mockDataFrameEditor_instance = MockDataFrameEditor()
        monkeypatch.setattr('spyder.plugins.variableexplorer.widgets.collectionseditor.DataFrameEditor',
                            MockDataFrameEditor)
        coll = {'rng': rng}
        editor = CollectionsEditorTableView(None, coll)
        editor.delegate.createEditor(None, None,
                                     editor.model.createIndex(0, 3))
        mockDataFrameEditor_instance.show.assert_called_once_with()


def test_sort_collectionsmodel():
    coll = [1, 3, 2]
    cm = CollectionsModel(None, coll)
    assert cm.rowCount() == 3
    assert cm.columnCount() == 4
    cm.sort(0)  # sort by index
    assert data_table(cm, 3, 4) == [['0', '1', '2'],
                                    ['int', 'int', 'int'],
                                    ['1', '1', '1'],
                                    ['1', '3', '2']]
    cm.sort(3)  # sort by value
    assert data_table(cm, 3, 4) == [['0', '2', '1'],
                                    ['int', 'int', 'int'],
                                    ['1', '1', '1'],
                                    ['1', '2', '3']]
    coll = [[1, 2], 3]
    cm = CollectionsModel(None, coll)
    assert cm.rowCount() == 2
    assert cm.columnCount() == 4
    cm.sort(1)  # sort by type
    assert data_table(cm, 2, 4) == [['1', '0'],
                                    ['int', 'list'],
                                    ['1', '2'],
                                    ['3', '[1, 2]']]
    cm.sort(2)  # sort by size
    assert data_table(cm, 2, 4) == [['1', '0'],
                                    ['int', 'list'],
                                    ['1', '2'],
                                    ['3', '[1, 2]']]


def test_sort_collectionsmodel_with_many_rows():
    coll = list(range(2*LARGE_NROWS))
    cm = CollectionsModel(None, coll)
    assert cm.rowCount() == cm.rows_loaded == ROWS_TO_LOAD
    assert cm.columnCount() == 4
    cm.sort(1)  # This was causing an issue (#5232)
    cm.fetchMore()
    assert cm.rowCount() == 2 * ROWS_TO_LOAD
    for _ in range(3):
        cm.fetchMore()
    assert cm.rowCount() == len(coll)


def test_rename_and_duplicate_item_in_collection_editor():
    collections = {'list': ([1, 2, 3], False, True),
                   'tuple': ((1, 2, 3), False, False),
                   'dict': ({'a': 1, 'b': 2}, True, True)}
    for coll, rename_enabled, duplicate_enabled in collections.values():
        coll_copy = copy.copy(coll)
        editor = CollectionsEditorTableView(None, coll)
        assert editor.rename_action.isEnabled()
        assert editor.duplicate_action.isEnabled()
        editor.setCurrentIndex(editor.model.createIndex(0, 0))
        editor.refresh_menu()
        assert editor.rename_action.isEnabled() == rename_enabled
        assert editor.duplicate_action.isEnabled() == duplicate_enabled
        if isinstance(coll, list):
            editor.duplicate_item()
            assert editor.model.get_data() == coll_copy + [coll_copy[0]]


def test_edit_mutable_and_immutable_types(monkeypatch):
    """Check to ensure mutable types (lists, dicts) and individual values are
    editable, but not immutable ones (tuples) or anything inside of them,
    per #5991"""
    MockQLineEdit = Mock()
    attr_to_patch_qlineedit = ('spyder.plugins.variableexplorer.widgets.' +
                               'collectionseditor.QLineEdit')
    monkeypatch.setattr(attr_to_patch_qlineedit, MockQLineEdit)

    MockTextEditor = Mock()
    attr_to_patch_textedit = ('spyder.plugins.variableexplorer.widgets.' +
                              'collectionseditor.TextEditor')
    monkeypatch.setattr(attr_to_patch_textedit, MockTextEditor)

    MockQDateTimeEdit = Mock()
    attr_to_patch_qdatetimeedit = ('spyder.plugins.variableexplorer.widgets.' +
                                   'collectionseditor.QDateTimeEdit')
    monkeypatch.setattr(attr_to_patch_qdatetimeedit, MockQDateTimeEdit)

    MockCollectionsEditor = Mock()
    mockCollectionsEditor_instance = MockCollectionsEditor()
    attr_to_patch_coledit = ('spyder.plugins.variableexplorer.widgets.' +
                             'collectionseditor.CollectionsEditor')
    monkeypatch.setattr(attr_to_patch_coledit, MockCollectionsEditor)

    list_test = [1, "012345678901234567901234567890123456789012",
                 datetime.datetime(2017, 12, 24, 7, 9), [1, 2, 3], (2, "eggs")]
    tup_test = tuple(list_test)

    # Tests for mutable type (list) #
    editor_list = CollectionsEditorTableView(None, list_test)

    # Directly editable values inside list
    editor_list_value = editor_list.delegate.createEditor(
        None, None, editor_list.model.createIndex(0, 3))
    assert editor_list_value is not None
    assert MockQLineEdit.call_count == 1

    # Text Editor for long text inside list
    editor_list.delegate.createEditor(None, None,
                                      editor_list.model.createIndex(1, 3))
    assert MockTextEditor.call_count == 2
    MockTextEditor.assert_called_with(ANY, ANY, readonly=False)

    # Datetime inside list
    editor_list_datetime = editor_list.delegate.createEditor(
        None, None, editor_list.model.createIndex(2, 3))
    assert editor_list_datetime is not None
    assert MockQDateTimeEdit.call_count == 1

    # List inside list
    editor_list.delegate.createEditor(None, None,
                                      editor_list.model.createIndex(3, 3))
    assert mockCollectionsEditor_instance.show.call_count == 1
    mockCollectionsEditor_instance.setup.assert_called_with(ANY, ANY,
                                                            icon=ANY,
                                                            readonly=False)

    # Tuple inside list
    editor_list.delegate.createEditor(None, None,
                                      editor_list.model.createIndex(4, 3))
    assert mockCollectionsEditor_instance.show.call_count == 2
    mockCollectionsEditor_instance.setup.assert_called_with(ANY, ANY,
                                                            icon=ANY,
                                                            readonly=True)

    # Tests for immutable type (tuple) #
    editor_tup = CollectionsEditorTableView(None, tup_test)

    # Directly editable values inside tuple
    editor_tup_value = editor_tup.delegate.createEditor(
        None, None, editor_tup.model.createIndex(0, 3))
    assert editor_tup_value is None
    assert MockQLineEdit.call_count == 1

    # Text Editor for long text inside tuple
    editor_tup.delegate.createEditor(None, None,
                                     editor_tup.model.createIndex(1, 3))
    assert MockTextEditor.call_count == 4
    MockTextEditor.assert_called_with(ANY, ANY, readonly=True)

    # Datetime inside tuple
    editor_tup_datetime = editor_tup.delegate.createEditor(
        None, None, editor_tup.model.createIndex(2, 3))
    assert editor_tup_datetime is None
    assert MockQDateTimeEdit.call_count == 1

    # List inside tuple
    editor_tup.delegate.createEditor(None, None,
                                     editor_tup.model.createIndex(3, 3))
    assert mockCollectionsEditor_instance.show.call_count == 3
    mockCollectionsEditor_instance.setup.assert_called_with(ANY, ANY,
                                                            icon=ANY,
                                                            readonly=True)

    # Tuple inside tuple
    editor_tup.delegate.createEditor(None, None,
                                     editor_tup.model.createIndex(4, 3))
    assert mockCollectionsEditor_instance.show.call_count == 4
    mockCollectionsEditor_instance.setup.assert_called_with(ANY, ANY,
                                                            icon=ANY,
                                                            readonly=True)


@flaky(max_runs=3)
def test_view_module_in_coledit():
    """Check that modules don't produce an error when trying to open them in
    Variable Explorer, and are set as readonly. Regression test for #6080"""
    editor = CollectionsEditor()
    editor.setup(os, "module_test", readonly=False)
    assert editor.widget.editor.readonly

if __name__ == "__main__":
    pytest.main()
