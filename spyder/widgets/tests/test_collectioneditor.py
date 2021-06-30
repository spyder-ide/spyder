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
from unittest.mock import Mock

# Third party imports
import numpy
import pandas
import pytest
from flaky import flaky
from qtpy.QtCore import Qt, QPoint
from qtpy.QtWidgets import QWidget, QDateEdit

# Local imports
from spyder.config.manager import CONF
from spyder.widgets.collectionseditor import (
    RemoteCollectionsEditorTableView, CollectionsEditorTableView,
    CollectionsModel, CollectionsEditor, LARGE_NROWS, ROWS_TO_LOAD, natsort)
from spyder.plugins.variableexplorer.widgets.namespacebrowser import (
    NamespacesBrowserFinder)
from spyder.plugins.variableexplorer.widgets.tests.test_dataframeeditor import \
    generate_pandas_indexes
from spyder.py3compat import PY2, to_text_string
from spyder_kernels.utils.nsview import get_size


# =============================================================================
# Constants
# =============================================================================
# Full path to this file's parent directory for loading data
LOCATION = path.realpath(os.path.join(os.getcwd(), os.path.dirname(__file__)))


# =============================================================================
# Utility functions and classes
# =============================================================================
def data(cm, i, j):
    return cm.data(cm.index(i, j))


def data_table(cm, n_rows, n_cols):
    return [[data(cm, i, j) for i in range(n_rows)] for j in range(n_cols)]


class MockParent(QWidget):

    def __init__(self):
        super(QWidget, self).__init__(None)
        self.proxy_model = None


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
def test_rename_variable(qtbot):
    """Test renaming of the correct variable."""
    variables = {'a': 1,
                 'b': 2,
                 'c': 3,
                 'd': '4',
                 'e': 5}
    editor = CollectionsEditorTableView(None, variables.copy())
    qtbot.addWidget(editor)
    editor.setCurrentIndex(editor.model.index(1, 0))

    editor.rename_item(new_name='b2')
    assert editor.model.rowCount() == 5
    assert data(editor.model, 0, 0) == 'a'
    assert data(editor.model, 1, 0) == 'b2'
    assert data(editor.model, 2, 0) == 'c'
    assert data(editor.model, 3, 0) == 'd'
    assert data(editor.model, 4, 0) == 'e'

    # Reset variables and try renaming one again
    new_variables = {'a': 1,
                     'b': 2,
                     'b2': 2,
                     'c': 3,
                     'd': '4',
                     'e': 5}
    editor.set_data(new_variables.copy())
    editor.adjust_columns()
    editor.setCurrentIndex(editor.model.index(1, 0))
    editor.rename_item(new_name='b3')
    assert editor.model.rowCount() == 6
    assert data(editor.model, 0, 0) == 'a'
    assert data(editor.model, 1, 0) == 'b2'
    assert data(editor.model, 2, 0) == 'b3'
    assert data(editor.model, 3, 0) == 'c'
    assert data(editor.model, 4, 0) == 'd'
    assert data(editor.model, 5, 0) == 'e'


def test_remove_variable(qtbot):
    """Test removing of the correct variable."""
    variables = {'a': 1,
                 'b': 2,
                 'c': 3,
                 'd': '4',
                 'e': 5}
    editor = CollectionsEditorTableView(None, variables.copy())
    qtbot.addWidget(editor)
    editor.setCurrentIndex(editor.model.index(1, 0))

    editor.remove_item(force=True)
    assert editor.model.rowCount() == 4
    assert data(editor.model, 0, 0) == 'a'
    assert data(editor.model, 1, 0) == 'c'
    assert data(editor.model, 2, 0) == 'd'
    assert data(editor.model, 3, 0) == 'e'

    # Reset variables and try removing one again
    editor.set_data(variables.copy())
    editor.adjust_columns()
    editor.setCurrentIndex(editor.model.index(1, 0))
    editor.remove_item(force=True)
    assert editor.model.rowCount() == 4
    assert data(editor.model, 0, 0) == 'a'
    assert data(editor.model, 1, 0) == 'c'
    assert data(editor.model, 2, 0) == 'd'
    assert data(editor.model, 3, 0) == 'e'


