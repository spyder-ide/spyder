# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""
File assoaciations widget for use in global and project preferences.
"""

# Standard library imports
from __future__ import print_function
import os
import os.path as osp
import pwd
import sys

# Third party imports
from qtpy.compat import getopenfilename
from qtpy.QtCore import (Signal, Slot, QEvent, QFileInfo, QObject, QRegExp,
                         QSize, Qt)
from qtpy.QtGui import (QIcon, QRegExpValidator, QTextCursor)
from qtpy.QtWidgets import (QDialog, QHBoxLayout, QLabel, QLineEdit,
                            QListWidget, QListWidgetItem, QVBoxLayout,
                            QMainWindow, QListWidgetItem, QInputDialog)

# Local imports
from spyder.config.base import _
from spyder.py3compat import iteritems, to_text_string
from spyder.config.utils import is_ubuntu
from spyder.utils import icon_manager as ima
from spyder.utils.stringmatching import get_search_scores
from spyder.widgets.helperwidgets import HelperToolButton, HTMLDelegate
from spyder.config.main import CONF


# Third party imports
from qtpy.QtCore import Qt
from qtpy.QtGui import QCursor
from qtpy.QtWidgets import (QApplication, QGroupBox, QLabel, QVBoxLayout, QListWidget,
                            QPushButton, QHBoxLayout, QWidget, QTabWidget,
                            QDialogButtonBox)

# Local imports
from spyder.api.preferences import PluginConfigPage
from spyder.config.base import _


def get_mac_application_icon_path(fpath):
    """"""
    import plistlib
    info_path = os.path.join(fpath, 'Contents', 'Info.plist')

    # with open(info_path, 'rb') as fp:
    try:
        pl = plistlib.readPlist(info_path)
    except:
        pl = {}

    icon_file = pl.get('CFBundleIconFile')
    icon_path = None
    if icon_file:
        icon_path = os.path.join(fpath, 'Contents', 'Resources', icon_file)
        if not os.path.isfile(icon_path):
            icon_path = None

    return icon_path


def get_username():
    """"""
    return pwd.getpwuid(os.getuid())[0]


def get_mac_applications():
    """"""
    apps = {}
    roots = ['/Applications', '/Users/{}/Applications/'.format(get_username())]
    sub_roots = []
    for root in roots:
        for item in os.listdir(root):
            if not item.endswith('.app') and os.path.isdir(item):
                sub_roots.append(os.path.join(root, item))

    for root in roots + sub_roots:
        for item in os.listdir(root):
            if item.endswith('.app'):
                fpath = os.path.join(root, item)
                name = item.split('.app')[0]
                icon = get_mac_application_icon_path(fpath)
                apps[name] = (icon, fpath)
    return apps


def get_installed_applications():
    """"""
    apps = {}
    if sys.platform == 'darwin':
        apps = get_mac_applications()

    return apps


class ApplicationsDialog(QDialog):
    """"""

    def __init__(self, parent=None, association=None):
        """"""
        super(ApplicationsDialog, self).__init__(parent=parent)

        # Widgets
        self.label = QLabel()
        self.label_browse = QLabel()
        self.edit_filter = QLineEdit()
        self.list = QListWidget()
        self.button_browse = QPushButton(_('Browse...'))
        self.button_box = QDialogButtonBox(QDialogButtonBox.Ok
                                           | QDialogButtonBox.Cancel)
        self.button_ok = self.button_box.button(QDialogButtonBox.Ok)
        self.button_cancel = self.button_box.button(QDialogButtonBox.Cancel)

        self.setWindowTitle(_('Applications dialog'))
        self.edit_filter.setPlaceholderText(_('Type to filter by name...'))

        # Layout
        layout = QVBoxLayout()
        layout.addWidget(self.label)
        layout.addWidget(self.edit_filter)
        layout.addWidget(self.list)
        layout_browse = QHBoxLayout()
        layout_browse.addWidget(self.button_browse)
        layout_browse.addWidget(self.label_browse)
        layout.addLayout(layout_browse)
        layout.addStretch()
        layout.addWidget(self.button_box)
        self.setLayout(layout)

        # Signals
        self.edit_filter.textChanged.connect(self.filter)
        self.button_browse.clicked.connect(self.browse)
        self.button_ok.clicked.connect(self.accept)
        self.button_cancel.clicked.connect(self.reject)

        self.setup()

    def setup(self):
        """"""
        QApplication.setOverrideCursor(QCursor(Qt.WaitCursor))
        self.list.clear()
        apps = get_installed_applications()
        for app in sorted(apps):
            icon_path, fpath = apps[app]
            if icon_path:
                try:
                    icon = QIcon(icon_path)
                except:
                    icon = ima.icon('help')    
            else:
                icon = ima.icon('help')
            item = QListWidgetItem(icon, app)
            item.fpath = fpath
            self.list.addItem(item)
        QApplication.restoreOverrideCursor()

    def browse(self):
        """"""
        if sys.platform == 'darwin':
            basedir = '/Applications/'
            filters = _('Applications (*.app)')
            title = _('Select application')
            filename, _selfilter = getopenfilename(self, title, basedir, filters)

            if filename and filename.endswith('.app'):
                fpath = filename
                app = os.path.basename(filename).split('.app')[0]
                for row in range(self.list.count()):
                    item = self.list.item(row)
                    if app == item.text() and fpath == item.fpath:
                        break
                else:
                    icon_path = get_mac_application_icon_path(fpath)
                    icon = QIcon(icon_path) if icon_path else ima.icon('help')
                    item = QListWidgetItem(icon, app)
                    item.fpath = fpath
                    self.list.addItem(item)
                self.list.setCurrentItem(item)
                self.list.setFocus()

    def filter(self, text):
        """"""
        text = self.edit_filter.text().lower().strip()
        for row in range(self.list.count()):
            item = self.list.item(row)
            item.setHidden(text not in item.text().lower())

    def set_extension(self, extension):
        """"""
        self.label.setText(_('Choose the application for files of type ')
                           + extension)

    @property
    def application_path(self):
        """"""
        return self.list.currentItem().fpath

    @property
    def application_name(self):
        """"""
        return self.list.currentItem().text()


class FileAssociationsWidget(QWidget):
    """"""
    sig_data_changed = Signal(dict)

    def __init__(self, parent=None):
        """"""
        super(FileAssociationsWidget, self).__init__(parent=parent)

        # Variables
        self._data = {}
        self._initial_data = {}
        self._dlg_applications = None

        # Widgets
        self.label = QLabel(_('This is the main description of this tab.'))
        self.label_extensions = QLabel(_('File types:'))
        self.list_extensions = QListWidget()
        self.button_add = QPushButton(_('Add'))
        self.button_remove = QPushButton(_('Remove'))

        self.label_applications = QLabel(_('Associated applications:'))
        self.list_applications = QListWidget()
        self.button_add_application = QPushButton(_('Add'))
        self.button_remove_application = QPushButton(_('Remove'))
        self.button_default = QPushButton(_('Set default'))

        # Layout
        layout_extensions = QHBoxLayout()
        layout_extensions.addWidget(self.list_extensions, 4)

        layout_buttons_extensions = QVBoxLayout()
        layout_buttons_extensions.addWidget(self.button_add)
        layout_buttons_extensions.addWidget(self.button_remove)
        layout_buttons_extensions.addStretch()

        layout_applications = QHBoxLayout()
        layout_applications.addWidget(self.list_applications, 4)

        layout_buttons_applications = QVBoxLayout()
        layout_buttons_applications.addWidget(self.button_add_application)
        layout_buttons_applications.addWidget(self.button_remove_application)
        layout_buttons_applications.addWidget(self.button_default)
        layout_buttons_applications.addStretch()

        layout_extensions.addLayout(layout_buttons_extensions, 2)
        layout_applications.addLayout(layout_buttons_applications, 2)

        layout = QVBoxLayout()
        layout.addWidget(self.label)
        layout.addWidget(self.label_extensions)
        layout.addLayout(layout_extensions)
        layout.addWidget(self.label_applications)
        layout.addLayout(layout_applications)

        self.setLayout(layout)

        # Signals
        self.button_add.clicked.connect(self.add_association)
        self.button_remove.clicked.connect(self.remove_association)
        self.button_add_application.clicked.connect(self.add_application)
        self.button_remove_application.clicked.connect(
            self.remove_application)
        self.button_default.clicked.connect(self.set_default_application)
        self.list_extensions.currentRowChanged.connect(self.update_extensions)
        self.list_applications.currentRowChanged.connect(
            self.update_applications)
        self._refresh()

    def _refresh(self):
        """"""
        self.setUpdatesEnabled(False)
        for widget in [self.button_remove,  self.button_add_application,
                       self.button_remove_application, self.button_default]:
            widget.setDisabled(True)

        # If a selected item
        item = self.list_extensions.currentItem()
        if item:
            for widget in [self.button_remove, self.button_add_application,
                           self.button_remove_application]:
                widget.setDisabled(False)
        self.setUpdatesEnabled(True)

    def _add_association(self, value):
        """"""
        # Check value is not pressent
        for row in range(self.list_extensions.count()):
            item = self.list_extensions.item(row)
            if item.text().strip() == value.strip():
                break
        else:
            item = QListWidgetItem(value)
            self.list_extensions.addItem(item)
            self.list_extensions.setCurrentItem(item)

        self._refresh()

    def _add_application(self, app_name, fpath):
        """"""
        for row in range(self.list_applications.count()):
            item = self.list_extensions.item(row)
            if item and item.text().strip() == app_name:
                break
        else:
            icon_path = get_mac_application_icon_path(fpath)
            icon = QIcon(icon_path) if icon_path else ima.icon('help')
            item = QListWidgetItem(icon, app_name)
            self.list_applications.addItem(item)
            self.list_applications.setCurrentItem(item)

    def load_values(self, data=None):
        """"""
        self._data = data
        self._initial_data = data.copy()
        self._update_extensions()

    def _update_extensions(self):
        """"""
        self.list_extensions.clear()
        for extension, _ in sorted(self._data.items()):
            self._add_association(extension)

        # Select first item
        self.list_extensions.setCurrentRow(0)
        self.update_extensions()
        self.update_applications()

    def add_association(self, slot=None, value=None):
        """"""
        if value is None:
            text, ok_pressed = QInputDialog.getText(
                self,
                _('File association'),
                _('Enter new file association/extension (e.g. `*.txt` or '
                '`pattern.dol`)'),
                QLineEdit.Normal,
                "",
            )
        else:
           text, ok_pressed = value, True
 
        if ok_pressed:
            self._data[text] = []
            self._add_association(text)
            self.check_data_changed()

    def remove_association(self):
        """"""
        if self._data:
            if self.current_extension:
                self._data.pop(self.current_extension)
                self._update_extensions()
                self._refresh()
                self.check_data_changed()

    def add_application(self):
        """"""
        if self.current_extension:
            if self._dlg_applications is None:
                self._dlg_applications = ApplicationsDialog(self)

            self._dlg_applications.set_extension(self.current_extension)

            if self._dlg_applications.exec_():
                fpath = self._dlg_applications.application_path
                app = self._dlg_applications.application_name
                self._data[self.current_extension].append((app, fpath))
                self._add_application(app, fpath)
                self.check_data_changed()

    def remove_application(self):
        """"""
        current_row = self.list_applications.currentRow()
        values = self._data.get(self.current_extension)
        if values and current_row != -1:
            values.pop(current_row)
            self.update_extensions()
            self.update_applications()
            self.check_data_changed()

    def set_default_application(self):
        """"""
        current_row = self.list_applications.currentRow()
        if current_row != -1:
            values = self._data[self.current_extension]
            value = values.pop(current_row)
            values.insert(0, value)
            self._data[self.current_extension] = values
            self.update_extensions()
            self.check_data_changed()

    def update_extensions(self, row=None):
        """"""
        self.list_applications.clear()
        for extension, values in self._data.items():
            if extension.strip() == self.current_extension:
                for (app_name, fpath) in values:
                    self._add_application(app_name, fpath)
                break
        self.list_applications.setCurrentRow(0)
        self._refresh()

    def update_applications(self, row=None):
        """"""
        self._refresh()
        current_row =  self.list_applications.currentRow()
        self.button_default.setEnabled(current_row != 0)

    def check_data_changed(self):
        """"""
        self.sig_data_changed.emit(self._data)

    @property
    def current_extension(self):
        """"""
        item = self.list_extensions.currentItem()
        if item:
            return item.text()

    @property
    def data(self):
        """"""
        return self._data


def test_widget():
    from spyder.utils.qthelpers import qapplication
    app = qapplication()
    widget = FileAssociationsWidget()
    data = {
        '*.txt':
            [('App name', 'path-to-app'), ('App name 2', 'path-to-app')],
        '*.csv':
            [('App name 2', 'path-to-app'), ('App name 5', 'path-to-app')],
    }
    widget.load_values(data)
    widget.show()
    app.exec_()


if __name__ == '__main__':
    test_widget()
