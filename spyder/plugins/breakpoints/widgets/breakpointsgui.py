# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# based loosley on pylintgui.py by Pierre Raybaut
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""Breakpoint widget"""

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
from qtpy.QtCore import (QAbstractTableModel, QModelIndex, QTextCodec, Qt,
                         Signal)
from qtpy.QtWidgets import (QItemDelegate, QMenu, QTableView, QHBoxLayout,
                            QVBoxLayout, QWidget)

# Local imports
from spyder.config.base import get_translation
from spyder.config.main import CONF
from spyder.utils.qthelpers import (add_actions, create_action,
                                    create_plugin_layout)

# This is needed for testing this module as a stand alone script
try:
    _ = get_translation("breakpoints", "spyder_breakpoints")
except KeyError as error:
    import gettext
    _ = gettext.gettext


locale_codec = QTextCodec.codecForLocale()


class BreakpointTableModel(QAbstractTableModel):
    """
    Table model for breakpoints dictionary

    """
    def __init__(self, parent, data):
        QAbstractTableModel.__init__(self, parent)
        if data is None:
            data = {}
        self._data = None
        self.breakpoints = None
        self.set_data(data)

    def set_data(self, data):
        """Set model data"""
        self._data = data
        keys = list(data.keys())
        self.breakpoints = []
        for key in keys:
            bp_list = data[key]
            if bp_list:
                for item in data[key]:
                    self.breakpoints.append((key, item[0], item[1], ""))
        self.reset()

    def rowCount(self, qindex=QModelIndex()):
        """Array row number"""
        return len(self.breakpoints)

    def columnCount(self, qindex=QModelIndex()):
        """Array column count"""
        return 4

    def sort(self, column, order=Qt.DescendingOrder):
        """Overriding sort method"""
        if column == 0:
            self.breakpoints.sort(
                key=lambda breakpoint: breakpoint[1])
            self.breakpoints.sort(
                key=lambda breakpoint: osp.basename(breakpoint[0]))
        elif column == 1:
            pass
        elif column == 2:
            pass
        elif column == 3:
            pass
        self.reset()

    def headerData(self, section, orientation, role=Qt.DisplayRole):
        """Overriding method headerData"""
        if role != Qt.DisplayRole:
            return to_qvariant()
        i_column = int(section)
        if orientation == Qt.Horizontal:
            headers = (_("File"), _("Line"), _("Condition"), "")
            return to_qvariant( headers[i_column] )
        else:
            return to_qvariant()

    def get_value(self, index):
        """Return current value"""
        return self.breakpoints[index.row()][index.column()]

    def data(self, index, role=Qt.DisplayRole):
        """Return data at table index"""
        if not index.isValid():
            return to_qvariant()
        if role == Qt.DisplayRole:
            if index.column() == 0:
                value = osp.basename(self.get_value(index))
                return to_qvariant(value)
            else:
                value = self.get_value(index)
                return to_qvariant(value)
        elif role == Qt.TextAlignmentRole:
            return to_qvariant(int(Qt.AlignLeft|Qt.AlignVCenter))
        elif role == Qt.ToolTipRole:
            if index.column() == 0:
                value = self.get_value(index)
                return to_qvariant(value)
            else:
                return to_qvariant()

    def reset(self):
        self.beginResetModel()
        self.endResetModel()


class BreakpointDelegate(QItemDelegate):
    def __init__(self, parent=None):
        QItemDelegate.__init__(self, parent)


class BreakpointTableView(QTableView):
    edit_goto = Signal(str, int, str)
    clear_breakpoint = Signal(str, int)
    clear_all_breakpoints = Signal()
    set_or_edit_conditional_breakpoint = Signal()

    def __init__(self, parent, data):
        QTableView.__init__(self, parent)
        self.model = BreakpointTableModel(self, data)
        self.setModel(self.model)
        self.delegate = BreakpointDelegate(self)
        self.setItemDelegate(self.delegate)

        self.setup_table()

    def setup_table(self):
        """Setup table"""
        self.horizontalHeader().setStretchLastSection(True)
        self.adjust_columns()
        self.columnAt(0)
        # Sorting columns
        self.setSortingEnabled(False)
        self.sortByColumn(0, Qt.DescendingOrder)

    def adjust_columns(self):
        """Resize three first columns to contents"""
        for col in range(3):
            self.resizeColumnToContents(col)

    def mouseDoubleClickEvent(self, event):
        """Reimplement Qt method"""
        index_clicked = self.indexAt(event.pos())
        if self.model.breakpoints:
            filename = self.model.breakpoints[index_clicked.row()][0]
            line_number_str = self.model.breakpoints[index_clicked.row()][1]
            self.edit_goto.emit(filename, int(line_number_str), '')
        if index_clicked.column()==2:
            self.set_or_edit_conditional_breakpoint.emit()

    def contextMenuEvent(self, event):
        index_clicked = self.indexAt(event.pos())
        actions = []
        self.popup_menu = QMenu(self)
        clear_all_breakpoints_action = create_action(self,
            _("Clear breakpoints in all files"),
            triggered=lambda: self.clear_all_breakpoints.emit())
        actions.append(clear_all_breakpoints_action)
        if self.model.breakpoints:
            filename = self.model.breakpoints[index_clicked.row()][0]
            lineno = int(self.model.breakpoints[index_clicked.row()][1])
            # QAction.triggered works differently for PySide and PyQt
            if not API == 'pyside':
                clear_slot = lambda _checked, filename=filename, lineno=lineno: \
                    self.clear_breakpoint.emit(filename, lineno)
                edit_slot = lambda _checked, filename=filename, lineno=lineno: \
                    (self.edit_goto.emit(filename, lineno, ''),
                     self.set_or_edit_conditional_breakpoint.emit())
            else:
                clear_slot = lambda filename=filename, lineno=lineno: \
                    self.clear_breakpoint.emit(filename, lineno)
                edit_slot = lambda filename=filename, lineno=lineno: \
                    (self.edit_goto.emit(filename, lineno, ''),
                     self.set_or_edit_conditional_breakpoint.emit())

            clear_breakpoint_action = create_action(self,
                    _("Clear this breakpoint"),
                    triggered=clear_slot)
            actions.insert(0,clear_breakpoint_action)

            edit_breakpoint_action = create_action(self,
                    _("Edit this breakpoint"),
                    triggered=edit_slot)
            actions.append(edit_breakpoint_action)
        add_actions(self.popup_menu, actions)
        self.popup_menu.popup(event.globalPos())
        event.accept()


class BreakpointWidget(QWidget):
    """
    Breakpoint widget
    """
    VERSION = '1.0.0'
    clear_all_breakpoints = Signal()
    set_or_edit_conditional_breakpoint = Signal()
    clear_breakpoint = Signal(str, int)
    edit_goto = Signal(str, int, str)

    def __init__(self, parent, options_button=None):
        QWidget.__init__(self, parent)

        self.setWindowTitle("Breakpoints")
        self.dictwidget = BreakpointTableView(self,
                               self._load_all_breakpoints())
        if options_button:
            btn_layout = QHBoxLayout()
            btn_layout.setAlignment(Qt.AlignLeft)
            btn_layout.addStretch()
            btn_layout.addWidget(options_button, Qt.AlignRight)
            layout = create_plugin_layout(btn_layout, self.dictwidget)
        else:
            layout = QVBoxLayout()
            layout.addWidget(self.dictwidget)
        self.setLayout(layout)
        self.dictwidget.clear_all_breakpoints.connect(
                                     lambda: self.clear_all_breakpoints.emit())
        self.dictwidget.clear_breakpoint.connect(
                         lambda s1, lino: self.clear_breakpoint.emit(s1, lino))
        self.dictwidget.edit_goto.connect(
                        lambda s1, lino, s2: self.edit_goto.emit(s1, lino, s2))
        self.dictwidget.set_or_edit_conditional_breakpoint.connect(
                        lambda: self.set_or_edit_conditional_breakpoint.emit())

    def _load_all_breakpoints(self):
        bp_dict = CONF.get('run', 'breakpoints', {})
        for filename in list(bp_dict.keys()):
            if not osp.isfile(filename):
                bp_dict.pop(filename)
        return bp_dict

    def get_data(self):
        pass

    def set_data(self):
        bp_dict = self._load_all_breakpoints()
        self.dictwidget.model.set_data(bp_dict)
        self.dictwidget.adjust_columns()
        self.dictwidget.sortByColumn(0, Qt.DescendingOrder)


#==============================================================================
# Tests
#==============================================================================
def test():
    """Run breakpoint widget test"""
    from spyder.utils.qthelpers import qapplication
    app = qapplication()
    widget = BreakpointWidget(None)
    widget.show()
    sys.exit(app.exec_())


if __name__ == '__main__':
    test()
