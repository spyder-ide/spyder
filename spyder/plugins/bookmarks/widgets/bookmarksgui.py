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
from qtpy import API
from qtpy.compat import to_qvariant
from qtpy.QtCore import (QAbstractTableModel, QModelIndex, Qt, Signal,
                         QSortFilterProxyModel, Slot)
from qtpy.QtWidgets import (QTableView, QHBoxLayout, QMenu,
                            QVBoxLayout, QWidget, QAbstractItemView,
                            QHeaderView)

# Local imports
from spyder.config.base import get_translation
from spyder.utils.qthelpers import (add_actions, create_action,
                                    create_plugin_layout)
from spyder.config.manager import CONF
from spyder.utils.sourcecode import disambiguate_fname

# This is needed for testing this module as a stand alone script
try:
    _ = get_translation("bookmarks", "spyder_bookmarks")
except KeyError:
    import gettext
    _ = gettext.gettext

COLUMN_COUNT = 6
EXTRA_COLUMNS = 1
COL_SLOT, COL_FILE, COL_LINE, COL_COL, COL_SHORTCUT, COL_BLANK, COL_FULL = range(
        COLUMN_COUNT + EXTRA_COLUMNS)
COLUMN_HEADERS = (_("Slot"), _("File"), _("Line"), _("Col"), _("Shortcut"), "")


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
                filename = data[slot_num][0]
                if filename not in filenames:
                    filenames.append(filename)
            for slot_num in list(data.keys()):
                filename = data[slot_num][0]
                line_number = data[slot_num][1]
                column_number = data[slot_num][2]
                self.bookmarks.append((slot_num,
                                       disambiguate_fname(filenames, filename),
                                       line_number, column_number, "TBD", "", filename))
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
            if index.column() in (COL_SLOT, COL_LINE, COL_COL):
                # Align line number right
                return to_qvariant(int(Qt.AlignRight | Qt.AlignVCenter))
            else:
                return to_qvariant(int(Qt.AlignLeft | Qt.AlignVCenter))

    def reset(self):
        self.beginResetModel()
        self.endResetModel()


class BookmarkTableView(QTableView):
    load_bookmark = Signal(int)
    delete_bookmark = Signal(int)
    update_bookmark = Signal(int, int, int)
    delete_all_bookmarks = Signal()

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
        self.adjust_columns()

    def adjust_columns(self):
        """Resize all but last column to contents"""
        for col in range(COLUMN_COUNT - 1):
            self.resizeColumnToContents(col)

    def mouseDoubleClickEvent(self, event):
        """Double-click event"""
        if self.model.bookmarks:
            item_clicked = self.indexAt(event.pos())
            item_row = self.sortmodel.mapToSource(item_clicked).row()
            slot_number = self.model.bookmarks[item_row][COL_SLOT]
            self.load_bookmark.emit(int(slot_number))

    def contextMenuEvent(self, event):
        index_clicked = self.indexAt(event.pos())
        actions = []
        self.popup_menu = QMenu(self)
        delete_all_bookmarks_action = create_action(self,
            _("Delete bookmarks in all files"),
            triggered=lambda: self.delete_all_bookmarks.emit())
        actions.append(delete_all_bookmarks_action)
        if self.model.bookmarks:
            slot = int(self.model.bookmarks[index_clicked.row()][COL_SLOT])
            # QAction.triggered works differently for PySide and PyQt
            if not API == 'pyside':
                clear_slot = lambda _checked, slot=slot: \
                    self.delete_bookmark.emit(slot)
            else:
                clear_slot = lambda slot=slot: \
                    self.delete_bookmark.emit(slot)

            clear_bookmark_action = create_action(self,
                                                  _("Delete this bookmark"),
                                                  triggered=clear_slot)
            actions.insert(0, clear_bookmark_action)

        add_actions(self.popup_menu, actions)
        self.popup_menu.popup(event.globalPos())
        event.accept()


class BookmarkWidget(QWidget):
    """
    Bookmarks widget
    """
    VERSION = '1.0.0'
    load_bookmark = Signal(int)
    delete_bookmark = Signal(int)
    delete_all_bookmarks = Signal()
    update_bookmark = Signal(int, int, int)

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
        self.bookmarktable.load_bookmark.connect(self.load_bookmark)
        self.bookmarktable.delete_all_bookmarks.connect(self.delete_all_bookmarks)
        self.bookmarktable.delete_bookmark.connect(self.delete_bookmark)
        self.bookmarktable.update_bookmark.connect(self.update_bookmark)

    @Slot(str, int, int)
    def goto_bookmark_handler(self, filename, line_number, col_number):
        self.load_bookmark.emit(filename, line_number, '',
                                None, True, col_number - 1)

    def get_data(self):
        pass

    @Slot()
    def set_data(self):
        bookmarks = self._load_all_bookmarks()
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