def test_remove_remote_variable(qtbot, monkeypatch):
    """Test the removing of the correct remote variable."""
    variables = {'a': {'type': 'int',
                       'size': 1,
                       'color': '#0000ff',
                       'view': '1'},
                 'b': {'type': 'int',
                       'size': 1,
                       'color': '#0000ff',
                       'view': '2'},
                 'c': {'type': 'int',
                       'size': 1,
                       'color': '#0000ff',
                       'view': '3'},
                 'd': {'type': 'str',
                       'size': 1, 'color': '#800000',
                       'view': '4'},
                 'e': {'type': 'int',
                       'size': 1,
                       'color': '#0000ff',
                       'view': '5'}}
    editor = RemoteCollectionsEditorTableView(None, variables.copy())
    qtbot.addWidget(editor)
    editor.setCurrentIndex(editor.model.index(1, 0))

    # Monkey patch remove variables
    def remove_values(ins, names):
        assert names == ['b']
        data = {'a': {'type': 'int',
                      'size': 1,
                      'color': '#0000ff',
                      'view': '1'},
                'c': {'type': 'int',
                      'size': 1,
                      'color': '#0000ff',
                      'view': '3'},
                'd': {'type': 'str',
                      'size': 1, 'color': '#800000',
                      'view': '4'},
                'e': {'type': 'int',
                      'size': 1,
                      'color': '#0000ff',
                      'view': '5'}}
        editor.set_data(data)
    monkeypatch.setattr(
        'spyder.widgets'
        '.collectionseditor.RemoteCollectionsEditorTableView.remove_values',
        remove_values)

    editor.remove_item(force=True)
    assert editor.model.rowCount() == 4
    assert data(editor.model, 0, 0) == 'a'
    assert data(editor.model, 1, 0) == 'c'
    assert data(editor.model, 2, 0) == 'd'
    assert data(editor.model, 3, 0) == 'e'

    # Reset variables and try removing one again
    editor.set_data(variables.copy())
    editor.adjust_columns()
    editor.setCurrentIndex(editor.model.index(1, 0))
    editor.remove_item(force=True)
    assert editor.model.rowCount() == 4
    assert data(editor.model, 0, 0) == 'a'
    assert data(editor.model, 1, 0) == 'c'
    assert data(editor.model, 2, 0) == 'd'
    assert data(editor.model, 3, 0) == 'e'


def test_filter_rows(qtbot):
    """Test rows filtering."""
    data = (
        {'dfa':
            {'type': 'DataFrame', 'size': (2, 1), 'color': '#00ff00',
             'view': 'Column names: 0'},
         'dfb':
            {'type': 'DataFrame', 'size': (2, 1), 'color': '#00ff00',
             'view': 'Column names: 0'}}
    )
    editor = RemoteCollectionsEditorTableView(None, data)
    editor.finder = NamespacesBrowserFinder(editor,
                                            editor.set_regex)
    qtbot.addWidget(editor)

    # Initially two rows
    assert editor.model.rowCount() == 2

    # Match two rows by name
    editor.finder.setText("df")
    assert editor.model.rowCount() == 2

    # Match two rows by type
    editor.finder.setText("DataFrame")
    assert editor.model.rowCount() == 2

    # Only one match
    editor.finder.setText("dfb")
    assert editor.model.rowCount() == 1

    # No match
    editor.finder.setText("dfbc")
    assert editor.model.rowCount() == 0


def test_create_dataframeeditor_with_correct_format(qtbot, monkeypatch):
    df = pandas.DataFrame(['foo', 'bar'])
    editor = CollectionsEditorTableView(None, {'df': df})
    qtbot.addWidget(editor)
    CONF.set('variable_explorer', 'dataframe_format', '10d')
    editor.delegate.createEditor(None, None, editor.model.index(0, 3))
    dataframe_editor = next(iter(editor.delegate._editors.values()))['editor']
    qtbot.addWidget(dataframe_editor)
    dataframe_editor.dataModel._format == '%10d'

def test_collectionsmodel_with_two_ints():
    coll = {'x': 1, 'y': 2}
    cm = CollectionsModel(MockParent(), coll)

    assert cm.rowCount() == 2
    assert cm.columnCount() == 4
    # dict is unordered, so first row might be x or y
    assert data(cm, 0, 0) in {'x',
                              'y'}
    if data(cm, 0, 0) == 'x':
        row_with_x = 0
        row_with_y = 1
    else:
        row_with_x = 1
        row_with_y = 0
    assert data(cm, row_with_x, 1) == 'int'
    assert data(cm, row_with_x, 2) == 1
    assert data(cm, row_with_x, 3) == '1'
    assert data(cm, row_with_y, 0) == 'y'
    assert data(cm, row_with_y, 1) == 'int'
    assert data(cm, row_with_y, 2) == 1
    assert data(cm, row_with_y, 3) == '2'

