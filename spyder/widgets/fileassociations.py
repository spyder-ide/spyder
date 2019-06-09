# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""
File associations widget for use in global and project preferences.
"""

# Standard library imports
from __future__ import print_function
import glob
import itertools
import os
import sys

# Third party imports
from qtpy.compat import getopenfilename
from qtpy.QtCore import QSize, Qt, Signal
from qtpy.QtGui import QCursor, QIcon
from qtpy.QtWidgets import (QApplication, QDialog, QDialogButtonBox,
                            QHBoxLayout, QInputDialog, QLabel, QLineEdit,
                            QListWidget, QListWidgetItem, QPushButton,
                            QVBoxLayout, QWidget)
# Local imports
from spyder.config.base import _, get_conf_path
from spyder.utils import icon_manager as ima


def parse_linux_desktop_entry(fpath):
    """Load data from desktop entry with xdg specification."""
    from xdg.DesktopEntry import DesktopEntry

    try:
        entry = DesktopEntry(fpath)
        entry_data = {}
        entry_data['name'] = entry.getName()
        entry_data['icon_path'] = entry.getIcon()
        entry_data['exec'] = entry.getExec()
        entry_data['type'] = entry.getType()
        entry_data['hidden'] = entry.getHidden()
        entry_data['fpath'] = fpath
    except Exception:
        entry_data = {
            'name': '',
            'icon_path': '',
            'hidden': '',
            'exec': '',
            'type': '',
            'fpath': fpath
        }

    return entry_data


def get_mac_application_icon_path(app_bundle_path):
    """Parse mac application bundle and return path for *.icns file."""
    import plistlib
    contents_path = info_path = os.path.join(app_bundle_path, 'Contents')
    info_path = os.path.join(contents_path, 'Info.plist')

    pl = {}
    if os.path.isfile(info_path):
        try:
            # readPlist is deprecated but needed for py27 compat
            pl = plistlib.readPlist(info_path)
        except Exception:
            # TODO: Add the specific errors to catch
            pass

    icon_file = pl.get('CFBundleIconFile')
    icon_path = None
    if icon_file:
        icon_path = os.path.join(contents_path, 'Resources', icon_file)

        # Some app bundles seem to list the icon name without extension
        if not icon_path.endswith('.icns'):
            icon_path = icon_path + '.icns'

        if not os.path.isfile(icon_path):
            icon_path = None

    return icon_path


def get_username():
    """Return current session username."""
    if os.name == 'nt':
        username = os.getlogin()
    else:
        import pwd
        username = pwd.getpwuid(os.getuid())[0]

    return username


def get_win_reg_info(key_path, hive, flag, subkeys):
    """
    See:
    https://stackoverflow.com/questions/53132434/list-of-installed-programs
    """
    import winreg

    reg = winreg.ConnectRegistry(None, hive)
    software_list = []
    try:
        key = winreg.OpenKey(reg, key_path, 0, winreg.KEY_READ | flag)
        count_subkey = winreg.QueryInfoKey(key)[0]

        for index in range(count_subkey):
            software = {}
            try:
                subkey_name = winreg.EnumKey(key, index)
                if not (subkey_name.startswith('{')
                        and subkey_name.endswith('}')):
                    software['key'] = subkey_name
                    subkey = winreg.OpenKey(key, subkey_name)
                    for property in subkeys:
                        try:
                            value = winreg.QueryValueEx(subkey, property)[0]
                            software[property] = value
                        except EnvironmentError:
                            software[property] = ''
                    software_list.append(software)
            except EnvironmentError:
                continue
    except Exception:
        pass

    return software_list


def get_win_applications():
    """Return all system installed windows applications."""
    import winreg

    # See:
    # https://docs.microsoft.com/en-us/windows/desktop/shell/app-registration
    key_path = 'SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\App Paths'

    # Hive and flags
    hfs = [
        (winreg.HKEY_LOCAL_MACHINE, winreg.KEY_WOW64_32KEY),
        (winreg.HKEY_LOCAL_MACHINE, winreg.KEY_WOW64_64KEY),
        (winreg.HKEY_CURRENT_USER, 0),
    ]
    subkeys = [None]
    sort_key = 'key'
    app_paths = {}
    _apps = [get_win_reg_info(key_path, hf[0], hf[1], subkeys) for hf in hfs]
    software_list = itertools.chain(*_apps)
    for software in sorted(software_list, key=lambda x: x[sort_key]):
        if software[None]:
            key = software['key'].capitalize().replace('.exe', '')
            app_paths[key] = software[None].lower()

    # See:
    # https://www.blog.pythonlibrary.org/2010/03/03/finding-installed-software-using-python/
    # https://stackoverflow.com/questions/53132434/list-of-installed-programs
    key_path = 'SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Uninstall'
    subkeys = ['DisplayName', 'InstallLocation', 'DisplayIcon']
    sort_key = 'DisplayName'
    apps = {}
    _apps = [get_win_reg_info(key_path, hf[0], hf[1], subkeys) for hf in hfs]
    software_list = itertools.chain(*_apps)
    for software in sorted(software_list, key=lambda x: x[sort_key]):
        location = software['InstallLocation']
        name = software['DisplayName']
        icon = software['DisplayIcon']
        key = software['key']
        if name and icon:
            icon = icon.replace('"', '').replace("'", '')
            icon = icon.split(',')[0]

            if location == '' and icon:
                location = os.path.dirname(icon)

            if not os.path.isfile(icon):
                icon = ''

            if location and os.path.isdir(location):
                files = [f for f in os.listdir(location)
                         if os.path.isfile(os.path.join(location, f))]
                if files:
                    for fname in files:
                        fn_low = fname.lower()
                        valid_file = fn_low.endswith(('.exe', '.com', '.bat'))
                        if valid_file and not fn_low.startswith('unins'):
                            fpath = os.path.join(location, fname)
                            apps[name + ' (' + fname + ')'] = (icon.lower(),
                                                               fpath.lower())
    # Join data
    values = list(zip(*apps.values()))[-1]
    for name, fpath in app_paths.items():
        if fpath not in values:
            apps[name] = fpath

    return apps


def get_linux_applications():
    """Return all system installed linux applications."""
    # See:
    # https://standards.freedesktop.org/desktop-entry-spec/desktop-entry-spec-latest.html
    # https://askubuntu.com/questions/433609/how-can-i-list-all-applications-installed-in-my-system
    apps = {}
    desktop_app_paths = [
        '/usr/share/**/*.desktop',
        '~/.local/share/**/*.desktop',
    ]
    all_entries_data = []
    for path in desktop_app_paths:
        fpaths = glob.glob(path)
        for fpath in fpaths:
            entry_data = parse_linux_desktop_entry(fpath)
            all_entries_data.append(entry_data)

    for entry_data in sorted(all_entries_data, key=lambda x: x['name']):
        if not entry_data['hidden'] and entry_data['type'] == 'Application':
            apps[entry_data['name']] = entry_data['fpath']

    return apps


def get_mac_applications():
    """Return all system installed osx applications."""
    apps = {}
    app_folders = [
        '/**/*.app',
        '/Users/{}/**/*.app'.format(get_username())
    ]

    fpaths = []
    for path in app_folders:
        fpaths += glob.glob(path)

    for fpath in fpaths:
        if os.path.isdir(fpath):
            name = os.path.basename(fpath).split('.app')[0]
            apps[name] = fpath

    return apps


def get_application_icon(fpath):
    """Return application icon or default icon if not found."""
    if os.path.isfile(fpath) or os.path.isdir(fpath):
        icon = ima.icon('no_match')
        if sys.platform == 'darwin':
            icon_path = get_mac_application_icon_path(fpath)
            if icon_path and os.path.isfile(icon_path):
                icon = QIcon(icon_path)
        elif os.name == 'nt':
            pass
        else:
            entry_data = parse_linux_desktop_entry(fpath)
            icon_path = entry_data['icon_path']
            if icon_path:
                if os.path.isfile(icon_path):
                    icon = QIcon(icon_path)
                else:
                    icon = QIcon.fromTheme(icon_path)
    else:
        icon = ima.icon('help')

    return icon


def get_installed_applications():
    """
    Return all system installed applications.

    The return value is a list of tuples where the first item is the icon path
    and the second item is the program executable path.
    """
    apps = {}
    if sys.platform == 'darwin':
        apps = get_mac_applications()
    elif os.name == 'nt':
        apps = get_win_applications()
    else:
        apps = get_linux_applications()

    return apps


class ApplicationsDialog(QDialog):
    """Dialog for selection of installed system/user applications."""

    def __init__(self, parent=None):
        """Dialog for selection of installed system/user applications."""
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

        # Widget setup
        self.setWindowTitle(_('Applications dialog'))
        self.edit_filter.setPlaceholderText(_('Type to filter by name...'))
        self.list.setIconSize(QSize(16, 16))  # FIXME: Use metrics

        # Layout
        layout = QVBoxLayout()
        layout.addWidget(self.label)
        layout.addWidget(self.edit_filter)
        layout.addWidget(self.list)
        layout_browse = QHBoxLayout()
        layout_browse.addWidget(self.button_browse)
        layout_browse.addWidget(self.label_browse)
        layout.addLayout(layout_browse)
        layout.addSpacing(12)  # FIXME: Use metrics
        layout.addWidget(self.button_box)
        self.setLayout(layout)

        # Signals
        self.edit_filter.textChanged.connect(self.filter)
        self.button_browse.clicked.connect(lambda x: self.browse())
        self.button_ok.clicked.connect(self.accept)
        self.button_cancel.clicked.connect(self.reject)

        self.setup()

    def setup(self):
        """Load installed applications."""
        QApplication.setOverrideCursor(QCursor(Qt.WaitCursor))
        self.list.clear()
        apps = get_installed_applications()
        for app in sorted(apps, key=lambda x: x.lower()):
            fpath = apps[app]
            icon = get_application_icon(fpath)
            item = QListWidgetItem(icon, app)
            item.setToolTip(fpath)
            item.fpath = fpath
            self.list.addItem(item)

        # FIXME: Use metrics
        self.list.setMinimumWidth(self.list.sizeHintForColumn(0) + 24)
        QApplication.restoreOverrideCursor()

    def browse(self, fpath=None):
        """Prompt user to select an application not found on the list."""
        item = None

        if sys.platform == 'darwin':
            basedir = '/Applications/'
            filters = _('Applications (*.app)')
            title = _('Select application')

            if fpath is None:
                fpath, __ = getopenfilename(self, title, basedir, filters)

            if fpath and fpath.endswith('.app'):
                app = os.path.basename(fpath).split('.app')[0]
                for row in range(self.list.count()):
                    item = self.list.item(row)
                    if app == item.text() and fpath == item.fpath:
                        break
        elif os.name == 'nt':
            basedir = 'C:\\'
            filters = _('Applications (*.exe *.bat *.com)')
            title = _('Select application')

            if fpath is None:
                fpath, __ = getopenfilename(self, title, basedir, filters)

            if fpath and fpath.endswith(('.exe', '.bat', '.com')):
                app = os.path.basename(fpath).capitalize().rsplit('.')[0]
                for row in range(self.list.count()):
                    item = self.list.item(row)
                    if app == item.text() and fpath == item.fpath:
                        break
        else:
            basedir = '/'
            filters = _('Applications (*.desktop)')
            title = _('Select application')

            if fpath is None:
                fpath, __ = getopenfilename(self, title, basedir, filters)

            if fpath and fpath.endswith(('.desktop')):
                entry_data = parse_linux_desktop_entry(fpath)
                app = entry_data['name']
                for row in range(self.list.count()):
                    item = self.list.item(row)
                    if app == item.text() and fpath == item.fpath:
                        break
        if fpath:
            if item:
                self.list.setCurrentItem(item)
            else:
                icon = get_application_icon(fpath)
                item = QListWidgetItem(icon, app)
                item.fpath = fpath
                self.list.addItem(item)

        self.list.setFocus()

    def filter(self, text):
        """Filter the list of applications based on text."""
        text = self.edit_filter.text().lower().strip()
        for row in range(self.list.count()):
            item = self.list.item(row)
            item.setHidden(text not in item.text().lower())

    def set_extension(self, extension):
        """Set the extension on the label of the dialog."""
        self.label.setText(_('Choose the application for files of type ')
                           + extension)

    @property
    def application_path(self):
        """Return the selected application path to executable."""
        return self.list.currentItem().fpath

    @property
    def application_name(self):
        """Return the selected application name."""
        return self.list.currentItem().text()


class FileAssociationsWidget(QWidget):
    """Widget to add applications association to file extensions."""
    sig_data_changed = Signal(dict)

    def __init__(self, parent=None):
        """Widget to add applications association to file extensions."""
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
        self._refresh()

    def _refresh(self):
        """Refresh the status of buttons on widget."""
        self.setUpdatesEnabled(False)
        for widget in [self.button_remove,  self.button_add_application,
                       self.button_remove_application, self.button_default]:
            widget.setDisabled(True)

        item = self.list_extensions.currentItem()
        if item:
            for widget in [self.button_remove, self.button_add_application,
                           self.button_remove_application]:
                widget.setDisabled(False)
        self.setUpdatesEnabled(True)

    def _add_association(self, value):
        """Add association helper."""
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
        """Add application helper."""
        for row in range(self.list_applications.count()):
            item = self.list_extensions.item(row)
            if item and item.text().strip() == app_name:
                break
        else:
            icon = get_application_icon(fpath)
            item = QListWidgetItem(icon, app_name)
            self.list_applications.addItem(item)
            self.list_applications.setCurrentItem(item)

        if not (os.path.isfile(fpath) or os.path.isdir(fpath)):
            item.setToolTip(_('Application not found!'))

    def _update_extensions(self):
        """Update extensions list."""
        self.list_extensions.clear()
        for extension, _ in sorted(self._data.items()):
            self._add_association(extension)

        # Select first item
        self.list_extensions.setCurrentRow(0)
        self.update_extensions()
        self.update_applications()

    def load_values(self, data=None):
        """
        Load file associations data.

        Format {'*.ext': [['Application Name', '/path/to/app/executable']]}

        `/path/to/app/executable` is an executable app on mac and windows and
        a .desktop xdg file on linux.
        """
        self._data = data
        self._update_extensions()

    def add_association(self, slot=None, value=None):
        """Add extension file association."""
        if value is None:
            text, ok_pressed = QInputDialog.getText(
                self,
                _('File association'),
                (_('Enter new file association/extension') +
                 ' (e.g. <code>*.txt</code> or <code>name.ext</code>)'),
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
        """Remove extension file association."""
        if self._data:
            if self.current_extension:
                self._data.pop(self.current_extension)
                self._update_extensions()
                self._refresh()
                self.check_data_changed()

    def add_application(self):
        """Remove application to selected extension."""
        if self.current_extension:
            if self._dlg_applications is None:
                self._dlg_applications = ApplicationsDialog(self)

            self._dlg_applications.set_extension(self.current_extension)

            if self._dlg_applications.exec_():
                app_name = self._dlg_applications.application_name
                fpath = self._dlg_applications.application_path
                self._data[self.current_extension].append((app_name, fpath))
                self._add_application(app_name, fpath)
                self.check_data_changed()

    def remove_application(self):
        """Remove application from selected extension."""
        current_row = self.list_applications.currentRow()
        values = self._data.get(self.current_extension)
        if values and current_row != -1:
            values.pop(current_row)
            self.update_extensions()
            self.update_applications()
            self.check_data_changed()

    def set_default_application(self):
        """
        Set the selected item on the application list as default application.
        """
        current_row = self.list_applications.currentRow()
        if current_row != -1:
            values = self._data[self.current_extension]
            value = values.pop(current_row)
            values.insert(0, value)
            self._data[self.current_extension] = values
            self.update_extensions()
            self.check_data_changed()

    def update_extensions(self, row=None):
        """Update extensiosn list after additions or deletions."""
        self.list_applications.clear()
        for extension, values in self._data.items():
            if extension.strip() == self.current_extension:
                for (app_name, fpath) in values:
                    self._add_application(app_name, fpath)
                break
        self.list_applications.setCurrentRow(0)
        self._refresh()

    def update_applications(self, row=None):
        """Update application list after additions or deletions."""
        self._refresh()
        current_row = self.list_applications.currentRow()
        self.button_default.setEnabled(current_row != 0)

    def check_data_changed(self):
        """Check if data has changed and emit signal as needed."""
        self.sig_data_changed.emit(self._data)

    @property
    def current_extension(self):
        """Return the current selected extension text."""
        item = self.list_extensions.currentItem()
        if item:
            return item.text()

    @property
    def data(self):
        """Return the current file associations data."""
        return self._data.copy()


def test_widget():
    from spyder.utils.qthelpers import qapplication
    app = qapplication()
    widget = FileAssociationsWidget()
    data = {
        '*.txt':
            [
                ('App name 1', 'path-to-app'),
                ('App name 2', 'path-to-app'),
            ],
        '*.csv':
            [
                ('App name 2', 'path-to-app'),
                ('App name 5', 'path-to-app'),
            ],
    }
    widget.load_values(data)
    widget.show()
    app.exec_()


if __name__ == '__main__':
    test_widget()
