# -*- coding: utf-8 -*-
#
# Copyright © 2013 Pierre Raybaut
# Licensed under the terms of the MIT License
# (see spyderlib/__init__.py for details)

"""Module checking Spyder optional runtime dependencies"""

from spyderlib.qt.QtGui import (QDialog, QTableView, QItemDelegate,
                                QVBoxLayout, QHBoxLayout, QPushButton,
                                QApplication)
from spyderlib.qt.QtCore import Qt, QModelIndex, QAbstractTableModel, SIGNAL
from spyderlib.qt.compat import to_qvariant
import sys

# Local imports
from spyderlib.baseconfig import _
from spyderlib.utils.qthelpers import get_icon
from spyderlib import __version__


class DependenciesTableModel(QAbstractTableModel):
    def __init__(self, parent, dependencies):
        QAbstractTableModel.__init__(self, parent)
        self.dependencies = None
        self.set_data(dependencies)
    
    def set_data(self, dependencies):
        """Set model data"""
        self.dependencies = dependencies
        self.reset()   
    
    def rowCount(self, qindex=QModelIndex()):
        """Array row number"""
        return len(self.dependencies)
    
    def columnCount(self, qindex=QModelIndex()):
        """Array column count"""
        return 4

    def sort(self, column, order=Qt.DescendingOrder):
        """Overriding sort method"""
        if column == 0:
            self.dependencies.sort(key=lambda dep: getattr(dep, 'modname'))
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
            headers = (_("Module"), _("Version"),
                       _("Status"), _("Related features"))
            return to_qvariant( headers[i_column] )
        else:
            return to_qvariant()
    
    def get_value(self, index):
        """Return current value"""
        dep = self.dependencies[index.row()]
        return (dep.modname, dep.version,
                dep.get_status(), dep.features)[index.column()]
    
    def data(self, index, role=Qt.DisplayRole):
        """Return data at table index"""
        if not index.isValid():
            return to_qvariant()
        if role == Qt.DisplayRole:
            if index.column() == 0:
                value = self.get_value(index)
                return to_qvariant(value)
            else:
                value = self.get_value(index)
                return to_qvariant(value)
        elif role == Qt.TextAlignmentRole:
            return to_qvariant(int(Qt.AlignLeft|Qt.AlignVCenter))
    
class DependenciesDelegate(QItemDelegate):
    def __init__(self, parent=None):
        QItemDelegate.__init__(self, parent)

class DependenciesTableView(QTableView):
    def __init__(self, parent, data):
        QTableView.__init__(self, parent)
        self.model = DependenciesTableModel(self, data)
        self.setModel(self.model)
        self.delegate = DependenciesDelegate(self)
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

class DependenciesDialog(QDialog):
    def __init__(self, parent):
        QDialog.__init__(self, parent)
        self.setWindowTitle("Spyder %s: %s" % (__version__,
                                               _("Optional Dependencies")))
        self.setWindowIcon(get_icon('advanced.png'))
        self.setModal(True)
        self.view = DependenciesTableView(self, [])
        vlayout = QVBoxLayout()
        vlayout.addWidget(self.view)
        hlayout = QHBoxLayout()
        btn = QPushButton(_("Copy to clipboard"), )
        self.connect(btn, SIGNAL('clicked()'), self.copy_to_clipboard)
        hlayout.addWidget(btn)
        hlayout.addStretch()
        vlayout.addLayout(hlayout)
        self.setLayout(vlayout)
        self.resize(500, 300)
        
    def set_data(self, dependencies):
        self.view.model.set_data(dependencies)
        self.view.adjust_columns()
        self.view.sortByColumn(0, Qt.DescendingOrder)
    
    def copy_to_clipboard(self):
        from spyderlib.dependencies import status
        QApplication.clipboard().setText(status())


def test():
    """Run dependency widget test"""
    from spyderlib import dependencies
    
    # Test sample
    dependencies.add("IPython", "Enhanced Python interpreter", "0.13")    
    
    from spyderlib.utils.qthelpers import qapplication
    app = qapplication()
    dlg = DependenciesDialog(None)
    dlg.set_data(dependencies.DEPENDENCIES)
    dlg.show()
    sys.exit(dlg.exec_())


if __name__ == '__main__':
    test()