def test_collectionsmodel_with_index():
    # Regression test for spyder-ide/spyder#3380,
    # modified for spyder-ide/spyder#3758.
    for rng_name, rng in generate_pandas_indexes().items():
        coll = {'rng': rng}
        cm = CollectionsModel(MockParent(), coll)
        assert data(cm, 0, 0) == 'rng'
        assert data(cm, 0, 1) == rng_name
        assert data(cm, 0, 2) == '(20,)' or data(cm, 0, 2) == '(20L,)'
    try:
        assert data(cm, 0, 3) == rng._summary()
    except AttributeError:
        assert data(cm, 0, 3) == rng.summary()


def test_shows_dataframeeditor_when_editing_index(qtbot, monkeypatch):
    for rng_name, rng in generate_pandas_indexes().items():
        MockDataFrameEditor = Mock()
        mockDataFrameEditor_instance = MockDataFrameEditor()
        monkeypatch.setattr('spyder.plugins.variableexplorer.widgets.collectionsdelegate.DataFrameEditor',
                            MockDataFrameEditor)
        coll = {'rng': rng}
        editor = CollectionsEditorTableView(None, coll)
        editor.delegate.createEditor(None, None,
                                     editor.model.index(0, 3))
        mockDataFrameEditor_instance.show.assert_called_once_with()


def test_sort_numpy_numeric_collectionsmodel():
    var_list = [
        numpy.float64(1e16), numpy.float64(10), numpy.float64(1),
        numpy.float64(0.1), numpy.float64(1e-6),
        numpy.float64(0), numpy.float64(-1e-6), numpy.float64(-1),
        numpy.float64(-10), numpy.float64(-1e16)
        ]
    cm = CollectionsModel(MockParent(), var_list)
    assert cm.rowCount() == 10
    assert cm.columnCount() == 4
    cm.sort(0)  # sort by index
    assert data_table(cm, 10, 4) == [list(range(0, 10)),
                                     [u'float64']*10,
                                     [1]*10,
                                     ['1e+16', '10.0', '1.0', '0.1',
                                      '1e-06', '0.0', '-1e-06',
                                      '-1.0', '-10.0', '-1e+16']]
    cm.sort(3)  # sort by value
    assert data_table(cm, 10, 4) == [list(range(9, -1, -1)),
                                     [u'float64']*10,
                                     [1]*10,
                                     ['-1e+16', '-10.0', '-1.0',
                                      '-1e-06', '0.0', '1e-06',
                                      '0.1', '1.0', '10.0', '1e+16']]


def test_sort_float_collectionsmodel():
    var_list = [
        float(1e16), float(10), float(1), float(0.1), float(1e-6),
        float(0), float(-1e-6), float(-1), float(-10), float(-1e16)
        ]
    cm = CollectionsModel(MockParent(), var_list)
    assert cm.rowCount() == 10
    assert cm.columnCount() == 4
    cm.sort(0)  # sort by index
    assert data_table(cm, 10, 4) == [list(range(0, 10)),
                                     [u'float']*10,
                                     [1]*10,
                                     ['1e+16', '10.0', '1.0', '0.1',
                                      '1e-06', '0.0', '-1e-06',
                                      '-1.0', '-10.0', '-1e+16']]
    cm.sort(3)  # sort by value
    assert data_table(cm, 10, 4) == [list(range(9, -1, -1)),
                                     [u'float']*10,
                                     [1]*10,
                                     ['-1e+16', '-10.0', '-1.0',
                                      '-1e-06', '0.0', '1e-06',
                                      '0.1', '1.0', '10.0', '1e+16']]


