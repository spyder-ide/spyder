# -*- coding: utf-8 -*-
#
# Copyright © 2012 Jed Ludlow
# based loosley on pylintgui.py by Pierre Raybaut
# Licensed under the terms of the MIT License
# (see spyderlib/__init__.py for details)

"""Breakpoint widget"""

# pylint: disable=C0103
# pylint: disable=R0903
# pylint: disable=R0911
# pylint: disable=R0201

from spyderlib.qt.QtGui import (QWidget, QTableView, QItemDelegate,
                                QVBoxLayout, QMenu)
from spyderlib.qt.QtCore import (Qt, SIGNAL, QTextCodec,
                                 QModelIndex, QAbstractTableModel)
locale_codec = QTextCodec.codecForLocale()
from spyderlib.qt.compat import to_qvariant
import sys
import os.path as osp

# Local imports
from spyderlib.baseconfig import get_translation
from spyderlib.config import CONF
from spyderlib.utils.qthelpers import create_action, add_actions

_ = get_translation("p_breakpoints", dirname="spyderplugins")

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
    
class BreakpointDelegate(QItemDelegate):
    def __init__(self, parent=None):
        QItemDelegate.__init__(self, parent)

class BreakpointTableView(QTableView):
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
            self.emit(SIGNAL("edit_goto(QString,int,QString)"),
                               filename, int(line_number_str), '') 
        if index_clicked.column()==2:
            self.emit(SIGNAL("set_or_edit_conditional_breakpoint()")) 
                           
    def contextMenuEvent(self, event):
        index_clicked = self.indexAt(event.pos())
        actions = []
        self.popup_menu = QMenu(self)
        clear_all_breakpoints_action = create_action(self, 
            _("Clear breakpoints in all files"),
            triggered=lambda: self.emit(SIGNAL('clear_all_breakpoints()')))
        actions.append(clear_all_breakpoints_action)
        if self.model.breakpoints:
            filename = self.model.breakpoints[index_clicked.row()][0]
            lineno = int(self.model.breakpoints[index_clicked.row()][1])         
            clear_breakpoint_action = create_action(self,
                    _("Clear this breakpoint"),
                    triggered=lambda filename=filename, lineno=lineno: \
                    self.emit(SIGNAL('clear_breakpoint(QString,int)'),
                              filename, lineno))
            actions.insert(0,clear_breakpoint_action)

            edit_breakpoint_action = create_action(self,
                    _("Edit this breakpoint"),
                    triggered=lambda filename=filename, lineno=lineno: \
                    (self.emit(SIGNAL('edit_goto(QString,int,QString)'),
                              filename, lineno, ''),
                     self.emit(SIGNAL("set_or_edit_conditional_breakpoint()")))
                    )
            actions.append(edit_breakpoint_action)
        add_actions(self.popup_menu, actions)        
        self.popup_menu.popup(event.globalPos())
        event.accept()

class BreakpointWidget(QWidget):
    """
    Breakpoint widget
    """
    VERSION = '1.0.0'
    
    def __init__(self, parent):
        QWidget.__init__(self, parent)
        
        self.setWindowTitle("Breakpoints")        
        self.dictwidget = BreakpointTableView(self, 
                               self._load_all_breakpoints())
        layout = QVBoxLayout()
        layout.addWidget(self.dictwidget)
        self.setLayout(layout)
        self.connect(self.dictwidget, SIGNAL('clear_all_breakpoints()'),
                     lambda: self.emit(SIGNAL('clear_all_breakpoints()')))
        self.connect(self.dictwidget, SIGNAL('clear_breakpoint(QString,int)'),
                     lambda s1, lino: self.emit(
                     SIGNAL('clear_breakpoint(QString,int)'), s1, lino))
        self.connect(self.dictwidget, SIGNAL("edit_goto(QString,int,QString)"),
                     lambda s1, lino, s2: self.emit(
                     SIGNAL("edit_goto(QString,int,QString)"), s1, lino, s2))
        self.connect(self.dictwidget, SIGNAL('set_or_edit_conditional_breakpoint()'),
                     lambda: self.emit(SIGNAL('set_or_edit_conditional_breakpoint()')))    
                     
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

def test():
    """Run breakpoint widget test"""
    from spyderlib.utils.qthelpers import qapplication
    app = qapplication()
    widget = BreakpointWidget(None)
    widget.show()
    sys.exit(app.exec_())
    
if __name__ == '__main__':
    test()
