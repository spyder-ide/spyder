# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright (c) 2019- Spyder Project Contributors
#
# Released under the terms of the MIT License
# (see LICENSE.txt in the Spyder root directory for details)
# -----------------------------------------------------------------------------

"""
Tests for the array editor.
"""

# Standard library imports
import datetime

# Third party imports
from qtpy.QtCore import Qt
import numpy as np
import pytest

# Local imports
from spyder.plugins.variableexplorer.widgets.objectexplorer import (
        ObjectExplorer)
from spyder.py3compat import PY2

# =============================================================================
# Fixtures
# =============================================================================
@pytest.fixture
def objectexplorer(qtbot):
    """Set up ObjectExplorer."""
    def create_objectexplorer(obj, **kwargs):
        editor = ObjectExplorer(obj, **kwargs)
        qtbot.addWidget(editor)
        return editor
    return create_objectexplorer


# =============================================================================
# Tests
# =============================================================================
def test_objectexplorer(objectexplorer):
    """Test to validate proper creation of the editor."""
    class Foobar(object):
        def __init__(self):
            self.text = "toto"

        def get_text(self):
            return self.text

        @property
        def error_attribute(self):
            # Attribute to test that the object explorer
            # handles errors by getattr gracefully
            raise AttributeError

    foobar = Foobar()
    editor = objectexplorer(foobar,
                            name='foobar',
                            show_callable_attributes=False,
                            show_special_attributes=False)
    # Editor was created
    assert editor

    # Check header data and default hidden sections
    header = editor.obj_tree.header()
    header_model = header.model()
    assert not header.isSectionHidden(0)
    assert header_model.headerData(0, Qt.Horizontal,
                                   Qt.DisplayRole) == "Name"
    assert not header.isSectionHidden(1)
    assert header_model.headerData(1, Qt.Horizontal,
                                   Qt.DisplayRole) == "Type"
    assert not header.isSectionHidden(2)
    assert header_model.headerData(2, Qt.Horizontal,
                                   Qt.DisplayRole) == "Size"
    assert not header.isSectionHidden(3)
    assert header_model.headerData(3, Qt.Horizontal,
                                   Qt.DisplayRole) == "Value"
    assert not header.isSectionHidden(4)
    assert header_model.headerData(4, Qt.Horizontal,
                                   Qt.DisplayRole) == "Callable"
    assert not header.isSectionHidden(5)
    assert header_model.headerData(5, Qt.Horizontal,
                                   Qt.DisplayRole) == "Path"
    assert header.isSectionHidden(6)
    assert header_model.headerData(6, Qt.Horizontal,
                                   Qt.DisplayRole) == "Id"
    assert header.isSectionHidden(7)
    assert header_model.headerData(7, Qt.Horizontal,
                                   Qt.DisplayRole) == "Attribute"
    assert header.isSectionHidden(8)
    assert header_model.headerData(8, Qt.Horizontal,
                                   Qt.DisplayRole) == "Routine"
    assert header.isSectionHidden(9)
    assert header_model.headerData(9, Qt.Horizontal,
                                   Qt.DisplayRole) == "File"
    assert header.isSectionHidden(10)
    assert header_model.headerData(10, Qt.Horizontal,
                                   Qt.DisplayRole) == "Source file"

    model = editor.obj_tree.model()

    # Check number of rows
    assert model.rowCount() == 1
    assert model.columnCount() == 11


@pytest.mark.parametrize('params', [
            'kjkj kj k j j kj k jkj',
            [1, 3, 4, 'kjkj', None],
            {1, 2, 1, 3, None, 'A', 'B', 'C', True, False},
            1.2233,
            np.random.rand(10, 10),
            datetime.date(1945, 5, 8),
            datetime.datetime(1945, 5, 8)
        ])
def test_objectexplorer_collection_types(objectexplorer, params):
    """Test to validate proper handling of collection data types."""
    test = params
    editor = objectexplorer(test,
                            name='variable',
                            show_callable_attributes=True,
                            show_special_attributes=True)
    # Editor was created
    assert editor

    # Check number of rows and row content
    model = editor.obj_tree.model()
    # The row for the variable
    assert model.rowCount() == 1
    # Root row without children
    assert model.rowCount(model.index(0, 0)) == 0
    assert model.columnCount() == 11


@pytest.mark.parametrize('params', [
            # show_callable_, show_special_, rowCount for python 3 and 2
            (True, True, [34, 26], ),
            (False, False, [8, 8], )
        ])
def test_objectexplorer_types(objectexplorer, params):
    """Test to validate proper handling of data types inside an object."""
    class Foobar(object):
        def __init__(self):
            self.text = "toto"
            self.list = [1, 3, 4, 'kjkj', None]
            self.set = {1, 2, 1, 3, None, 'A', 'B', 'C', True, False},
            self.dict = {'d': 1, 'a': np.random.rand(10, 10), 'b': [1, 2]},
            self.float = 1.2233,
            self.array = np.random.rand(10, 10),
            self.date = datetime.date(1945, 5, 8),
            self.datetime = datetime.datetime(1945, 5, 8)
    foo = Foobar()

    show_callable, show_special, row_count = params
    editor = objectexplorer(foo,
                            name='foo',
                            show_callable_attributes=show_callable,
                            show_special_attributes=show_special)
    # Editor was created
    assert editor

    # Check number of rows and row content
    model = editor.obj_tree.model()
    # The row for the object
    assert model.rowCount() == 1
    # Rows from the object attributes
    assert model.rowCount(model.index(0, 0)) in row_count
    assert model.columnCount() == 11


if __name__ == "__main__":
    pytest.main()
