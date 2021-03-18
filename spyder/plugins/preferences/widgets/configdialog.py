# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

from spyder.config.base import _, load_lang_conf
from spyder.config.manager import CONF
from spyder.utils.icon_manager import ima

from qtpy.QtCore import QSize, Qt, Signal, Slot
from qtpy.QtWidgets import (QDialog, QDialogButtonBox, QHBoxLayout,
                            QListView, QListWidget, QListWidgetItem,
                            QPushButton, QScrollArea, QSplitter,
                            QStackedWidget, QVBoxLayout)


class ConfigDialog(QDialog):
    """Spyder configuration ('Preferences') dialog box"""

    # Signals
    check_settings = Signal()
    size_change = Signal(QSize)

    def __init__(self, parent=None):
        QDialog.__init__(self, parent)

        self.main = parent

        # Widgets
        self.pages_widget = QStackedWidget()
        self.pages_widget.setMinimumWidth(600)
        self.contents_widget = QListWidget()
        self.button_reset = QPushButton(_('Reset to defaults'))

        bbox = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Apply |
                                QDialogButtonBox.Cancel)
        self.apply_btn = bbox.button(QDialogButtonBox.Apply)
        self.ok_btn = bbox.button(QDialogButtonBox.Ok)

        # Widgets setup
        # Destroying the C++ object right after closing the dialog box,
        # otherwise it may be garbage-collected in another QThread
        # (e.g. the editor's analysis thread in Spyder), thus leading to
        # a segmentation fault on UNIX or an application crash on Windows
        self.setAttribute(Qt.WA_DeleteOnClose)
        self.setWindowTitle(_('Preferences'))
        self.setWindowIcon(ima.icon('configure'))
        self.contents_widget.setMovement(QListView.Static)
        self.contents_widget.setSpacing(1)
        self.contents_widget.setCurrentRow(0)
        self.contents_widget.setMinimumWidth(220)
        self.contents_widget.setMinimumHeight(400)

        # Layout
        hsplitter = QSplitter()
        hsplitter.addWidget(self.contents_widget)
        hsplitter.addWidget(self.pages_widget)
        hsplitter.setStretchFactor(0, 1)
        hsplitter.setStretchFactor(1, 2)

        btnlayout = QHBoxLayout()
        btnlayout.addWidget(self.button_reset)
        btnlayout.addStretch(1)
        btnlayout.addWidget(bbox)

        vlayout = QVBoxLayout()
        vlayout.addWidget(hsplitter)
        vlayout.addLayout(btnlayout)

        self.setLayout(vlayout)

        # Signals and slots
        if self.main:
            self.button_reset.clicked.connect(self.main.reset_spyder)
        self.pages_widget.currentChanged.connect(self.current_page_changed)
        self.contents_widget.currentRowChanged.connect(
                                             self.pages_widget.setCurrentIndex)
        bbox.accepted.connect(self.accept)
        bbox.rejected.connect(self.reject)
        bbox.clicked.connect(self.button_clicked)

        # Ensures that the config is present on spyder first run
        CONF.set('main', 'interface_language', load_lang_conf())

    def get_current_index(self):
        """Return current page index"""
        return self.contents_widget.currentRow()

    def set_current_index(self, index):
        """Set current page index"""
        self.contents_widget.setCurrentRow(index)

    def get_page(self, index=None):
        """Return page widget"""
        if index is None:
            widget = self.pages_widget.currentWidget()
        else:
            widget = self.pages_widget.widget(index)

        if widget:
            return widget.widget()

    def get_index_by_name(self, name):
        """Return page index by CONF_SECTION name."""
        for idx in range(self.pages_widget.count()):
            widget = self.pages_widget.widget(idx)
            widget = widget.widget()
            try:
                # New API
                section = widget.plugin.NAME
            except AttributeError:
                section = widget.CONF_SECTION

            if section == name:
                return idx
        else:
            return None

    @Slot()
    def accept(self):
        """Reimplement Qt method"""
        for index in range(self.pages_widget.count()):
            configpage = self.get_page(index)
            if not configpage.is_valid():
                return
            configpage.apply_changes()
        QDialog.accept(self)

    def button_clicked(self, button):
        if button is self.apply_btn:
            # Apply button was clicked
            configpage = self.get_page()
            if not configpage.is_valid():
                return
            configpage.apply_changes()

    def current_page_changed(self, index):
        widget = self.get_page(index)
        self.apply_btn.setVisible(widget.apply_callback is not None)
        self.apply_btn.setEnabled(widget.is_modified)

    def add_page(self, widget):
        self.check_settings.connect(widget.check_settings)
        widget.show_this_page.connect(lambda row=self.contents_widget.count():
                                      self.contents_widget.setCurrentRow(row))
        widget.apply_button_enabled.connect(self.apply_btn.setEnabled)
        scrollarea = QScrollArea(self)
        scrollarea.setWidgetResizable(True)
        scrollarea.setWidget(widget)
        self.pages_widget.addWidget(scrollarea)
        item = QListWidgetItem(self.contents_widget)
        try:
            item.setIcon(widget.get_icon())
        except TypeError:
            pass
        item.setText(widget.get_name())
        item.setFlags(Qt.ItemIsSelectable|Qt.ItemIsEnabled)
        item.setSizeHint(QSize(0, 25))

    def check_all_settings(self):
        """This method is called to check all configuration page settings
        after configuration dialog has been shown"""
        self.check_settings.emit()

    def resizeEvent(self, event):
        """
        Reimplement Qt method to be able to save the widget's size from the
        main application
        """
        QDialog.resizeEvent(self, event)
        self.size_change.emit(self.size())
