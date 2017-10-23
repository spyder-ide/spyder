# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""Module checking Spyder runtime dependencies"""

# Standard library imports
import sys

# Third party imports
from qtpy.compat import to_qvariant
from qtpy.QtCore import Qt, QModelIndex, QAbstractTableModel
from qtpy.QtGui import QColor
from qtpy.QtWidgets import (QApplication, QDialog, QDialogButtonBox,
                            QHBoxLayout, QItemDelegate, QLabel, QPushButton,
                            QTableView, QVBoxLayout)

# Local imports
from spyder import __version__
from spyder.config.base import _
from spyder.utils import icon_manager as ima


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
            from spyder.dependencies import Dependency
            status = dep.get_status()
            if status == Dependency.NOK:
                color = QColor(Qt.red)
                color.setAlphaF(.25)
                return to_qvariant(color)

    def reset(self):
        self.beginResetModel()
        self.endResetModel()


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
                                               _("Dependencies")))
        self.setWindowIcon(ima.icon('tooloptions'))
        self.setModal(True)

        self.view = DependenciesTableView(self, [])

        opt_mods = ['NumPy', 'Matplotlib', 'Pandas', 'SymPy', 'Cython']
        self.label = QLabel(_("Spyder depends on several Python modules to "
                              "provide the right functionality for all its "
                              "panes. The table below shows the required "
                              "and installed versions (if any) of all of "
                              "them.<br><br>"
                              "<b>Note</b>: You can safely use Spyder "
                              "without the following modules installed: "
                              "<b>%s</b> and <b>%s</b>.<br><br>"
                              "Please also note that new "
                              "dependencies or changed ones will be correctly "
                              "detected only after Spyder is restarted.")
                              % (', '.join(opt_mods[:-1]), opt_mods[-1]))
        self.label.setWordWrap(True)
        self.label.setAlignment(Qt.AlignJustify)
        self.label.setContentsMargins(5, 8, 12, 10)

        btn = QPushButton(_("Copy to clipboard"), )
        btn.clicked.connect(self.copy_to_clipboard)
        bbox = QDialogButtonBox(QDialogButtonBox.Ok)
        bbox.accepted.connect(self.accept)
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

    def exec_(self):
        self.show()
        # we need an explicit show() because resizeRowsToContents() does only
        # work correctly after the widget has been drawn. Without this the
        # dimensions are not known yet.
        self.view.resizeRowsToContents()
        super(DependenciesDialog, self).exec_()

    def set_data(self, dependencies):
        self.view.model.set_data(dependencies)
        self.view.adjust_columns()
        self.view.sortByColumn(0, Qt.DescendingOrder)
    
    def copy_to_clipboard(self):
        from spyder.dependencies import status
        QApplication.clipboard().setText(status())


def test():
    """Run dependency widget test"""
    from spyder import dependencies
    
    # Test sample
    dependencies.add("IPython", "Enhanced Python interpreter", ">=0.13")
    dependencies.add("matplotlib", "Interactive data plotting", ">=1.0")
    dependencies.add("sympy", "Symbolic Mathematics", ">=10.0")
    dependencies.add("foo", "Non-existent module", ">=1.0")
    
    from spyder.utils.qthelpers import qapplication
    app = qapplication()
    dlg = DependenciesDialog(None)
    dlg.set_data(dependencies.DEPENDENCIES)
    dlg.show()
    sys.exit(dlg.exec_())


if __name__ == '__main__':
    test()
