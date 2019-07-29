# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""Bookmarks widget"""

# pylint: disable=C0103
# pylint: disable=R0903
# pylint: disable=R0911
# pylint: disable=R0201

# Standard library imports
import os.path as osp
import sys

# Third party imports
from qtpy.compat import to_qvariant
from qtpy.QtCore import (QAbstractTableModel, QModelIndex, Qt, Signal,
                         QSortFilterProxyModel, Slot)
from qtpy.QtWidgets import (QTableView, QHBoxLayout,
                            QVBoxLayout, QWidget, QAbstractItemView,
                            QHeaderView)

# Local imports
from spyder.config.base import get_translation
from spyder.utils.qthelpers import create_plugin_layout
from spyder.config.manager import CONF
from spyder.utils.sourcecode import disambiguate_fname

# This is needed for testing this module as a stand alone script
try:
    _ = get_translation("bookmarks", "spyder_bookmarks")
except KeyError:
    import gettext
    _ = gettext.gettext

COLUMN_COUNT = 5
EXTRA_COLUMNS = 1
COL_SLOT, COL_FILE, COL_LINE, COL_SHORTCUT, COL_BLANK, COL_FULL = range(
        COLUMN_COUNT + EXTRA_COLUMNS)
COLUMN_HEADERS = (_("Slot"), _("File"), _("Line"), _("Shortcut"), "")


class BookmarkTableModel(QAbstractTableModel):
    """
    Table model for bookmarks list

    """

    def __init__(self, parent, data):
        QAbstractTableModel.__init__(self, parent)
        if data is None:
            data = {}
        self._data = None
        self.bookmarks = None
        self.set_data(data)

    def set_data(self, data):
        """Set model data"""
        self._data = data
        self.bookmarks = []
        filenames = []
        if data:
            for slot_num in list(data.keys()):
                filenames.append(data[slot_num][0])
            for slot_num in list(data.keys()):
                filename = data[slot_num][0]
                line_number = data[slot_num][1]
                self.bookmarks.append((slot_num,
                                       disambiguate_fname(filenames, filename),
                                       line_number, "TBD", "", filename))
        self.reset()

    def rowCount(self, qindex=QModelIndex()):
        """Array row number"""
        return len(self.bookmarks)

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
        return self.bookmarks[index.row()][index.column()]

    def data(self, index, role=Qt.DisplayRole):
        """Return data at table index"""
        if not index.isValid():
            return to_qvariant()
        if role == Qt.DisplayRole:
            value = self.get_value(index)
            return to_qvariant(value)
        elif role == Qt.TextAlignmentRole:
            if index.column() in (COL_SLOT, COL_LINE):
                # Align line number right
                return to_qvariant(int(Qt.AlignRight | Qt.AlignVCenter))
            else:
                return to_qvariant(int(Qt.AlignLeft | Qt.AlignVCenter))

    def reset(self):
        self.beginResetModel()
        self.endResetModel()


class BookmarkTableView(QTableView):
    edit_goto = Signal(str, int)

    def __init__(self, parent, data):
        QTableView.__init__(self, parent)

        self.model = BookmarkTableModel(self, data)
        self.sortmodel = QSortFilterProxyModel()
        self.sortmodel.setSourceModel(self.model)
        self.setModel(self.sortmodel)
        self.setup_table()

    def setup_table(self):
        """Setup table"""
        # Minmize row spacing
        self.setStyleSheet('QTableView {padding: 0px;}')
        self.verticalHeader().setSectionResizeMode(
                QHeaderView.ResizeToContents)
        self.horizontalHeader().setStretchLastSection(True)
        self.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.setSelectionMode(QAbstractItemView.SingleSelection)
        self.setSortingEnabled(True)
        self.setShowGrid(False)
        self.clicked.connect(self.onClick)
        self.adjust_columns()

    def adjust_columns(self):
        """Resize all but last column to contents"""
        for col in range(COLUMN_COUNT - 1):
            self.resizeColumnToContents(col)

    def onClick(self, item):
        """Double-click event"""
        original_item = self.sortmodel.mapToSource(item)
        data = self.model.bookmarks[original_item.row()]
        self.edit_goto.emit(data[COL_FULL], data[COL_LINE])



class BookmarkWidget(QWidget):
    """
    Bookmarks widget
    """
    VERSION = '1.0.0'
    edit_goto = Signal(str, int, str)

    def __init__(self, parent, options_button=None):
        QWidget.__init__(self, parent)

        self.setWindowTitle("Bookmarks")
        self.bookmarktable = BookmarkTableView(self, None)
        if options_button:
            btn_layout = QHBoxLayout()
            btn_layout.setAlignment(Qt.AlignLeft)
            btn_layout.addStretch()
            btn_layout.addWidget(options_button, Qt.AlignRight)
            layout = create_plugin_layout(btn_layout, self.bookmarktable)
        else:
            layout = QVBoxLayout()
            layout.addWidget(self.bookmarktable)
        self.setLayout(layout)
        self.bookmarktable.edit_goto.connect(self.edit_goto_handler)

    @Slot(str, int)
    def edit_goto_handler(self, filename, line_number):
        self.edit_goto.emit(filename, line_number, '')

    def get_data(self):
        pass

    @Slot()
    def set_data(self):
        print("Set data")
        bookmarks = self._load_all_bookmarks()
        print(bookmarks)
        self.bookmarktable.model.set_data(bookmarks)
        self.bookmarktable.adjust_columns()
        self.bookmarktable.sortByColumn(COL_FILE, Qt.DescendingOrder)

    def _load_all_bookmarks(self):
        slots = CONF.get('editor', 'bookmarks', {})
        for slot_num in list(slots.keys()):
            if not osp.isfile(slots[slot_num][0]):
                slots.pop(slot_num)
        return slots



# =============================================================================
# Tests
# =============================================================================
def test():
    """Run bookmarks/errors widget test"""
    from spyder.utils.qthelpers import qapplication
    app = qapplication()
    widget = BookmarkWidget(None)
    widget.show()
    sys.exit(app.exec_())


if __name__ == '__main__':
    test()
