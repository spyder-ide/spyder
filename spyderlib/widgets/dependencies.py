# -*- coding: utf-8 -*-
#
# Copyright © 2013 Pierre Raybaut
# Licensed under the terms of the MIT License
# (see spyderlib/__init__.py for details)

"""Module checking Spyder optional runtime dependencies"""

from spyderlib.qt.QtGui import (QDialog, QTableView, QItemDelegate, QColor,
                                QVBoxLayout, QHBoxLayout, QPushButton,
                                QApplication, QLabel, QDialogButtonBox)
from spyderlib.qt.QtCore import (Qt, QModelIndex, QAbstractTableModel, SIGNAL,
                                 SLOT)
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
            headers = (_("Module"), _(" Required "),
                       _(" Installed "), _("Provided features"))
            return to_qvariant( headers[i_column] )
        else:
            return to_qvariant()
    
    def get_value(self, index):
        """Return current value"""
        dep = self.dependencies[index.row()]
        return (dep.modname, dep.required_version,
                dep.get_installed_version(), dep.features)[index.column()]
    
    def data(self, index, role=Qt.DisplayRole):
        """Return data at table index"""
        if not index.isValid():
            return to_qvariant()
        dep = self.dependencies[index.row()]
        if role == Qt.DisplayRole:
            if index.column() == 0:
                value = self.get_value(index)
                return to_qvariant(value)
            else:
                value = self.get_value(index)
                return to_qvariant(value)
        elif role == Qt.TextAlignmentRole:
            return to_qvariant(int(Qt.AlignLeft|Qt.AlignVCenter))
        elif role == Qt.BackgroundColorRole:
            from spyderlib.dependencies import Dependency
            status = dep.get_status()
            if status == Dependency.NOK:
                color = QColor(Qt.red)
                color.setAlphaF(.25)
                return to_qvariant(color)


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

        important_mods = ['rope', 'pyflakes', 'IPython', 'matplotlib']
        self.label = QLabel(_("Spyder depends on several Python modules to "
                              "provide additional functionality for its "
                              "plugins. The table below shows the required "
                              "and installed versions (if any) of all of "
                              "them.<br><br>"
                              "Although Spyder can work without any of these "
                              "modules, it's strongly recommended that at "
                              "least you try to install <b>%s</b> and "
                              "<b>%s</b> to have a much better experience.")
                              % (', '.join(important_mods[:-1]),
                                 important_mods[-1]))
        self.label.setWordWrap(True)
        self.label.setAlignment(Qt.AlignJustify)
        self.label.setContentsMargins(5, 8, 12, 10)

        btn = QPushButton(_("Copy to clipboard"), )
        self.connect(btn, SIGNAL('clicked()'), self.copy_to_clipboard)
        bbox = QDialogButtonBox(QDialogButtonBox.Ok)
        self.connect(bbox, SIGNAL("accepted()"), SLOT("accept()"))
        hlayout = QHBoxLayout()
        hlayout.addWidget(btn)
        hlayout.addStretch()
        hlayout.addWidget(bbox)

        vlayout = QVBoxLayout()
        vlayout.addWidget(self.label)
        vlayout.addWidget(self.view)
        vlayout.addLayout(hlayout)

        self.setLayout(vlayout)
        self.resize(630, 420)
        
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
    dependencies.add("IPython", "Enhanced Python interpreter", ">=0.13")
    dependencies.add("matplotlib", "Interactive data plotting", ">=1.0")
    dependencies.add("sympy", "Symbolic Mathematics", ">=10.0")
    dependencies.add("foo", "Non-existent module", ">=1.0")
    
    from spyderlib.utils.qthelpers import qapplication
    app = qapplication()
    dlg = DependenciesDialog(None)
    dlg.set_data(dependencies.DEPENDENCIES)
    dlg.show()
    sys.exit(dlg.exec_())


if __name__ == '__main__':
    test()