@pytest.mark.skipif(os.name == 'nt' and PY2, reason='Fails on Win and py2')
def test_sort_collectionsmodel():
    var_list1 = [0, 1, 2]
    var_list2 = [3, 4, 5, 6]
    var_dataframe1 = pandas.DataFrame([[1, 2, 3], [20, 30, 40], [2, 2, 2]])
    var_dataframe2 = pandas.DataFrame([[1, 2, 3], [20, 30, 40]])
    var_series1 = pandas.Series(var_list1)
    var_series2 = pandas.Series(var_list2)

    coll = [1, 3, 2]
    cm = CollectionsModel(MockParent(), coll)
    assert cm.rowCount() == 3
    assert cm.columnCount() == 4
    cm.sort(0)  # sort by index
    assert data_table(cm, 3, 4) == [[0, 1, 2],
                                    ['int', 'int', 'int'],
                                    [1, 1, 1],
                                    ['1', '3', '2']]
    cm.sort(3)  # sort by value
    assert data_table(cm, 3, 4) == [[0, 2, 1],
                                    ['int', 'int', 'int'],
                                    [1, 1, 1],
                                    ['1', '2', '3']]

    coll = [1, var_list1, var_list2, var_dataframe1, var_dataframe2,
            var_series1, var_series2]
    cm = CollectionsModel(MockParent(), coll)
    assert cm.rowCount() == 7
    assert cm.columnCount() == 4

    cm.sort(1)  # sort by type
    assert data_table(cm, 7, 4) == [
        [3, 4, 5, 6, 0, 1, 2],
        ['DataFrame', 'DataFrame', 'Series', 'Series', 'int', 'list', 'list'],
        ['(3, 3)', '(2, 3)', '(3,)', '(4,)', 1, 3, 4],
        ['Column names: 0, 1, 2',
         'Column names: 0, 1, 2',
         'Series object of pandas.core.series module',
         'Series object of pandas.core.series module',
         '1',
         '[0, 1, 2]',
         '[3, 4, 5, 6]']]

    cm.sort(2)  # sort by size
    assert data_table(cm, 7, 4) == [
        [3, 4, 5, 6, 0, 1, 2],
        ['DataFrame', 'DataFrame', 'Series', 'Series', 'int', 'list', 'list'],
        ['(2, 3)', '(3,)', '(3, 3)', '(4,)', 1, 3, 4],
        ['Column names: 0, 1, 2',
         'Column names: 0, 1, 2',
         'Series object of pandas.core.series module',
         'Series object of pandas.core.series module',
         '1',
         '[0, 1, 2]',
         '[3, 4, 5, 6]']] or data_table(cm, 7, 4) == [
        [0, 1, 2, 4, 5, 3, 6],
        [u'int', u'list', u'list', u'DataFrame', u'Series', u'DataFrame',
         u'Series'],
        [1, 3, 4, u'(2, 3)', u'(3,)', u'(3, 3)', u'(4,)'],
        ['1',
         '[0, 1, 2]',
         '[3, 4, 5, 6]',
         'Column names: 0, 1, 2',
         'Series object of pandas.core.series module',
         'Column names: 0, 1, 2',
         'Series object of pandas.core.series module',
         ]]


def test_sort_and_fetch_collectionsmodel_with_many_rows():
    coll = list(range(2*LARGE_NROWS))
    cm = CollectionsModel(MockParent(), coll)
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
        editor.setCurrentIndex(editor.model.index(0, 0))
        editor.refresh_menu()
        assert editor.rename_action.isEnabled() == rename_enabled
        assert editor.duplicate_action.isEnabled() == duplicate_enabled
        if isinstance(coll, list):
            editor.duplicate_item()
            assert editor.source_model.get_data() == coll_copy + [coll_copy[0]]


def test_edit_datetime(monkeypatch):
    """
    Test datetimes are editable and NaT values are correctly handled.

    Regression test for spyder-ide/spyder#13557 and spyder-ide/spyder#8329
    """
    variables = [pandas.NaT, datetime.date.today()]
    editor_list = CollectionsEditorTableView(None, variables)

    # Test that the NaT value cannot be edited on the variable explorer
    editor_list_value = editor_list.delegate.createEditor(
        None, None, editor_list.model.index(0, 3))
    assert editor_list_value is None

    # Test that a date can be edited on the variable explorer
    editor_list_value = editor_list.delegate.createEditor(
        None, None, editor_list.model.index(1, 3))
    assert isinstance(editor_list_value, QDateEdit)


