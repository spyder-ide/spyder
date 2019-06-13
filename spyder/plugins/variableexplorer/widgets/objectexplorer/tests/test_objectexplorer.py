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
from spyder.plugins.variableexplorer.widgets.tests.test_dataframeeditor \
    import data
from spyder.plugins.variableexplorer.widgets.objectexplorer.objectexplorer \
    import ObjectExplorer


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
    foobar = Foobar()
    example = {'foobar': foobar}
    editor = objectexplorer(example,
                            expanded=True,
                            show_callable_attributes=False,
                            show_special_attributes=False,
                            auto_refresh=False,
                            refresh_rate=2)
    # Editor was created
    assert editor

    # Check header data and default hidden sections
    header = editor.obj_tree.header()
    header_model = header.model()
    assert not header.isSectionHidden(0)
    assert header_model.headerData(0, Qt.Horizontal,
                                   Qt.DisplayRole) == "name"
    assert header.isSectionHidden(1)
    assert header_model.headerData(1, Qt.Horizontal,
                                   Qt.DisplayRole) == "type"
    assert not header.isSectionHidden(2)
    assert header_model.headerData(2, Qt.Horizontal,
                                   Qt.DisplayRole) == "path"
    assert not header.isSectionHidden(3)
    assert header_model.headerData(3, Qt.Horizontal,
                                   Qt.DisplayRole) == "summary"
    assert header.isSectionHidden(4)
    assert header_model.headerData(4, Qt.Horizontal,
                                   Qt.DisplayRole) == "unicode"
    assert header.isSectionHidden(5)
    assert header_model.headerData(5, Qt.Horizontal,
                                   Qt.DisplayRole) == "str"
    assert not header.isSectionHidden(6)
    assert header_model.headerData(6, Qt.Horizontal,
                                   Qt.DisplayRole) == "repr"
    assert header.isSectionHidden(7)
    assert header_model.headerData(7, Qt.Horizontal,
                                   Qt.DisplayRole) == "length"
    assert not header.isSectionHidden(8)
    assert header_model.headerData(8, Qt.Horizontal,
                                   Qt.DisplayRole) == "type name"
    assert header.isSectionHidden(9)
    assert header_model.headerData(9, Qt.Horizontal,
                                   Qt.DisplayRole) == "id"
    assert header.isSectionHidden(10)
    assert header_model.headerData(10, Qt.Horizontal,
                                   Qt.DisplayRole) == "is attribute"
    assert not header.isSectionHidden(11)
    assert header_model.headerData(11, Qt.Horizontal,
                                   Qt.DisplayRole) == "is callable"
    assert header.isSectionHidden(12)
    assert header_model.headerData(12, Qt.Horizontal,
                                   Qt.DisplayRole) == "is routine"
    assert header.isSectionHidden(13)
    assert header_model.headerData(13, Qt.Horizontal,
                                   Qt.DisplayRole) == "inspect predicates"
    assert header.isSectionHidden(14)
    assert header_model.headerData(14, Qt.Horizontal,
                                   Qt.DisplayRole) == "inspect.getmodule"
    assert header.isSectionHidden(15)
    assert header_model.headerData(15, Qt.Horizontal,
                                   Qt.DisplayRole) == "inspect.getfile"
    assert header.isSectionHidden(16)
    assert header_model.headerData(16, Qt.Horizontal,
                                   Qt.DisplayRole) == "inspect.getsourcefile"

    model = editor.obj_tree.model()

    # Check number of rows
    assert model.rowCount() == 1
    assert model.columnCount() == 17


def test_objectexplorer_types(objectexplorer):
    """Test to validate proper handling of multiple data types."""
    test = {'str': 'kjkj kj k j j kj k jkj',
            'list': [1, 3, 4, 'kjkj', None],
            'set': {1, 2, 1, 3, None, 'A', 'B', 'C', True, False},
            'dict': {'d': 1, 'a': np.random.rand(10, 10), 'b': [1, 2]},
            'float': 1.2233,
            'array': np.random.rand(10, 10),
            'date': datetime.date(1945, 5, 8),
            'datetime': datetime.datetime(1945, 5, 8)}
    editor = objectexplorer(test,
                            expanded=True,
                            show_callable_attributes=True,
                            show_special_attributes=True,
                            auto_refresh=False,
                            refresh_rate=2)
    # Editor was created
    assert editor

    # Check number of rows
    model = editor.obj_tree.model()
    assert model.rowCount() == 48
    assert model.columnCount() == 17


if __name__ == "__main__":
    pytest.main()
