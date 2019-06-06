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

    if icon_file is None:
        print(fpath)

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
        self.label = QLabel(_('Choose the application for files of type '))
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

        self._setup()

    def _setup(self):
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

    @property
    def application(self):
        """"""
        return self.list.currentItem().fpath


class FileAssociationsWidget(QWidget):
    """"""

    def __init__(self, parent=None, data=None):
        """"""
        super(FileAssociationsWidget, self).__init__(parent=parent)

        # Variables
        self._data = {}
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
        self._setup()

        if data:
            self.load_values(data)

    def _setup(self):
        """"""
        for widget in [self.button_remove,  self.button_add_application,
                       self.button_remove_application, self.button_default]:
            widget.setDisabled(True)

        # If a selected item
        item = self.list_extensions.currentItem()
        if item:
            for widget in [self.button_remove, self.button_add_application,
                           self.button_remove_application]:
                widget.setDisabled(False)

    def _check_values(self):
        """"""

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

        self._data[value] = []
        self._setup()

    def _remove_association(self, index):
        """"""
        print(index)

    def _add_application(self, value, key=None):
        """"""
        for row in range(self.list_applications.count()):
            item = self.list_extensions.item(row)
            if item and item.text().strip() == value.strip():
                break
        else:
            item = QListWidgetItem(value)
            self.list_applications.addItem(item)
            self.list_applications.setCurrentItem(item)

        # self._data[key].append(value)

    def load_values(self, data=None):
        """"""
        self._data = data
        for key, values in sorted(data.items()):
            self._add_association(key)
            for value in values:
                self._add_application(key, value)

        # Select first item
        self.list_applications.setCurrentRow(0)

    def add_association(self, show_dialog=True):
        """"""
        text, ok_pressed = QInputDialog.getText(
            self,
            _('File association'),
            _('Enter new file association/extension (e.g. `*.txt` or '
              '`pattern.dol`)'),
            QLineEdit.Normal,
            "",
        )
        if ok_pressed:
            self._add_association(text)

    def remove_association(self, index):
        """"""

    def add_application(self):
        """"""
        if self._dlg_applications is None:
            self._dlg_applications = ApplicationsDialog(self)
        self._dlg_applications.show()

    def remove_application(self):
        """"""

    def set_default_application(self):
        """"""
        current_item = self.list_extensions.currentItem()
        current_row = self.list_editors.currentRow()
        values = self._data[current_item.text().strip()]
        value = values.pop(current_row)
        values.insert(0, value)
        self._data[current_item.text().strip()] = values
        self.update_extensions()

    def update_extensions(self, row=None):
        """"""
        self.list_applications.clear()
        current_item = self.list_extensions.currentItem()
        for key, values in self._data.items():
            if key.strip() == current_item.text().strip():
                for value in values:
                    self._add_application(value)
                break
        self.list_applications.setCurrentRow(0)

    def update_applications(self, row=None):
        """"""
        current_row =  self.list_applications.currentRow()
        self.button_default.setEnabled(current_row != 0)


def test_widget():
    from spyder.utils.qthelpers import qapplication
    app = qapplication()
    widget = FileAssociationsWidget()
    data = {
        '*.txt':
            ['something', 'something 2'],
        '*.csv':
            ['something 4', 'something 5', 'some 3'],
    }
    # widget.load_values(data)
    widget.show()
    app.exec_()


if __name__ == '__main__':
    test_widget()