def test_edit_mutable_and_immutable_types(monkeypatch):
    """
    Test that mutable objs/vals are editable in VarExp; immutable ones aren't.

    Regression test for spyder-ide/spyder#5991.
    """
    MockQLineEdit = Mock()
    attr_to_patch_qlineedit = ('spyder.plugins.variableexplorer.widgets.' +
                               'collectionsdelegate.QLineEdit')
    monkeypatch.setattr(attr_to_patch_qlineedit, MockQLineEdit)

    MockTextEditor = Mock()
    attr_to_patch_textedit = ('spyder.plugins.variableexplorer.widgets.' +
                              'collectionsdelegate.TextEditor')
    monkeypatch.setattr(attr_to_patch_textedit, MockTextEditor)

    MockQDateTimeEdit = Mock()
    attr_to_patch_qdatetimeedit = ('spyder.plugins.variableexplorer.widgets.' +
                                   'collectionsdelegate.QDateTimeEdit')
    monkeypatch.setattr(attr_to_patch_qdatetimeedit, MockQDateTimeEdit)

    MockCollectionsEditor = Mock()
    mockCollectionsEditor_instance = MockCollectionsEditor()
    attr_to_patch_coledit = ('spyder.widgets.' +
                             'collectionseditor.CollectionsEditor')
    monkeypatch.setattr(attr_to_patch_coledit, MockCollectionsEditor)

    list_test = [1, "012345678901234567901234567890123456789012",
                 datetime.datetime(2017, 12, 24, 7, 9), [1, 2, 3], (2, "eggs")]
    tup_test = tuple(list_test)

    # Tests for mutable type (list) #
    editor_list = CollectionsEditorTableView(None, list_test)

    # Directly editable values inside list
    editor_list_value = editor_list.delegate.createEditor(
        None, None, editor_list.model.index(0, 3))
    assert editor_list_value is not None
    assert MockQLineEdit.call_count == 1

    # Text Editor for long text inside list
    editor_list.delegate.createEditor(None, None,
                                      editor_list.model.index(1, 3))
    assert MockTextEditor.call_count == 2
    assert not MockTextEditor.call_args[1]["readonly"]

    # Datetime inside list
    editor_list_datetime = editor_list.delegate.createEditor(
        None, None, editor_list.model.index(2, 3))
    assert editor_list_datetime is not None
    assert MockQDateTimeEdit.call_count == 1

    # List inside list
    editor_list.delegate.createEditor(None, None,
                                      editor_list.model.index(3, 3))
    assert mockCollectionsEditor_instance.show.call_count == 1
    assert not mockCollectionsEditor_instance.setup.call_args[1]["readonly"]

    # Tuple inside list
    editor_list.delegate.createEditor(None, None,
                                      editor_list.model.index(4, 3))
    assert mockCollectionsEditor_instance.show.call_count == 2
    assert mockCollectionsEditor_instance.setup.call_args[1]["readonly"]

    # Tests for immutable type (tuple) #
    editor_tup = CollectionsEditorTableView(None, tup_test)

    # Directly editable values inside tuple
    editor_tup_value = editor_tup.delegate.createEditor(
        None, None, editor_tup.model.index(0, 3))
    assert editor_tup_value is None
    assert MockQLineEdit.call_count == 1

    # Text Editor for long text inside tuple
    editor_tup.delegate.createEditor(None, None,
                                     editor_tup.model.index(1, 3))
    assert MockTextEditor.call_count == 4
    assert MockTextEditor.call_args[1]["readonly"]

    # Datetime inside tuple
    editor_tup_datetime = editor_tup.delegate.createEditor(
        None, None, editor_tup.model.index(2, 3))
    assert editor_tup_datetime is None
    assert MockQDateTimeEdit.call_count == 1

    # List inside tuple
    editor_tup.delegate.createEditor(None, None,
                                     editor_tup.model.index(3, 3))
    assert mockCollectionsEditor_instance.show.call_count == 3
    assert mockCollectionsEditor_instance.setup.call_args[1]["readonly"]

    # Tuple inside tuple
    editor_tup.delegate.createEditor(None, None,
                                     editor_tup.model.index(4, 3))
    assert mockCollectionsEditor_instance.show.call_count == 4
    assert mockCollectionsEditor_instance.setup.call_args[1]["readonly"]


@flaky(max_runs=3)
def test_view_module_in_coledit():
    """
    Test that modules don't produce an error when opening in Variable Explorer.

    Also check that they are set as readonly. Regression test for
    spyder-ide/spyder#6080.
    """
    editor = CollectionsEditor()
    editor.setup(os, "module_test", readonly=False)
    assert editor.widget.editor.readonly

