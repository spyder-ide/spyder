# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License

"""
Tests for namespacebrowser.py
"""

from __future__ import division

# Standard library imports
import string
import sys
try:
    from unittest.mock import Mock
except ImportError:
    from mock import Mock # Python 2

# Third party imports
from flaky import flaky
import pytest
from qtpy.QtCore import Qt, QPoint, QModelIndex

# Local imports
from spyder.plugins.variableexplorer.widgets.collectionseditor import (
    ROWS_TO_LOAD)
from spyder.plugins.variableexplorer.widgets.namespacebrowser import (
    NamespaceBrowser)
from spyder.plugins.variableexplorer.widgets.tests.test_collectioneditor import (
    data, data_table)
from spyder.py3compat import PY2


def test_setup_sets_dataframe_format(qtbot):
    browser = NamespaceBrowser(None)
    browser.set_shellwidget(Mock())
    browser.setup(exclude_private=True, exclude_uppercase=True,
                  exclude_capitalized=True, exclude_unsupported=False,
                  exclude_callables_and_modules=True,
                  minmax=False, dataframe_format='%10.5f')
    assert browser.editor.source_model.dataframe_format == '%10.5f'


@flaky(max_runs=5)
@pytest.mark.skipif(
    sys.platform.startswith('linux') and PY2,
    reason="Sometimes fails on Linux and Python 2"
)
def test_automatic_column_width(qtbot):
    browser = NamespaceBrowser(None)
    browser.set_shellwidget(Mock())
    browser.setup(exclude_private=True, exclude_uppercase=True,
                  exclude_capitalized=True, exclude_unsupported=False,
                  exclude_callables_and_modules=True,
                  minmax=False)
    col_width = [browser.editor.columnWidth(i) for i in range(4)]
    browser.set_data({'a_variable':
            {'type': 'int', 'size': 1, 'color': '#0000ff', 'view': '1'}})
    new_col_width = [browser.editor.columnWidth(i) for i in range(4)]
    assert browser.editor.automatic_column_width
    assert col_width != new_col_width  # Automatic col width is on
    browser.editor.horizontalHeader()._handle_section_is_pressed = True
    browser.editor.setColumnWidth(0, 100)  # Simulate user changing col width
    assert browser.editor.automatic_column_width == False
    browser.set_data({'a_lengthy_variable_name_which_should_change_width':
            {'type': 'int', 'size': 1, 'color': '#0000ff', 'view': '1'}})
    assert browser.editor.columnWidth(0) == 100  # Automatic col width is off


def test_sort_by_column(qtbot):
    """
    Test that clicking the header view the namespacebrowser is sorted.
    Regression test for spyder-ide/spyder#9835 .
    """
    browser = NamespaceBrowser(None)
    qtbot.addWidget(browser)
    browser.set_shellwidget(Mock())
    browser.setup(exclude_private=True, exclude_uppercase=True,
                  exclude_capitalized=True, exclude_unsupported=False,
                  exclude_callables_and_modules=True,
                  minmax=False)
    browser.set_data(
        {'a_variable':
            {'type': 'int', 'size': 1, 'color': '#0000ff', 'view': '1'},
         'b_variable':
            {'type': 'int', 'size': 1, 'color': '#0000ff', 'view': '2'}}
    )

    header = browser.editor.horizontalHeader()

    # Check header is clickable
    assert header.sectionsClickable()

    model = browser.editor.model

    # Base check of the model
    assert model.rowCount() == 2
    assert model.columnCount() == 5
    assert data_table(model, 2, 4) == [['a_variable', 'b_variable'],
                                       ['int', 'int'],
                                       [1, 1],
                                       ['1', '2']]

    with qtbot.waitSignal(header.sectionClicked):
        browser.show()
        qtbot.mouseClick(header.viewport(), Qt.LeftButton, pos=QPoint(1, 1))

    # Check sort effect
    assert data_table(model, 2, 4) == [['b_variable', 'a_variable'],
                                       ['int', 'int'],
                                       [1, 1],
                                       ['2', '1']]


def test_keys_sorted_and_sort_with_large_rows(qtbot):
    """
    Test that keys are sorted and sorting works as expected when
    there's a large number of rows.

    This is a regression test for issue spyder-ide/spyder#10702
    """
    browser = NamespaceBrowser(None)
    qtbot.addWidget(browser)
    browser.set_shellwidget(Mock())
    browser.setup(exclude_private=True, exclude_uppercase=True,
                  exclude_capitalized=True, exclude_unsupported=False,
                  exclude_callables_and_modules=True,
                  minmax=False)

    variables = {}

    # Create variables.
    variables['i'] = (
        {'type': 'int', 'size': 1, 'color': '#0000ff', 'view': '1'}
    )

    for i in range(100):
        if i < 10:
            var = 'd_0' + str(i)
        else:
            var = 'd_' + str(i)
        variables[var] = (
            {'type': 'int', 'size': 1, 'color': '#0000ff', 'view': '1'}
        )

    # Set data
    browser.set_data(variables)

    # Assert we loaded the expected amount of data and that we can fetch
    # more.
    model = browser.editor.model
    assert model.rowCount() == ROWS_TO_LOAD
    assert model.canFetchMore(QModelIndex())

    # Assert keys are sorted
    assert data(model, 49, 0) == 'd_49'

    # Sort
    header = browser.editor.horizontalHeader()
    with qtbot.waitSignal(header.sectionClicked):
        qtbot.mouseClick(header.viewport(), Qt.LeftButton, pos=QPoint(1, 1))

    # Assert we loaded all data before performing the sort.
    assert data(model, 0, 0) == 'i'


def test_filtering_with_large_rows(qtbot):
    """
    Test that filtering works when there's a large number of rows.
    """
    browser = NamespaceBrowser(None)
    qtbot.addWidget(browser)
    browser.set_shellwidget(Mock())
    browser.setup(exclude_private=True, exclude_uppercase=True,
                  exclude_capitalized=True, exclude_unsupported=False,
                  exclude_callables_and_modules=True,
                  minmax=False)

    # Create data
    variables = {}
    for i in range(200):
        letter = string.ascii_lowercase[i // 10]
        var = letter + str(i)
        variables[var] = (
            {'type': 'int', 'size': 1, 'color': '#0000ff', 'view': '1'}
        )

    # Set data
    browser.set_data(variables)

    # Assert we loaded the expected amount of data and that we can fetch
    # more data.
    model = browser.editor.model
    assert model.rowCount() == ROWS_TO_LOAD
    assert model.canFetchMore(QModelIndex())
    assert data(model, 49, 0) == 'e49'

    # Assert we can filter variables not loaded yet.
    qtbot.keyClicks(browser.finder.text_finder, "t19")
    assert model.rowCount() == 10

    # Assert all variables effectively start with 't19'.
    for i in range(10):
        assert data(model, i, 0) == 't19{}'.format(i)

    # Hide finder widget in order to reset it.
    browser.show_finder(set_visible=False)

    # Create a new variable that starts with a different letter than
    # the rest.
    new_variables = variables.copy()
    new_variables['z'] = (
        {'type': 'int', 'size': 1, 'color': '#0000ff', 'view': '1'}
    )

    # Emulate the process of loading those variables after the
    # namespace view is sent from the kernel.
    browser.process_remote_view(new_variables)

    # Assert that can find 'z' among the declared variables.
    qtbot.keyClicks(browser.finder.text_finder, "z")
    assert model.rowCount() == 1


if __name__ == "__main__":
    pytest.main()
