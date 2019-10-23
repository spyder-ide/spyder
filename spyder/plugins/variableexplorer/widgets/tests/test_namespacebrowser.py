# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License

"""
Tests for namespacebrowser.py
"""

# Standard library imports
try:
    from unittest.mock import Mock
except ImportError:
    from mock import Mock # Python 2

# Third party imports
import pytest
from qtpy.QtCore import Qt, QPoint

# Local imports
from spyder.plugins.variableexplorer.widgets.namespacebrowser import NamespaceBrowser
from spyder.plugins.variableexplorer.widgets.tests.test_collectioneditor import data_table

def test_setup_sets_dataframe_format(qtbot):
    browser = NamespaceBrowser(None)
    browser.set_shellwidget(Mock())
    browser.setup(exclude_private=True, exclude_uppercase=True,
                  exclude_capitalized=True, exclude_unsupported=True,
                  minmax=False, dataframe_format='%10.5f')
    assert browser.editor.source_model.dataframe_format == '%10.5f'


def test_automatic_column_width(qtbot):
    browser = NamespaceBrowser(None)
    browser.set_shellwidget(Mock())
    browser.setup(exclude_private=True, exclude_uppercase=True,
                  exclude_capitalized=True, exclude_unsupported=True,
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
                  exclude_capitalized=True, exclude_unsupported=True,
                  minmax=False)
    browser.set_data(
        {'a_variable':
            {'type': 'int', 'size': 1, 'color': '#0000ff', 'view': '1'},
         'b_variable':
            {'type': 'int', 'size': 1, 'color': '#0000ff', 'view': '2'}})

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


if __name__ == "__main__":
    pytest.main()
