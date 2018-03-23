# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright © Spyder Project Contributors
#
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)
# ----------------------------------------------------------------------------

"""
Tests for the Variable Explorer Collections Editor.
"""

# Standard library imports
import os  # Example module for testing display inside CollecitonsEditor
from os import path
import copy
import datetime
from xml.dom.minidom import parseString
try:
    from unittest.mock import Mock
except ImportError:
    from mock import Mock  # Python 2

# Third party imports
import numpy
import pandas
import pytest
from flaky import flaky
from qtpy.QtCore import Qt
from qtpy.QtWidgets import QWidget

# Local imports
from spyder.widgets.variableexplorer.collectionseditor import (
    CollectionsEditorTableView, CollectionsModel, CollectionsEditor,
    LARGE_NROWS, ROWS_TO_LOAD)
from spyder.widgets.variableexplorer.tests.test_dataframeeditor import \
    generate_pandas_indexes

# =============================================================================
# Constants
# =============================================================================
# Full path to this file's parent directory for loading data
LOCATION = path.realpath(os.path.join(os.getcwd(), os.path.dirname(__file__)))


# =============================================================================
# Utility functions
# =============================================================================
def data(cm, i, j):
    return cm.data(cm.createIndex(i, j))


def data_table(cm, n_rows, n_cols):
    return [[data(cm, i, j) for i in range(n_rows)] for j in range(n_cols)]


# =============================================================================
# Pytest Fixtures
# =============================================================================
@pytest.fixture
def nonsettable_objects_data():
    """Rturn Python objects with immutable attribs to test CollectionEditor."""
    test_objs = [pandas.Period("2018-03"), pandas.Categorical([1, 2, 42])]
    expected_objs = [pandas.Period("2018-03"), pandas.Categorical([1, 2, 42])]
    keys_test = [["_typ", "day", "dayofyear", "hour"],
                 ["_typ", "nbytes", "ndim"]]
    return zip(test_objs, expected_objs, keys_test)