def test_notimplementederror_multiindex():
    """
    Test that the NotImplementedError when scrolling a MultiIndex is handled.

    Regression test for spyder-ide/spyder#6284.
    """
    time_deltas = [pandas.Timedelta(minutes=minute)
                   for minute in range(5, 35, 5)]
    time_delta_multiindex = pandas.MultiIndex.from_product([[0, 1, 2, 3, 4],
                                                            time_deltas])
    col_model = CollectionsModel(MockParent(), time_delta_multiindex)
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

    Regression test for spyder-ide/spyder#5696.
    """
    # Mocking and setup
    test_parent = QWidget()

    MockCollectionsEditor = Mock()
    attr_to_patch_coledit = ('spyder.widgets.' +
                             'collectionseditor.CollectionsEditor')
    monkeypatch.setattr(attr_to_patch_coledit, MockCollectionsEditor)

    MockArrayEditor = Mock()
    attr_to_patch_arredit = ('spyder.plugins.variableexplorer.widgets.' +
                             'collectionsdelegate.ArrayEditor')
    monkeypatch.setattr(attr_to_patch_arredit, MockArrayEditor)

    MockDataFrameEditor = Mock()
    attr_to_patch_dfedit = ('spyder.plugins.variableexplorer.widgets.' +
                            'collectionsdelegate.DataFrameEditor')
    monkeypatch.setattr(attr_to_patch_dfedit, MockDataFrameEditor)

    MockTextEditor = Mock()
    attr_to_patch_textedit = ('spyder.plugins.variableexplorer.widgets.' +
                              'collectionsdelegate.TextEditor')
    monkeypatch.setattr(attr_to_patch_textedit, MockTextEditor)

    MockObjectExplorer = Mock()
    attr_to_patch_objectexplorer = ('spyder.plugins.variableexplorer.widgets.'
                                    + 'objectexplorer.ObjectExplorer')
    monkeypatch.setattr(attr_to_patch_objectexplorer, MockObjectExplorer)

    editor_data = [[0, 1, 2, 3, 4],
                   numpy.array([1.0, 42.0, 1337.0]),
                   pandas.DataFrame([[1, 2, 3], [20, 30, 40]]),
                   os,
                   "012345678901234567890123456789012345678901234567890123456"]
    col_editor = CollectionsEditorTableView(test_parent, editor_data)
    assert col_editor.parent() is test_parent

    for idx, mock_class in enumerate([MockCollectionsEditor,
                                      MockArrayEditor,
                                      MockDataFrameEditor,
                                      MockObjectExplorer,
                                      MockTextEditor]):
        col_editor.delegate.createEditor(col_editor.parent(), None,
                                         col_editor.model.index(idx, 3))
        assert mock_class.call_count == 1 + (idx // 4)
        assert mock_class.call_args[1]["parent"] is test_parent


def test_xml_dom_element_view():
    """
    Test that XML DOM ``Element``s are able to be viewied in CollectionsEditor.

    Regression test for spyder-ide/spyder#5642.
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

    Regression test for spyder-ide/spyder#6729.
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

    Unit regression test for issues spyder-ide/spyder#6727 and
    spyder-ide/spyder#6728.
    """
    for test_obj, expected_obj, keys in nonsettable_objects_data:
        col_model = CollectionsModel(None, test_obj)
        col_model.load_all()
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

    Integration regression test for issues spyder-ide/spyder#6727 and
    spyder-ide/spyder#6728.
    """
    for test_obj, expected_obj, keys in nonsettable_objects_data:
        col_editor = CollectionsEditor(None)
        col_editor.setup(test_obj)
        col_editor.show()
        qtbot.waitForWindowShown(col_editor)
        view = col_editor.widget.editor
        indicies = [view.source_model.get_index_from_key(key) for key in keys]

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

        if getattr(test_obj, "_typ", None) is None:
            keys.remove("_typ")

        assert all([getattr(test_obj, key)
                    == getattr(expected_obj, key) for key in keys])


def test_collectionseditor_with_class_having_buggy_copy(qtbot):
    """
    Test that editor for object whose .copy() returns a different type is
    readonly; cf. spyder-ide/spyder#6936.
    """
    class MyDictWithBuggyCopy(dict):
        pass

    md = MyDictWithBuggyCopy({1: 2})
    editor = CollectionsEditor()
    editor.setup(md)
    assert editor.widget.editor.readonly


