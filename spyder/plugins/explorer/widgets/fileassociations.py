# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""
File associations widget for use in global and project preferences.
"""

from __future__ import print_function

# Standard library imports
import os
import re
import sys

# Third party imports
from qtpy.compat import getopenfilename
from qtpy.QtCore import QRegExp, QSize, Qt, Signal
from qtpy.QtGui import QCursor, QRegExpValidator
from qtpy.QtWidgets import (QApplication, QDialog, QDialogButtonBox,
                            QHBoxLayout, QLabel, QLineEdit,
                            QListWidget, QListWidgetItem, QPushButton,
                            QVBoxLayout, QWidget)
# Local imports
from spyder.config.base import _
from spyder.utils.encoding import is_text_file
from spyder.utils.programs import (get_application_icon,
                                   get_installed_applications,
                                   parse_linux_desktop_entry)


class InputTextDialog(QDialog):
    """Input text dialog with regex validation."""

    def __init__(self, parent=None, title='', label=''):
        """Input text dialog with regex validation."""
        super(InputTextDialog, self).__init__(parent=parent)
        self._reg = None
        self._regex = None

        # Widgets
        self.label = QLabel()
        self.lineedit = QLineEdit()
        self.button_box = QDialogButtonBox(QDialogButtonBox.Ok
                                           | QDialogButtonBox.Cancel)
        self.button_ok = self.button_box.button(QDialogButtonBox.Ok)
        self.button_cancel = self.button_box.button(QDialogButtonBox.Cancel)

        # Widget setup
        self.setWindowTitle(title)
        self.setMinimumWidth(500)  # FIXME: use metrics
        self.label.setText(label)

        # Layout
        layout = QVBoxLayout()
        layout.addWidget(self.label)
        layout.addWidget(self.lineedit)
        layout.addSpacing(24)  # FIXME: use metrics
        layout.addWidget(self.button_box)
        self.setLayout(layout)

        # Signals
        self.button_ok.clicked.connect(self.accept)
        self.button_cancel.clicked.connect(self.reject)
        self.lineedit.textChanged.connect(self.validate)

        self.validate()

    def validate(self):
        """Validate content."""
        text = self.text().strip()
        is_valid = bool(text)
        if self._reg:
            res = self._reg.match(text)
            if res:
                text_matched = res.group(0)
                is_valid = is_valid and text_matched == text
            else:
                is_valid = False
        self.button_ok.setEnabled(is_valid)

    def set_regex_validation(self, regex):
        """Set the regular expression to validate content."""
        self._regex = regex
        self._reg = re.compile(regex, re.IGNORECASE)
        validator = QRegExpValidator(QRegExp(regex))
        self.lineedit.setValidator(validator)

    def text(self):
        """Return the text of the lineedit."""
        return self.lineedit.text()

    def set_text(self, text):
        """Set the text of the lineedit."""
        self.lineedit.setText(text)
        self.validate()


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
        self.setWindowTitle(_('Applications'))
        self.edit_filter.setPlaceholderText(_('Type to filter by name'))
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
        self.list.currentItemChanged.connect(self._refresh)

        self._refresh()
        self.setup()

    def setup(self, applications=None):
        """Load installed applications."""
        QApplication.setOverrideCursor(QCursor(Qt.WaitCursor))
        self.list.clear()
        if applications is None:
            apps = get_installed_applications()
        else:
            apps = applications

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
        self._refresh()

    def _refresh(self):
        """Refresh the status of buttons on widget."""
        self.button_ok.setEnabled(self.list.currentRow() != -1)

    def browse(self, fpath=None):
        """Prompt user to select an application not found on the list."""
        app = None
        item = None

        if sys.platform == 'darwin':
            if fpath is None:
                basedir = '/Applications/'
                filters = _('Applications (*.app)')
                title = _('Select application')
                fpath, __ = getopenfilename(self, title, basedir, filters)

            if fpath and fpath.endswith('.app') and os.path.isdir(fpath):
                app = os.path.basename(fpath).split('.app')[0]
                for row in range(self.list.count()):
                    item = self.list.item(row)
                    if app == item.text() and fpath == item.fpath:
                        break
                else:
                    item = None
        elif os.name == 'nt':
            if fpath is None:
                basedir = 'C:\\'
                filters = _('Applications (*.exe *.bat *.com)')
                title = _('Select application')
                fpath, __ = getopenfilename(self, title, basedir, filters)

            if fpath:
                check_1 = fpath.endswith('.bat') and is_text_file(fpath)
                check_2 = (fpath.endswith(('.exe', '.com'))
                           and not is_text_file(fpath))
                if check_1 or check_2:
                    app = os.path.basename(fpath).capitalize().rsplit('.')[0]
                    for row in range(self.list.count()):
                        item = self.list.item(row)
                        if app == item.text() and fpath == item.fpath:
                            break
                    else:
                        item = None
        else:
            if fpath is None:
                basedir = '/'
                filters = _('Applications (*.desktop)')
                title = _('Select application')
                fpath, __ = getopenfilename(self, title, basedir, filters)

            if fpath and fpath.endswith(('.desktop')) and is_text_file(fpath):
                entry_data = parse_linux_desktop_entry(fpath)
                app = entry_data['name']
                for row in range(self.list.count()):
                    item = self.list.item(row)
                    if app == item.text() and fpath == item.fpath:
                        break
                else:
                    item = None

        if fpath:
            if item:
                self.list.setCurrentItem(item)
            elif app:
                icon = get_application_icon(fpath)
                item = QListWidgetItem(icon, app)
                item.fpath = fpath
                self.list.addItem(item)
                self.list.setCurrentItem(item)

        self.list.setFocus()
        self._refresh()

    def filter(self, text):
        """Filter the list of applications based on text."""
        text = self.edit_filter.text().lower().strip()
        for row in range(self.list.count()):
            item = self.list.item(row)
            item.setHidden(text not in item.text().lower())
        self._refresh()

    def set_extension(self, extension):
        """Set the extension on the label of the dialog."""
        self.label.setText(_('Choose the application for files of type ')
                           + extension)

    @property
    def application_path(self):
        """Return the selected application path to executable."""
        item = self.list.currentItem()
        path = item.fpath if item else ''
        return path

    @property
    def application_name(self):
        """Return the selected application name."""
        item = self.list.currentItem()
        text = item.text() if item else ''
        return text


class FileAssociationsWidget(QWidget):
    """Widget to add applications association to file extensions."""

    # This allows validating a single extension entry or a list of comma
    # separated values (eg `*.json` or `*.json,*.txt,MANIFEST.in`)
    _EXTENSIONS_LIST_REGEX = (r'(?:(?:\*{1,1}|\w+)\.\w+)'
                              r'(?:,(?:\*{1,1}|\w+)\.\w+){0,20}')
    sig_data_changed = Signal(dict)

    def __init__(self, parent=None):
        """Widget to add applications association to file extensions."""
        super(FileAssociationsWidget, self).__init__(parent=parent)

        # Variables
        self._data = {}
        self._dlg_applications = None
        self._dlg_input = None
        self._regex = re.compile(self._EXTENSIONS_LIST_REGEX)

        # Widgets
        self.label = QLabel(
            _("Here you can associate different external applications "
              "to open specific file extensions (e.g. .txt "
              "files with Notepad++ or .csv files with Excel).")
        )
        self.label.setWordWrap(True)
        self.label_extensions = QLabel(_('File types:'))
        self.list_extensions = QListWidget()
        self.button_add = QPushButton(_('Add'))
        self.button_remove = QPushButton(_('Remove'))
        self.button_edit = QPushButton(_('Edit'))

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
        layout_buttons_extensions.addWidget(self.button_edit)
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
        self.button_add.clicked.connect(lambda: self.add_association())
        self.button_remove.clicked.connect(self.remove_association)
        self.button_edit.clicked.connect(self.edit_association)
        self.button_add_application.clicked.connect(self.add_application)
        self.button_remove_application.clicked.connect(
            self.remove_application)
        self.button_default.clicked.connect(self.set_default_application)
        self.list_extensions.currentRowChanged.connect(self.update_extensions)
        self.list_extensions.itemDoubleClicked.connect(self.edit_association)
        self.list_applications.currentRowChanged.connect(
            self.update_applications)
        self._refresh()
        self._create_association_dialog()

    def _refresh(self):
        """Refresh the status of buttons on widget."""
        self.setUpdatesEnabled(False)
        for widget in [self.button_remove,  self.button_add_application,
                       self.button_edit,
                       self.button_remove_application, self.button_default]:
            widget.setDisabled(True)

        item = self.list_extensions.currentItem()
        if item:
            for widget in [self.button_remove, self.button_add_application,
                           self.button_remove_application, self.button_edit]:
                widget.setDisabled(False)
        self.update_applications()
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
        app_not_found_text = _(' (Application not found!)')
        for row in range(self.list_applications.count()):
            item = self.list_applications.item(row)
            # Ensure the actual name is checked without the `app not found`
            # additional text, in case app was not found
            item_text = item.text().replace(app_not_found_text, '').strip()
            if item and item_text == app_name:
                break
        else:
            icon = get_application_icon(fpath)

            if not (os.path.isfile(fpath) or os.path.isdir(fpath)):
                app_name += app_not_found_text

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

    def _create_association_dialog(self):
        """Create input extension dialog and save it to for reuse."""
        self._dlg_input = InputTextDialog(
            self,
            title=_('File association'),
            label=(
                _('Enter new file extension. You can add several values '
                  'separated by commas.<br>Examples include:')
                + '<ul><li><code>*.txt</code></li>'
                + '<li><code>*.json,*.csv</code></li>'
                + '<li><code>*.json,README.md</code></li></ul>'
            ),
        )
        self._dlg_input.set_regex_validation(self._EXTENSIONS_LIST_REGEX)

    def load_values(self, data=None):
        """
        Load file associations data.

        Format {'*.ext': [['Application Name', '/path/to/app/executable']]}

        `/path/to/app/executable` is an executable app on mac and windows and
        a .desktop xdg file on linux.
        """
        self._data = {} if data is None else data
        self._update_extensions()

    def add_association(self, value=None):
        """Add extension file association."""
        if value is None:
            text, ok_pressed = '', False
            self._dlg_input.set_text('')

            if self._dlg_input.exec_():
                text = self._dlg_input.text()
                ok_pressed = True
        else:
            match = self._regex.match(value)
            text, ok_pressed = value, bool(match)

        if ok_pressed:
            if text not in self._data:
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

    def edit_association(self):
        """Edit text of current selected association."""
        old_text = self.current_extension
        self._dlg_input.set_text(old_text)

        if self._dlg_input.exec_():
            new_text = self._dlg_input.text()
            if old_text != new_text:
                values = self._data.pop(self.current_extension)
                self._data[new_text] = values
                self._update_extensions()
                self._refresh()
                for row in range(self.list_extensions.count()):
                    item = self.list_extensions.item(row)
                    if item.text() == new_text:
                        self.list_extensions.setCurrentItem(item)
                        break
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
