# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""Todo widget"""

# pylint: disable=C0103
# pylint: disable=R0903
# pylint: disable=R0911
# pylint: disable=R0201

# Standard library imports
import sys

# Third party imports
from qtpy.compat import to_qvariant
from qtpy.QtCore import (QAbstractTableModel, QModelIndex, Qt, Signal,
                         QSortFilterProxyModel, Slot)
from qtpy.QtWidgets import (QTableView, QHBoxLayout, QHeaderView,
                            QVBoxLayout, QWidget, QAbstractItemView)

# Local imports
from spyder.config.base import get_translation
from spyder.utils.qthelpers import create_plugin_layout

# This is needed for testing this module as a stand alone script
try:
    _ = get_translation("todo", "spyder_todo")
except KeyError:
    import gettext
    _ = gettext.gettext

COLUMN_COUNT = 4
COL_TYPE, COL_LINE, COL_COMMENT, COL_BLANK = range(COLUMN_COUNT)
COLUMN_HEADERS = (_("Type"), _("Line"), _("Comment"), "")


class TodoTableModel(QAbstractTableModel):
    """
    Table model for Todo list

    """

    def __init__(self, parent, data):
        QAbstractTableModel.__init__(self, parent)
        if data is None:
            data = {}
        self._data = None
        self.todos = None
        self.set_data(data)

    def set_data(self, data):
        """Set model data"""
        self._data = data
        self.todos = []
        for item in data:
            self.todos.append((item[2], item[1], item[0], ""))
        self.reset()

    def rowCount(self, qindex=QModelIndex()):
        """Array row number"""
        return len(self._data)

    def columnCount(self, qindex=QModelIndex()):
        """Array column count"""
        return COLUMN_COUNT

    def headerData(self, section, orientation, role=Qt.DisplayRole):
        """Overriding method headerData"""
        if role != Qt.DisplayRole:
            return to_qvariant()
        i_column = int(section)
        if orientation == Qt.Horizontal:
            return to_qvariant(COLUMN_HEADERS[i_column])
        else:
            return to_qvariant()

    def get_value(self, index):
        """Return current value"""
        return self.todos[index.row()][index.column()]

    def data(self, index, role=Qt.DisplayRole):
        """Return data at table index"""
        if not index.isValid():
            return to_qvariant()
        if role == Qt.DisplayRole:
            value = self.get_value(index)
            return to_qvariant(value)
        elif role == Qt.TextAlignmentRole:
            if index.column() == COL_LINE:
                # Align line number right
                return to_qvariant(int(Qt.AlignRight | Qt.AlignVCenter))
            else:
                return to_qvariant(int(Qt.AlignLeft | Qt.AlignVCenter))

    def reset(self):
        self.beginResetModel()
        self.endResetModel()


class TodoTableView(QTableView):
    edit_goto = Signal(int)

    def __init__(self, parent, data):
        QTableView.__init__(self, parent)

        self.setup_table()
        self.model = TodoTableModel(self, data)
        self.sortmodel = QSortFilterProxyModel()
        self.sortmodel.setSourceModel(self.model)
        self.setModel(self.sortmodel)

    def setup_table(self):
        """Setup table"""
        self.setStyleSheet('QTableView {padding: 0px;}')
        self.verticalHeader().setSectionResizeMode(
                QHeaderView.ResizeToContents)
        self.horizontalHeader().setStretchLastSection(True)
        self.adjust_columns()
        self.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.setSelectionMode(QAbstractItemView.SingleSelection)
        self.setSortingEnabled(True)
        self.sortByColumn(COL_LINE, Qt.AscendingOrder)
        self.setShowGrid(False)
        self.clicked.connect(self.onClick)

    def adjust_columns(self):
        """Resize all but last column to contents"""
        for col in range(COLUMN_COUNT - 1):
            self.resizeColumnToContents(col)

    def onClick(self, item):
        """Double-click event"""
        original_item = self.sortmodel.mapToSource(item)
        data = self.model.todos[original_item.row()]
        self.edit_goto.emit(data[COL_LINE])


class TodoWidget(QWidget):
    """
    Todo widget
    """
    VERSION = '1.0.0'
    edit_goto = Signal(str, int, str)

    def __init__(self, parent, options_button=None):
        QWidget.__init__(self, parent)
        self.filename = None
        self.setWindowTitle(_("Todos"))
        self.todotable = TodoTableView(self, None)
        if options_button:
            btn_layout = QHBoxLayout()
            btn_layout.setAlignment(Qt.AlignLeft)
            btn_layout.addStretch()
            btn_layout.addWidget(options_button, Qt.AlignRight)
            layout = create_plugin_layout(btn_layout, self.todotable)
        else:
            layout = QVBoxLayout()
            layout.addWidget(self.todotable)
        self.setLayout(layout)
        # Connect signal
        self.todotable.edit_goto.connect(self.edit_goto_handler)

    @Slot(int)
    def edit_goto_handler(self, line_number):
        self.edit_goto.emit(self.filename, line_number, '')

    def get_data(self):
        pass

    def set_data(self, todo_data, filename):
        self.todotable.model.set_data(todo_data)
        self.todotable.adjust_columns()
        self.filename = filename


# =============================================================================
# Tests
# =============================================================================
def test():
    """Run todo widget test"""
    from spyder.utils.qthelpers import qapplication
    app = qapplication()
    widget = TodoWidget(None)
    widget.show()
    sys.exit(app.exec_())


if __name__ == '__main__':
    test()