def test_collectionseditor_with_class_having_correct_copy(qtbot):
    """
    Test that editor for object whose .copy() returns the same type is not
    readonly; cf. spyder-ide/spyder#6936.
    """
    class MyDictWithCorrectCopy(dict):
        def copy(self):
            return MyDictWithCorrectCopy(self)

    md = MyDictWithCorrectCopy({1: 2})
    editor = CollectionsEditor()
    editor.setup(md)
    assert not editor.widget.editor.readonly


def test_collectionseditor_when_clicking_on_header_and_large_rows(qtbot):
    """
    Test that sorting works when clicking in its header and there's a
    large number of rows.
    """
    li = [1] * 10000
    editor = CollectionsEditor()
    editor.setup(li)

    # Perform the sorting. It should be done quite quickly because
    # there's a very small number of rows in display.
    view = editor.widget.editor
    header = view.horizontalHeader()
    with qtbot.waitSignal(header.sectionClicked, timeout=200):
        qtbot.mouseClick(header.viewport(), Qt.LeftButton, pos=QPoint(1, 1))

    # Assert data was sorted correctly.
    assert data(view.model, 0, 0) == 9999


def test_dicts_with_mixed_types_as_key(qtbot):
    """
    Test that we can show dictionaries with mixed data types as keys.

    This is a regression for spyder-ide/spyder#13481.
    """
    colors = {1: 'red', 'Y': 'yellow'}
    editor = CollectionsEditor()
    editor.setup(colors)
    assert editor.widget.editor.source_model.keys == [1, 'Y']


def test_dicts_natural_sorting(qtbot):
    """
    Test that natural sorting actually does what it should do
    """
    import random
    numbers = list(range(100))
    random.shuffle(numbers)
    dictionary = {'test{}'.format(i): None for i in numbers}
    data_sorted = sorted(list(dictionary.keys()), key=natsort)
    # numbers should be as a human would sort, e.g. test3 before test100
    # regular sort would sort test1, test10, test11,..., test2, test20,...
    expected = ['test{}'.format(i) for i in list(range(100))]
    editor = CollectionsEditor()
    editor.setup(dictionary)
    editor.widget.editor.source_model.sort(0)

    assert data_sorted == expected, 'Function failed'
    assert editor.widget.editor.source_model.keys == expected, \
        'GUI sorting fail'


def test_dicts_natural_sorting_mixed_types():
    """
    Test that natural sorting actually does what it should do.
    testing for issue 13733, as mixed types were sorted incorrectly.

    Sorting for other columns will be tested as well.
    """
    import pandas as pd
    dictionary = {'DSeries': pd.Series(dtype=int), 'aStr': 'algName',
                  'kDict': {2: 'asd', 3: 2}}

    # put this here variable, as it might change later to reflect string length
    str_size = get_size(dictionary['aStr'])

    editor = CollectionsEditor()
    editor.setup(dictionary)
    cm = editor.widget.editor.source_model
    cm.sort(0)
    keys = cm.keys
    types = cm.types
    sizes = cm.sizes

    assert keys == ['aStr', 'DSeries', 'kDict']
    assert types == ['str', 'Series', 'dict']
    assert sizes == [str_size, (0,), 2]

    assert data_table(cm, 3, 3) == [['aStr', 'DSeries', 'kDict'],
                                    ['str', 'Series', 'dict'],
                                    [str_size, '(0,)', 2]]

    # insert an item and check that it is still sorted correctly
    editor.widget.editor.new_value('List', [1, 2, 3])
    assert data_table(cm, 4, 3) == [['aStr', 'DSeries', 'kDict', 'List'],
                                    ['str', 'Series', 'dict', 'list'],
                                    [str_size, '(0,)', 2, 3]]
    cm.sort(0)
    assert data_table(cm, 4, 3) == [['aStr', 'DSeries', 'kDict', 'List'],
                                    ['str', 'Series', 'dict', 'list'],
                                    [str_size, '(0,)', 2, 3]]

    # now sort for types
    cm.sort(1)
    assert data_table(cm, 4, 3) == [['DSeries', 'kDict', 'List', 'aStr'],
                                    ['Series', 'dict', 'list', 'str'],
                                    ['(0,)', 2, 3, str_size]]

    # now sort for sizes
    cm.sort(2)
    assert data_table(cm, 4, 3) == [['DSeries', 'kDict', 'List', 'aStr'],
                                    ['Series', 'dict', 'list', 'str'],
                                    ['(0,)', 2, 3, str_size]]


if __name__ == "__main__":
    pytest.main()
