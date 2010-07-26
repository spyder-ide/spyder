# -*- coding: utf-8 -*-
#
# Copyright © 2009 Pierre Raybaut
# Licensed under the terms of the MIT License
# (see spyderlib/__init__.py for details)

"""Configuration dialog"""

from spyderlib.utils.qthelpers import get_icon

from PyQt4.QtGui import (QWidget, QCheckBox, QDialog, QGroupBox, QListWidget,
                         QListWidgetItem, QPushButton, QVBoxLayout, QLabel,
                         QLineEdit, QDateTimeEdit, QSpinBox, QGridLayout,
                         QStackedWidget, QListView, QHBoxLayout,
                         QDialogButtonBox, QMainWindow)
from PyQt4.QtCore import Qt, QDate, QSize, SIGNAL, SLOT


class Sample2():
    def setup_page(self):
        packagesGroup = QGroupBox(self.tr("Look for packages"))

        nameLabel = QLabel(self.tr("Name:"))
        nameEdit = QLineEdit()

        dateLabel = QLabel(self.tr("Released after:"))
        dateEdit = QDateTimeEdit(QDate.currentDate())

        releasesCheckBox = QCheckBox(self.tr("Releases"))
        upgradesCheckBox = QCheckBox(self.tr("Upgrades"))

        hitsSpinBox = QSpinBox()
        hitsSpinBox.setPrefix(self.tr("Return up to "))
        hitsSpinBox.setSuffix(self.tr(" results"))
        hitsSpinBox.setSpecialValueText(self.tr("Return only the first result"))
        hitsSpinBox.setMinimum(1)
        hitsSpinBox.setMaximum(100)
        hitsSpinBox.setSingleStep(10)

        startQueryButton = QPushButton(self.tr("Start query"))

        packagesLayout = QGridLayout()
        packagesLayout.addWidget(nameLabel, 0, 0)
        packagesLayout.addWidget(nameEdit, 0, 1)
        packagesLayout.addWidget(dateLabel, 1, 0)
        packagesLayout.addWidget(dateEdit, 1, 1)
        packagesLayout.addWidget(releasesCheckBox, 2, 0)
        packagesLayout.addWidget(upgradesCheckBox, 3, 0)
        packagesLayout.addWidget(hitsSpinBox, 4, 0, 1, 2)
        packagesGroup.setLayout(packagesLayout)

        vlayout = QVBoxLayout()
        vlayout.addWidget(packagesGroup)
        vlayout.addSpacing(12)
        vlayout.addWidget(startQueryButton)
        vlayout.addStretch(1)

        self.setLayout(vlayout)


class ConfigPage(QWidget):
    """Configuration page base class"""
    def __init__(self, parent, apply_callback=None):
        QWidget.__init__(self, parent)
        self.apply_callback = apply_callback
        
    def initialize(self):
        """
        Initialize configuration page:
            * setup GUI widgets
            * load settings and change widgets accordingly
        """
        self.setup_page()
        self.load_from_conf()
        
    def get_name(self):
        """Return page name"""
        raise NotImplementedError
    
    def get_icon(self):
        """Return page icon"""
        raise NotImplementedError
    
    def setup_page(self):
        """Setup configuration page widget"""
        raise NotImplementedError
    
    def apply_changes(self):
        """Apply changes callback"""
        self.save_to_conf()
        self.apply_callback()
    
    def load_from_conf(self):
        """Load settings from configuration file"""
        raise NotImplementedError
    
    def save_to_conf(self):
        """Save settings to configuration file"""
        raise NotImplementedError


class ConfigDialog(QDialog):
    def __init__(self, parent=None):
        super(ConfigDialog, self).__init__(parent)

        self.contents_widget = QListWidget()
        self.contents_widget.setMovement(QListView.Static)
        self.contents_widget.setMaximumWidth(128)
        self.contents_widget.setSpacing(1)

        bbox = QDialogButtonBox(QDialogButtonBox.Ok|QDialogButtonBox.Apply
                                     |QDialogButtonBox.Cancel)
        self.apply_btn = bbox.button(QDialogButtonBox.Apply)
        self.connect(bbox, SIGNAL("accepted()"), SLOT("accept()"))
        self.connect(bbox, SIGNAL("rejected()"), SLOT("reject()"))
        self.connect(bbox, SIGNAL("clicked(QAbstractButton*)"),
                     self.button_clicked)

        self.pages_widget = QStackedWidget()
        self.connect(self.pages_widget, SIGNAL("currentChanged(int)"),
                     self.current_page_changed)

        self.connect(self.contents_widget, SIGNAL("currentRowChanged(int)"),
                     self.pages_widget.setCurrentIndex)
        self.contents_widget.setCurrentRow(0)

        hlayout = QHBoxLayout()
        hlayout.addWidget(self.contents_widget)
        hlayout.addWidget(self.pages_widget, 1)

        btnlayout = QHBoxLayout()
        btnlayout.addStretch(1)
        btnlayout.addWidget(bbox)

        vlayout = QVBoxLayout()
        vlayout.addLayout(hlayout)
        vlayout.addStretch(1)
        vlayout.addSpacing(12)
        vlayout.addLayout(btnlayout)

        self.setLayout(vlayout)

        self.setWindowTitle(self.tr("Preferences"))
        self.setWindowIcon(get_icon("configure.png"))
        
    def button_clicked(self, button):
        if button is self.apply_btn:
            # Apply button was clicked
            self.pages_widget.currentWidget().apply_changes()
            
    def current_page_changed(self, index):
        widget = self.pages_widget.widget(index)
        self.apply_btn.setEnabled(widget.apply_callback is not None)
        
    def add_page(self, plugin):
        widget = plugin.create_configwidget(self)
        if widget is not None:
            self.pages_widget.addWidget(widget)
            item = QListWidgetItem(self.contents_widget)
            item.setIcon(widget.get_icon())
            item.setText(widget.get_name())
            item.setFlags(Qt.ItemIsSelectable|Qt.ItemIsEnabled)
            item.setSizeHint(QSize(0, 25))


def test():
    from spyderlib.utils.qthelpers import qapplication
    _app = qapplication()
    from spyderlib.plugins.editor import Editor
    from spyderlib.plugins.externalconsole import ExternalConsole
    
    class FakeSpyderApp(QMainWindow):
        def __init__(self):
            QMainWindow.__init__(self)
            self.inspector = None
    
    main = FakeSpyderApp()
    editor = Editor(main)
    extconsole = ExternalConsole(main, False)
    
    dialog = ConfigDialog()
    for plugin in (editor, extconsole):
        dialog.add_page(plugin)
    dialog.exec_()
    
if __name__ == "__main__":
    test()