# =============================================================================
# Tests
# ============================================================================
def test_create_dataframeeditor_with_correct_format(qtbot, monkeypatch):
    MockDataFrameEditor = Mock()
    mockDataFrameEditor_instance = MockDataFrameEditor()
    monkeypatch.setattr('spyder.widgets.variableexplorer.collectionseditor.DataFrameEditor',
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
        monkeypatch.setattr('spyder.widgets.variableexplorer.collectionseditor.DataFrameEditor',
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
    """
    Test that mutable objs/vals are editable in VarExp; immutable ones aren't.

    Regression test for issue #5991 .
    """
    MockQLineEdit = Mock()
    attr_to_patch_qlineedit = ('spyder.widgets.variableexplorer.' +
                               'collectionseditor.QLineEdit')
    monkeypatch.setattr(attr_to_patch_qlineedit, MockQLineEdit)

    MockTextEditor = Mock()
    attr_to_patch_textedit = ('spyder.widgets.variableexplorer.' +
                              'collectionseditor.TextEditor')
    monkeypatch.setattr(attr_to_patch_textedit, MockTextEditor)

    MockQDateTimeEdit = Mock()
    attr_to_patch_qdatetimeedit = ('spyder.widgets.variableexplorer.' +
                                   'collectionseditor.QDateTimeEdit')
    monkeypatch.setattr(attr_to_patch_qdatetimeedit, MockQDateTimeEdit)

    MockCollectionsEditor = Mock()
    mockCollectionsEditor_instance = MockCollectionsEditor()
    attr_to_patch_coledit = ('spyder.widgets.variableexplorer.' +
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
    assert not MockTextEditor.call_args[1]["readonly"]

    # Datetime inside list
    editor_list_datetime = editor_list.delegate.createEditor(
        None, None, editor_list.model.createIndex(2, 3))
    assert editor_list_datetime is not None
    assert MockQDateTimeEdit.call_count == 1

    # List inside list
    editor_list.delegate.createEditor(None, None,
                                      editor_list.model.createIndex(3, 3))
    assert mockCollectionsEditor_instance.show.call_count == 1
    assert not mockCollectionsEditor_instance.setup.call_args[1]["readonly"]

    # Tuple inside list
    editor_list.delegate.createEditor(None, None,
                                      editor_list.model.createIndex(4, 3))
    assert mockCollectionsEditor_instance.show.call_count == 2
    assert mockCollectionsEditor_instance.setup.call_args[1]["readonly"]

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
    assert MockTextEditor.call_args[1]["readonly"]

    # Datetime inside tuple
    editor_tup_datetime = editor_tup.delegate.createEditor(
        None, None, editor_tup.model.createIndex(2, 3))
    assert editor_tup_datetime is None
    assert MockQDateTimeEdit.call_count == 1

    # List inside tuple
    editor_tup.delegate.createEditor(None, None,
                                     editor_tup.model.createIndex(3, 3))
    assert mockCollectionsEditor_instance.show.call_count == 3
    assert mockCollectionsEditor_instance.setup.call_args[1]["readonly"]

    # Tuple inside tuple
    editor_tup.delegate.createEditor(None, None,
                                     editor_tup.model.createIndex(4, 3))
    assert mockCollectionsEditor_instance.show.call_count == 4
    assert mockCollectionsEditor_instance.setup.call_args[1]["readonly"]


@flaky(max_runs=3)
def test_view_module_in_coledit():
    """
    Test that modules don't produce an error when opening in Variable Explorer.

    Also check that they are set as readonly. Regression test for issue #6080 .
    """
    editor = CollectionsEditor()
    editor.setup(os, "module_test", readonly=False)
    assert editor.widget.editor.readonly

def test_notimplementederror_multiindex():
    """
    Test that the NotImplementedError when scrolling a MultiIndex is handled.

    Regression test for issue #6284 .
    """
    time_deltas = [pandas.Timedelta(minutes=minute)
                   for minute in range(5, 35, 5)]
    time_delta_multiindex = pandas.MultiIndex.from_product([[0, 1, 2, 3, 4],
                                                            time_deltas])
    col_model = CollectionsModel(None, time_delta_multiindex)
    assert col_model.rowCount() == col_model.rows_loaded == ROWS_TO_LOAD
    assert col_model.columnCount() == 4
    col_model.fetchMore()
    assert col_model.rowCount() == 2 * ROWS_TO_LOAD
    for _ in range(3):
        col_model.fetchMore()
    assert col_model.rowCount() == 5 * ROWS_TO_LOAD


def test_editor_parent_set(monkeypatch):
    """
    Test that editors have their parent set so they close with Spyder.

    Regression test for issue #5696 .
    """
    # Mocking and setup
    test_parent = QWidget()

    MockCollectionsEditor = Mock()
    attr_to_patch_coledit = ('spyder.widgets.variableexplorer.' +
                             'collectionseditor.CollectionsEditor')
    monkeypatch.setattr(attr_to_patch_coledit, MockCollectionsEditor)

    MockArrayEditor = Mock()
    attr_to_patch_arredit = ('spyder.widgets.variableexplorer.' +
                             'collectionseditor.ArrayEditor')
    monkeypatch.setattr(attr_to_patch_arredit, MockArrayEditor)

    MockDataFrameEditor = Mock()
    attr_to_patch_dfedit = ('spyder.widgets.variableexplorer.' +
                            'collectionseditor.DataFrameEditor')
    monkeypatch.setattr(attr_to_patch_dfedit, MockDataFrameEditor)

    MockTextEditor = Mock()
    attr_to_patch_textedit = ('spyder.widgets.variableexplorer.' +
                              'collectionseditor.TextEditor')
    monkeypatch.setattr(attr_to_patch_textedit, MockTextEditor)

    editor_data = [[0, 1, 2, 3, 4],
                   numpy.array([1.0, 42.0, 1337.0]),
                   pandas.DataFrame([[1, 2, 3], [20, 30, 40]]),
                   "012345678901234567890123456789012345678901234567890123456",
                   os]
    col_editor = CollectionsEditorTableView(test_parent, editor_data)
    assert col_editor.parent() is test_parent

    for idx, mock_class in enumerate([MockCollectionsEditor,
                                      MockArrayEditor,
                                      MockDataFrameEditor,
                                      MockTextEditor,
                                      MockCollectionsEditor]):
        col_editor.delegate.createEditor(col_editor.parent(), None,
                                         col_editor.model.createIndex(idx, 3))
        assert mock_class.call_count == 1 + (idx // 3)
        assert mock_class.call_args[1]["parent"] is test_parent


def test_xml_dom_element_view():
    """
    Test that XML DOM ``Element``s are able to be viewied in CollectionsEditor.

    Regression test for issue #5642 .
    """
    xml_path = path.join(LOCATION, 'dom_element_test.xml')
    with open(xml_path) as xml_file:
        xml_data = xml_file.read()

    xml_content = parseString(xml_data)
    xml_element = xml_content.getElementsByTagName("note")[0]

    col_editor = CollectionsEditor(None)
    col_editor.setup(xml_element)
    col_editor.show()
    assert col_editor.get_value()
    col_editor.accept()


def test_pandas_dateoffset_view():
    """
    Test that pandas ``DateOffset`` objs can be viewied in CollectionsEditor.

    Regression test for issue #6729 .
    """
    test_dateoffset = pandas.DateOffset()
    col_editor = CollectionsEditor(None)
    col_editor.setup(test_dateoffset)
    col_editor.show()
    assert col_editor.get_value()
    col_editor.accept()


def test_set_nonsettable_objects(nonsettable_objects_data):
    """
    Test that errors trying to set attributes in ColEdit are handled properly.

    Unit regression test for issues #6727 and #6728 .
    """
    for test_obj, expected_obj, keys in nonsettable_objects_data:
        col_model = CollectionsModel(None, test_obj)
        indicies = [col_model.get_index_from_key(key) for key in keys]
        for idx in indicies:
            assert not col_model.set_value(idx, "2")
            # Due to numpy's deliberate breakage of __eq__ comparison
            assert all([key == "_typ" or
                        (getattr(col_model.get_data().__obj__, key)
                         == getattr(expected_obj, key)) for key in keys])


@flaky(max_runs=3)
@pytest.mark.no_xvfb
def test_edit_nonsettable_objects(qtbot, nonsettable_objects_data):
    """
    Test that errors trying to edit attributes in ColEdit are handled properly.

    Integration regression test for issues #6727 and #6728 .
    """
    for test_obj, expected_obj, keys in nonsettable_objects_data:
        col_editor = CollectionsEditor(None)
        col_editor.setup(test_obj)
        col_editor.show()
        qtbot.waitForWindowShown(col_editor)
        view = col_editor.widget.editor
        indicies = [view.model.get_index_from_key(key) for key in keys]

        for _ in range(3):
            qtbot.keyClick(view, Qt.Key_Right)
        last_row = -1
        rows_to_test = [index.row() for index in indicies]
        for row in rows_to_test:
            for _ in range(row - last_row - 1):
                qtbot.keyClick(view, Qt.Key_Down)
            qtbot.keyClick(view, Qt.Key_Space)
            qtbot.keyClick(view.focusWidget(), Qt.Key_Backspace)
            qtbot.keyClicks(view.focusWidget(), "2")
            qtbot.keyClick(view.focusWidget(), Qt.Key_Down)
            last_row = row

        qtbot.wait(100)
        # Due to numpy's deliberate breakage of __eq__ comparison
        assert all([key == "_typ" or (getattr(col_editor.get_value(), key)
                    == getattr(expected_obj, key)) for key in keys])

        col_editor.accept()
        qtbot.wait(200)
        # Same reason as above
        assert all([key == "_typ" or (getattr(col_editor.get_value(), key)
                    == getattr(expected_obj, key)) for key in keys])
        assert all([getattr(test_obj, key)
                    == getattr(expected_obj, key) for key in keys])


if __name__ == "__main__":
    pytest.main()
