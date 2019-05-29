# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""Module checking Spyder runtime dependencies"""

# Standard library imports
import sys

# Third party imports
from qtpy.QtCore import Qt
from qtpy.QtGui import QColor
from qtpy.QtWidgets import (QApplication, QDialog, QDialogButtonBox,
                            QHBoxLayout, QVBoxLayout, QLabel, QPushButton,
                            QTreeWidget, QTreeWidgetItem)

# Local imports
from spyder import __version__
from spyder.config.base import _
from spyder.utils import icon_manager as ima


class DependenciesTreeWidget(QTreeWidget):

    def update_dependencies(self, dependencies):
        self.clear()
        headers = (_("Module"), _(" Required "),
                   _(" Installed "), _("Provided features"))
        self.setHeaderLabels(headers)
        mandatory_item = QTreeWidgetItem(["Mandatory"])
        font = mandatory_item.font(0)
        font.setBold(True)
        mandatory_item.setFont(0, font)
        optional_item = QTreeWidgetItem(["Optional"])
        optional_item.setFont(0, font)
        self.addTopLevelItems([mandatory_item, optional_item])

        for dependency in dependencies:
            item = QTreeWidgetItem([dependency.modname,
                                    dependency.required_version,
                                    dependency.installed_version,
                                    dependency.features])
            if dependency.check():
                item.setIcon(0, ima.icon('dependency_ok'))
            elif dependency.optional:
                item.setIcon(0, ima.icon('dependency_warning'))
                item.setForeground(2, QColor('#ff6a00'))
            else:
                item.setIcon(0, ima.icon('dependency_error'))
                item.setForeground(2, QColor(Qt.darkRed))
            if dependency.optional:
                optional_item.addChild(item)
            else:
                mandatory_item.addChild(item)
        self.expandAll()

    def resize_columns_to_contents(self):
        for col in range(self.columnCount()):
            self.resizeColumnToContents(col)


class DependenciesDialog(QDialog):
    def __init__(self, parent):
        QDialog.__init__(self, parent)
        self.setWindowTitle("Spyder %s: %s" % (__version__,
                                               _("Dependencies")))
        self.setWindowIcon(ima.icon('tooloptions'))
        self.setModal(True)

        self.treewidget = DependenciesTreeWidget(self)

        self.label = QLabel(_("Optional modules are not required to run "
                              "Spyder but enhance its functions."))
        self.label2 = QLabel(_("<b>Note:</b> New dependencies or changed ones "
                               "will be correctly detected only after Spyder "
                               "is restarted."))

        btn = QPushButton(_("Copy to clipboard"), )
        btn.clicked.connect(self.copy_to_clipboard)
        bbox = QDialogButtonBox(QDialogButtonBox.Ok)
        bbox.accepted.connect(self.accept)
        hlayout = QHBoxLayout()
        hlayout.addWidget(btn)
        hlayout.addStretch()
        hlayout.addWidget(bbox)

        vlayout = QVBoxLayout()
        vlayout.addWidget(self.treewidget)
        vlayout.addWidget(self.label)
        vlayout.addWidget(self.label2)
        vlayout.addLayout(hlayout)

        self.setLayout(vlayout)
        self.resize(840, 560)

    def set_data(self, dependencies):
        self.treewidget.update_dependencies(dependencies)
        self.treewidget.resize_columns_to_contents()

    def copy_to_clipboard(self):
        from spyder.dependencies import status
        QApplication.clipboard().setText(status())


def test():
    """Run dependency widget test"""
    from spyder import dependencies

    # Test sample
    dependencies.add("IPython", "Enhanced Python interpreter", ">=20.0")
    dependencies.add("matplotlib", "Interactive data plotting", ">=1.0")
    dependencies.add("sympy", "Symbolic Mathematics", ">=10.0", optional=True)
    dependencies.add("foo", "Non-existent module", ">=1.0")
    dependencies.add("numpy", "Edit arrays in Variable Explorer", ">=0.10",
                     optional=True)

    from spyder.utils.qthelpers import qapplication
    app = qapplication()
    dlg = DependenciesDialog(None)
    dlg.set_data(dependencies.DEPENDENCIES)
    dlg.show()
    sys.exit(dlg.exec_())


if __name__ == '__main__':
    test()
