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
from spyder.dependencies import MANDATORY, OPTIONAL, PLUGIN
from spyder.utils.icon_manager import ima
from spyder.utils.palette import SpyderPalette


class DependenciesTreeWidget(QTreeWidget):

    def update_dependencies(self, dependencies):
        self.clear()
        headers = (_("Module"), _("Package name"), _(" Required "),
                   _(" Installed "), _("Provided features"))
        self.setHeaderLabels(headers)

        # Mandatory items
        mandatory_item = QTreeWidgetItem([_("Mandatory")])
        font = mandatory_item.font(0)
        font.setBold(True)
        mandatory_item.setFont(0, font)

        # Optional items
        optional_item = QTreeWidgetItem([_("Optional")])
        optional_item.setFont(0, font)

        # Spyder plugins
        spyder_plugins = QTreeWidgetItem([_("Spyder plugins")])
        spyder_plugins.setFont(0, font)

        self.addTopLevelItems([mandatory_item, optional_item, spyder_plugins])

        for dependency in sorted(dependencies,
                                 key=lambda x: x.modname.lower()):
            item = QTreeWidgetItem([dependency.modname,
                                    dependency.package_name,
                                    dependency.required_version,
                                    dependency.installed_version,
                                    dependency.features])
            # Format content
            if dependency.check():
                item.setIcon(0, ima.icon('dependency_ok'))
            elif dependency.kind == OPTIONAL:
                item.setIcon(0, ima.icon('dependency_warning'))
                item.setForeground(2, QColor(SpyderPalette.COLOR_WARN_1))
            else:
                item.setIcon(0, ima.icon('dependency_error'))
                item.setForeground(2, QColor(SpyderPalette.COLOR_ERROR_1))

            # Add to tree
            if dependency.kind == OPTIONAL:
                optional_item.addChild(item)
            elif dependency.kind == PLUGIN:
                spyder_plugins.addChild(item)
            else:
                mandatory_item.addChild(item)

        self.expandAll()

    def resize_columns_to_contents(self):
        for col in range(self.columnCount()):
            self.resizeColumnToContents(col)


class DependenciesDialog(QDialog):

    def __init__(self, parent):
        QDialog.__init__(self, parent)

        # Widgets
        self.label = QLabel(_("Optional modules are not required to run "
                              "Spyder but enhance its functions."))
        self.label2 = QLabel(_("<b>Note:</b> New dependencies or changed ones "
                               "will be correctly detected only after Spyder "
                               "is restarted."))
        self.treewidget = DependenciesTreeWidget(self)
        btn = QPushButton(_("Copy to clipboard"), )
        bbox = QDialogButtonBox(QDialogButtonBox.Ok)

        # Widget setup
        self.setWindowTitle("Spyder %s: %s" % (__version__,
                                               _("Dependencies")))
        self.setWindowIcon(ima.icon('tooloptions'))
        self.setModal(False)

        # Layout
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
        self.resize(860, 560)

        # Signals
        btn.clicked.connect(self.copy_to_clipboard)
        bbox.accepted.connect(self.accept)

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
    dependencies.add("IPython", "IPython", "Enhanced Python interpreter",
                     ">=20.0")
    dependencies.add("matplotlib", "matplotlib", "Interactive data plotting",
                     ">=1.0")
    dependencies.add("sympy", "sympy", "Symbolic Mathematics", ">=10.0",
                     kind=OPTIONAL)
    dependencies.add("foo", "foo", "Non-existent module", ">=1.0")
    dependencies.add("numpy", "numpy",  "Edit arrays in Variable Explorer",
                     ">=0.10", kind=OPTIONAL)

    from spyder.utils.qthelpers import qapplication
    app = qapplication()
    dlg = DependenciesDialog(None)
    dlg.set_data(dependencies.DEPENDENCIES)
    dlg.show()
    sys.exit(dlg.exec_())


if __name__ == '__main__':
    test()
