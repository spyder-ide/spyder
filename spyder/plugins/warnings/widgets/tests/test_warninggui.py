# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
#

"""
Tests for todogui.py
"""

# Third part imports
import pytest
from qtpy.QtCore import Qt, QPoint

# Local imports
from spyder.plugins.completion.languageserver import DiagnosticSeverity
from spyder.plugins.variableexplorer.widgets.tests.test_collectioneditor import \
    data_table
from spyder.plugins.warnings.widgets.warninggui import WarningWidget


@pytest.fixture
def warning(qtbot):
    warning_widget = WarningWidget(None)
    qtbot.addWidget(warning_widget)
    warning_widget.resize(640, 480)
    return warning_widget


def test_warning_sorting(warning, qtbot):
    warningdata = [["pyflakes", "E100", DiagnosticSeverity.ERROR,
                    "Not good", 10],
                   ["pychecker", "F104", DiagnosticSeverity.WARNING,
                    "Some issue", 25],
                   ["pylint", "E102", DiagnosticSeverity.HINT,
                    "Maybe change this", 52]]

    warning.set_data(warningdata, "")
    header = warning.warningtable.horizontalHeader()

    # Check header is clickable
    assert header.sectionsClickable()

    # Chect correct number of items
    model = warning.warningtable.model
    sortmodel = warning.warningtable.sortmodel
    assert model.rowCount() == 3
    assert model.columnCount() == 5

    assert data_table(model, 3, 4) == [["E100", "F104", "E102"],
                                       [10, 25, 52],
                                       ["Not good", "Some issue",
                                        "Maybe change this"],
                                       ["pyflakes", "pychecker", "pylint"]]

    # Sorted by code
    with qtbot.waitSignal(header.sectionClicked):
        warning.show()
        qtbot.mouseClick(header.viewport(), Qt.LeftButton, pos=QPoint(1, 1))

    assert data_table(model, 3, 4, sortmodel) == [["E100", "E102", "F104"],
                                                  [10, 52, 25],
                                                  ["Not good",
                                                   "Maybe change this",
                                                   "Some issue"],
                                                  ["pyflakes", "pylint",
                                                   "pychecker"]]

    # Sorted by code again => opposite order
    with qtbot.waitSignal(header.sectionClicked):
        warning.show()
        qtbot.mouseClick(header.viewport(), Qt.LeftButton, pos=QPoint(1, 1))

    assert data_table(model, 3, 4, sortmodel) == [["F104", "E102", "E100"],
                                                  [25, 52, 10],
                                                  ["Some issue",
                                                   "Maybe change this",
                                                   "Not good"],
                                                  ["pychecker", "pylint",
                                                   "pyflakes"]]
