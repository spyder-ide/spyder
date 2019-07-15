# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""Warnings/errors widget"""

# pylint: disable=C0103
# pylint: disable=R0903
# pylint: disable=R0911
# pylint: disable=R0201

# Standard library imports
import sys

# Third party imports
from qtpy.compat import to_qvariant
from qtpy.QtCore import (QAbstractTableModel, QModelIndex, Qt, Signal,
                         QSortFilterProxyModel)
from qtpy.QtWidgets import (QTableView, QHBoxLayout, QStyledItemDelegate,
                            QVBoxLayout, QWidget, QAbstractItemView,
                            QHeaderView)

# Local imports
from spyder.config.base import get_translation
from spyder.utils.qthelpers import create_plugin_layout
from spyder.plugins.completion.languageserver import DiagnosticSeverity
from spyder.utils import icon_manager as ima

# This is needed for testing this module as a stand alone script
try:
    _ = get_translation("warnings", "spyder_warnings")
except KeyError:
    import gettext
    _ = gettext.gettext


class WarningTableModel(QAbstractTableModel):
    """
    Table model for Warnings/errors list

    """
    def __init__(self, parent, data):
        QAbstractTableModel.__init__(self, parent)
        if data is None:
            data = {}
        self._data = None
        self.warnings = None
        self.set_data(data)

    def set_data(self, data):
        """Set model data"""
        self._data = data
        self.warnings = []
        if data:
            for item in data:
                self.warnings.append((item[2], item[1], item[4], item[3],
                                      item[0]))
        self.reset()

    def rowCount(self, qindex=QModelIndex()):
        """Array row number"""
        return len(self.warnings)

    def columnCount(self, qindex=QModelIndex()):
        """Array column count"""
        return 5

    def headerData(self, section, orientation, role=Qt.DisplayRole):
        """Overriding method headerData"""
        if role != Qt.DisplayRole:
            return to_qvariant()
        i_column = int(section)
        if orientation == Qt.Horizontal:
            headers = ("", _("Code"), _("Line"), _("Comment"), _("Source"))
            return to_qvariant(headers[i_column])
        else:
            return to_qvariant()

    def get_value(self, index):
        """Return current value"""
        return self.warnings[index.row()][index.column()]

    def data(self, index, role=Qt.DisplayRole):
        """Return data at table index"""
        if not index.isValid():
            return to_qvariant()
        if role == Qt.DisplayRole:
            value = self.get_value(index)
            return to_qvariant(value)
        elif role == Qt.TextAlignmentRole:
            if index.column() == 2:
                # Align line number right
                return to_qvariant(int(Qt.AlignRight | Qt.AlignVCenter))
            else:
                return to_qvariant(int(Qt.AlignLeft | Qt.AlignVCenter))

    def reset(self):
        self.beginResetModel()
        self.endResetModel()


class WarningIconDelegate(QStyledItemDelegate):
    def __init__(self, parent):
        super(WarningIconDelegate, self).__init__(parent)
        self.parent = parent
        self.icons = {
            DiagnosticSeverity.ERROR: 'error',
            DiagnosticSeverity.WARNING: 'warning',
            DiagnosticSeverity.INFORMATION: 'information',
            DiagnosticSeverity.HINT: 'hint',
        }

    def paint(self, painter, option, index):
        idx = self.parent.getIcon(index)
        icon = ima.icon(self.icons[idx])
        icon.paint(painter, option.rect, Qt.AlignCenter)


class WarningTableView(QTableView):
    edit_goto = Signal(str, int, str)

    def __init__(self, parent, data):
        QTableView.__init__(self, parent)

        self.model = WarningTableModel(self, data)
        self.sortmodel = QSortFilterProxyModel()
        self.sortmodel.setSourceModel(self.model)
        self.setModel(self.sortmodel)
        self.setup_table()
        self.parent = parent

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
        delegate = WarningIconDelegate(self)
        self.setItemDelegateForColumn(0, delegate)
        self.adjust_columns()

    def adjust_columns(self):
        """Resize four first columns to contents"""
        for col in range(4):
            self.resizeColumnToContents(col)

    def onClick(self, item):
        """Double-click event"""
        original_item = self.sortmodel.mapToSource(item)
        data = self.model.warnings[original_item.row()]
        self.edit_goto.emit(self.parent.get_filename(), data[2], '')

    def getIcon(self, item):
        original_item = self.sortmodel.mapToSource(item)
        data = self.model.warnings[original_item.row()]
        return data[0]


class WarningWidget(QWidget):
    """
    Warnings/errors widget
    """
    VERSION = '1.0.0'
    edit_goto = Signal(str, int, str)

    def __init__(self, parent, options_button=None):
        QWidget.__init__(self, parent)
        self.parent = parent

        self.setWindowTitle("Warnings/errors")
        self.warningtable = WarningTableView(self, self._load_all_warnings())
        if options_button:
            btn_layout = QHBoxLayout()
            btn_layout.setAlignment(Qt.AlignLeft)
            btn_layout.addStretch()
            btn_layout.addWidget(options_button, Qt.AlignRight)
            layout = create_plugin_layout(btn_layout, self.warningtable)
        else:
            layout = QVBoxLayout()
            layout.addWidget(self.warningtable)
        self.setLayout(layout)
        self.warningtable.edit_goto.connect(
                        lambda s1, lino, s2: self.edit_goto.emit(s1, lino, s2))

    def _load_all_warnings(self):
        if self.parent:
            return self.parent.get_warning_list()

    def get_data(self):
        pass

    def get_filename(self):
        return self.parent.get_filename()

    def set_data(self):
        res = self._load_all_warnings()
        self.warningtable.model.set_data(res)
        self.warningtable.adjust_columns()


# =============================================================================
# Tests
# =============================================================================
def test():
    """Run warnings/errors widget test"""
    from spyder.utils.qthelpers import qapplication
    app = qapplication()
    widget = WarningWidget(None)
    widget.show()
    sys.exit(app.exec_())


if __name__ == '__main__':
    test()
