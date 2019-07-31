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
from spyder.plugins.todos.widgets.todogui import TodoWidget
from spyder.plugins.variableexplorer.widgets.tests.test_collectioneditor import \
    data_table


@pytest.fixture
def todo(qtbot):
    todo_widget = TodoWidget(None)
    qtbot.addWidget(todo_widget)
    todo_widget.resize(640, 480)
    return todo_widget


def test_todo_sorting(todo, qtbot):
    tododata = [["Fix me", 10, "XXX"],
                ["Change this", 32, "BUG"],
                ["See issue", 5, "TODO"]]

    todo.set_data(tododata, "")
    header = todo.todotable.horizontalHeader()

    # Check header is clickable
    assert header.sectionsClickable()

    # Chect correct number of items
    model = todo.todotable.model
    sortmodel = todo.todotable.sortmodel
    assert model.rowCount() == 3
    assert model.columnCount() == 4

    assert data_table(model, 3, 3) == [["XXX", "BUG", "TODO"],
                                       [10, 32, 5],
                                       ["Fix me", "Change this", "See issue"]]

    # Sorted by todo-label
    with qtbot.waitSignal(header.sectionClicked):
        todo.show()
        qtbot.mouseClick(header.viewport(), Qt.LeftButton, pos=QPoint(1, 1))

    assert data_table(model, 3, 3, sortmodel) == [["BUG", "TODO", "XXX"],
                                                  [32, 5, 10],
                                                  ["Change this", "See issue",
                                                   "Fix me"]]

    # Click again to sort in opposite order
    with qtbot.waitSignal(header.sectionClicked):
        todo.show()
        qtbot.mouseClick(header.viewport(), Qt.LeftButton, pos=QPoint(1, 1))

    assert data_table(model, 3, 3, sortmodel) == [["XXX", "TODO", "BUG"],
                                                  [10, 5, 32],
                                                  ["Fix me", "See issue",
                                                   "Change this"]]
