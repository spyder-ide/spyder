# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright © Spyder Project Contributors
#
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)
# -----------------------------------------------------------------------------
"""Project creation dialog."""

from __future__ import print_function

# Standard library imports
import errno
import os
import os.path as osp
import subprocess
import sys
import tempfile

# Third party imports
from qtpy.compat import getexistingdirectory
from qtpy.QtCore import Qt, Signal
from qtpy.QtGui import QIcon
from qtpy.QtWidgets import (QButtonGroup, QComboBox, QDialog,
                            QDialogButtonBox, QGridLayout, QGroupBox,
                            QHBoxLayout, QLabel, QLineEdit, QPushButton,
                            QRadioButton, QScrollArea, QStackedWidget, QToolButton,
                            QVBoxLayout, QWidget)
import requests

# Local imports
from spyder.config.base import _, get_home_dir
from spyder.plugins.projects.utils.conda import get_conda_environments
from spyder.plugins.projects.widgets import get_available_project_types
from spyder.py3compat import PY3, to_text_string
from spyder.utils import icon_manager as ima
from spyder.utils import programs
from spyder.utils.programs import is_anaconda
from spyder.utils.qthelpers import get_std_icon
from spyder.plugins.projects.utils.conda import (get_conda_environments,
                                                 get_conda_packages,
                                                 get_conda_forge_packages,
                                                 get_pypi_packages)
from spyder.plugins.projects.widgets.preferences import PackagesWidget


def is_writable(path):
    """Check if path has write access"""
    try:
        testfile = tempfile.TemporaryFile(dir=path)
        testfile.close()
    except OSError as e:
        if e.errno == errno.EACCES:  # 13
            return False
    return True


class BaseProjectPage(QWidget):
    """Base project configuration page."""

    # object represents the text of an issue
    sig_validated = Signal(bool, object)

    def __init__(self, parent=None):
        """Base project configuration page."""
        super(BaseProjectPage, self).__init__(parent=parent)
        self._parent = parent

    def setup_page(self):
        """This method is where the content is created."""
        raise NotImplementedError

    def get_name(self):
        """Return the page name."""
        raise NotImplementedError

    def validate(self):
        """
        Validate the project page.

        This method must emit `sig_validated` signal and return `True` or
        `False`.
        """
        raise NotImplementedError

    def create(self, context):
        """
        Actions to execute on context for later project creation.

        This method has to return the context dictionary.
        """
        return context


class GeneralProjectPage(BaseProjectPage):
    """"""

    sig_project_type_updated = Signal(str)

    def setup_page(self):
        """"""
        self.project_name = None
        self.location = get_home_dir()

        # Widgets
        self.groupbox = QButtonGroup()
        self.radio_new_dir = QRadioButton(_("New directory"))
        self.radio_from_dir = QRadioButton(_("Existing directory"))
        self.radio_from_vcs = QRadioButton(_("Version control"))

        self.label_project_name_or_url = QLabel(_('Project name'))
        self.label_location = QLabel(_('Location'))
        self.label_project_type = QLabel(_('Project type'))
        self.label_project_preferences = QLabel(_('Preferences'))

        self.text_project_name_or_url = QLineEdit()
        self.text_location = QLineEdit(get_home_dir())
        self.combo_project_type = QComboBox()
        self.combo_project_preferences = QComboBox()
        self.button_select_location = QToolButton()

        # Widget setup
        self.groupbox.addButton(self.radio_new_dir)
        self.groupbox.addButton(self.radio_from_dir)
        self.groupbox.addButton(self.radio_from_vcs)
        self.radio_new_dir.setChecked(True)
        self.text_location.setEnabled(True)
        self.text_location.setReadOnly(True)
        self.button_select_location.setIcon(get_std_icon('DirOpenIcon'))
        self.combo_project_type.addItems(self._get_project_types())

        self.combo_project_preferences.addItem(
            _('Use application preferences'), 'application')
        self.combo_project_preferences.addItem(
            _('Use project preferences'), 'project')
        self.setWindowTitle(_('Create new project'))
        self.setMinimumWidth(500)

        # Layouts
        layout_top = QHBoxLayout()
        layout_top.addWidget(self.radio_new_dir)
        layout_top.addWidget(self.radio_from_dir)
        layout_top.addWidget(self.radio_from_vcs)
        layout_top.addStretch(1)

        layout_grid = QGridLayout()
        layout_grid.addWidget(self.label_project_name_or_url, 0, 0)
        layout_grid.addWidget(self.text_project_name_or_url, 0, 1, 1, 2)
        layout_grid.addWidget(self.label_location, 1, 0)
        layout_grid.addWidget(self.text_location, 1, 1)
        layout_grid.addWidget(self.button_select_location, 1, 2)
        layout_grid.addWidget(self.label_project_type, 2, 0)
        layout_grid.addWidget(self.combo_project_type, 2, 1, 1, 2)
        layout_grid.addWidget(self.label_project_preferences, 3, 0)
        layout_grid.addWidget(self.combo_project_preferences, 3, 1, 1, 2)

        layout = QVBoxLayout()
        layout.addLayout(layout_top)
        layout.addSpacing(10)
        layout.addLayout(layout_grid)
        layout.addStretch()
        self.setLayout(layout)

        # Signals and slots
        self.button_select_location.clicked.connect(self._select_location)
        self.groupbox.buttonClicked.connect(self.validate)
        self.text_project_name_or_url.textChanged.connect(self.validate)
        self.combo_project_type.currentTextChanged.connect(
            self.sig_project_type_updated)

    def _get_project_types(self):
        """Get all available project types."""
        project_types = get_available_project_types()
        projects = []

        for project in project_types:
            projects.append(project.PROJECT_TYPE_NAME)

        return projects

    def _select_location(self):
        """Select directory."""
        location = osp.normpath(getexistingdirectory(
            self,
            _("Select directory"),
            self.location),
        )

        if location:
            if is_writable(location):
                self.location = location
                self.text_location.setText(location)
                self.validate()

    def validate(self):
        is_valid = False
        # self.text_project_name_or_url.setEnabled(self.radio_new_dir.isChecked())
        name_or_url = self.text_project_name_or_url.text().strip()
        path = None
        error = ''

        if self.radio_new_dir.isChecked():
            self.label_project_name_or_url.setDisabled(False)
            self.text_project_name_or_url.setDisabled(False)
            self.text_project_name_or_url.setVisible(True)
            self.label_project_name_or_url.setText(_('Project name    '))
            path = osp.join(self.location, name_or_url)

            if name_or_url == '':
                error = _('Project name cannot be empty!')
                is_valid = False
            else:
                if osp.isdir(path):
                    error = _('Directory already exists!')
                    is_valid = False
                else:
                    is_valid = True

        if self.radio_from_dir.isChecked():
            self.label_project_name_or_url.setDisabled(True)
            self.text_project_name_or_url.setVisible(False)
            self.text_project_name_or_url.setText('')
            self.label_project_name_or_url.setText('<p>' + '&nbsp;'*26 + '</p>')
            path = self.location
            is_valid = True

        if self.radio_from_vcs.isChecked():
            self.label_project_name_or_url.setDisabled(False)
            self.text_project_name_or_url.setDisabled(False)
            self.text_project_name_or_url.setVisible(True)
            self.label_project_name_or_url.setText(_('Repository URL'))
            if name_or_url == '':
                error = _('URL cannot be empty!')
                is_valid = False
            else:
                if name_or_url.lower().endswith('.git'):
                    try:
                        r = requests.head(name_or_url)
                        is_valid = r.status_code in [200, 301]
                    except Exception as e:
                        print(e)
                        is_valid = False
                        error = _('Write a valid url for the repository!')
                else:
                    is_valid = False
                    error = _('Valid url for the repository must end in `.git`!')

            path = self.location

        if path:
            self.text_location.setText(path)
    
        self.sig_validated.emit(is_valid, error)

        return is_valid, error

    def get_name(self):
        """"""
        return _('Create project from:')

    def create(self, context):
        """"""
        path = self.text_location.text()
        pref_idx = self.combo_project_preferences.currentIndex()
        preferences = self.combo_project_preferences.itemData(pref_idx) 

        if self.radio_from_vcs.isChecked():
            repo_url = self.text_project_name_or_url.text()
        else:
            repo_url = ''

        context['path'] = path
        context['preferences'] = preferences
        context['repository_url'] = repo_url

        # Fix this to make language independent
        context['project_type'] = self.combo_project_type.currentText()

        return context


class CondaProjectPage(BaseProjectPage):

    def setup_page(self):
        """"""
        self.label = QLabel(_("Select which type of conda environment "
                               "you want to use:<br>"))
        self.button_group = QButtonGroup(self)
        self.radio_use_project = QRadioButton(
            _("Use project environment"),
            self,
        )
        self.radio_use_existing = QRadioButton(
            _("Use existing conda environment"),
            self,
        )
        self.combobox = QComboBox(self)
        self.label_warning = QLabel()
        self.packages = PackagesWidget(self)

        # Widget setup
        self.packages.button_add.setDisabled(True)
        self.button_group.addButton(self.radio_use_project)
        self.button_group.addButton(self.radio_use_existing)
        envs = get_conda_environments()
        choices = [(osp.basename(env), env) for env in envs]
        for name, key in choices:
            if not (name is None and key is None):
                self.combobox.addItem(name, key)

        # Layouts
        layout = QGridLayout()
        layout.addWidget(self.label, 0, 0, 1, 2)
        layout.addWidget(self.radio_use_project, 1, 0, 1, 2)
        layout.addWidget(self.radio_use_existing, 2, 0)
        layout.addWidget(self.combobox, 2, 1)
        layout.addWidget(self.label_warning, 3, 0, 1, 2)
        layout.addWidget(self.packages, 4, 0, 1, 2)
        # layout.setRowStretch(4, 1000)
 
        self.setLayout(layout)

        # Signals
        self.button_group.buttonClicked.connect(self.validate)
        self.combobox.currentTextChanged.connect(self.validate)

    def get_name(self):
        """"""
        return _('Define Conda environment:')

    def validate(self):
        """"""
        error = ''
        if self.radio_use_existing.isChecked():
            self.combobox.setEnabled(True)
            self.packages.button_add.setDisabled(True)
            self.label_warning.setText(_('<i>Warning: This project is not reproducible!</i>'))
            prefix = self.combobox.itemData(self.combobox.currentIndex()) 
            packages = get_conda_packages(prefix)
            self.packages.clear()
            self.packages.add_packages(packages)
            is_valid = True
            error = ''
        elif self.radio_use_project.isChecked():
            self.combobox.setEnabled(False)
            self.packages.button_add.setDisabled(False)
            self.packages.clear()
            self.label_warning.setText('')
            is_valid = True
            error = ''
        else:
            self.combobox.setEnabled(False)
            self.packages.button_add.setDisabled(True)
            self.label_warning.setText('')
            is_valid = False
            error = _('Select an option!')

        self.sig_validated.emit(is_valid, error)
        return is_valid, error

    def create(self, context):
        """"""
        if self.radio_use_existing.isChecked():
            env = self.combobox.currentData()
            packages = []
        else:
            env = ''
            packages = self.packages.get_package_specs()
    
        context['conda_enviroment'] = env
        context['packages'] = packages

        return context


class ProjectDialog(QDialog):
    """Project creation dialog."""

    # Context with data from project creation
    sig_project_creation_requested = Signal(dict)

    def __init__(self, parent):
        """Project creation dialog."""
        super(ProjectDialog, self).__init__(parent=parent)
        self._invalid_index_start = -1

        # Widgets 
        self.label_title = QLabel()
        self.label_status = QLabel()
        self.pages_widget = QStackedWidget(self)
        self.page_general = GeneralProjectPage(self)
        self.page_conda = CondaProjectPage(self) if is_anaconda() else None
        self.button_select_location = QToolButton()
        self.button_cancel = QPushButton(_('Cancel'))
        self.button_previous = QPushButton(_('Previous'))
        self.button_next = QPushButton(_('Next'))
        self.button_create = QPushButton(_('Create'))

        self.bbox = QDialogButtonBox(Qt.Horizontal)
        self.bbox.addButton(self.button_cancel, QDialogButtonBox.ActionRole)
        self.bbox.addButton(self.button_previous, QDialogButtonBox.ActionRole)
        self.bbox.addButton(self.button_next, QDialogButtonBox.ActionRole)
        self.bbox.addButton(self.button_create, QDialogButtonBox.ActionRole)

        # Widget setup
        self.button_cancel.setDefault(True)
        self.button_cancel.setAutoDefault(True)
        self.setWindowTitle(_('Create new project'))
        for page in [self.page_general, self.page_conda]:
            if page:
                page.setup_page()
                self.add_page(page)

        self.button_previous.setEnabled(False)
        self.button_next.setEnabled(False)
        self.button_create.setEnabled(False)
        self.button_create.setVisible(False)
        self.setMinimumWidth(600)

        # Layouts
        layout = QVBoxLayout()
        layout.addWidget(self.label_title)
        layout.addWidget(self.pages_widget)
        layout.addWidget(self.label_status)
        layout.addSpacing(20)

        btnlayout = QHBoxLayout()
        btnlayout.addStretch(1)
        btnlayout.addWidget(self.bbox)

        layout.addLayout(btnlayout)
        self.setLayout(layout)

        # Signals
        self.button_cancel.clicked.connect(self.close)
        self.button_next.clicked.connect(self.next)
        self.button_previous.clicked.connect(self.previous)
        self.button_create.clicked.connect(self.create_project)
        self.pages_widget.currentChanged.connect(self.validate)
        self.page_general.sig_project_type_updated.connect(self.load_project_type)

        self.validate()

    def _refresh_buttons(self):
        """Update visibility and enabled state for buttons."""
        idx = self.pages_widget.currentIndex()
        is_first = idx == 0
        is_last = idx == (self.pages_widget.count() - 1)

        if is_first:
            self.button_create.setVisible(False)
            self.button_previous.setEnabled(False)
            self.button_next.setVisible(True)
            self.button_next.setEnabled(self._invalid_index_start != 0)
        elif is_last:
            self.button_next.setVisible(False)
            self.button_create.setVisible(True)
            self.button_previous.setEnabled(True)
        else:
            self.button_create.setVisible(False)
            self.button_previous.setEnabled(True)
            # Check if correct
            self.button_next.setEnabled(idx < self._invalid_index_start)
            self.button_next.setVisible(True)
            self.button_create.setVisible(False)

        self.button_create.setEnabled(self._is_project_valid())

    def _is_project_valid(self):
        """Check if all the tabs are valid."""
        for idx in range(self.pages_widget.count()):
            widget = self.pages_widget.widget(idx)

            widget.blockSignals(True)
            valid, _ = widget.validate()
            widget.blockSignals(False)
 
            if valid is False:
                return False

        return True

    def load_project_type(self, project):
        """"""
        print(project)
        # Remove the pages from 1 forward
        # Update any conda specific packages
        # Add any extra pages

    def add_page(self, widget):
        """Add a config page widget to the project dialog."""
        self.pages_widget.addWidget(widget)
        widget.sig_validated.connect(self.validate)

    def validate(self):
        """Validate the project options."""
        current_idx = self.pages_widget.currentIndex()
        name = self.pages_widget.currentWidget().get_name()
        self.label_title.setText('<b>{}</b>'.format(name))

        # Iterate from current tabs to see what pages need to be disabled
        for idx in range(self.pages_widget.count()):
            widget = self.pages_widget.widget(idx)
            widget.blockSignals(True)
            valid, error = widget.validate()
            widget.blockSignals(False)
            if valid is False:
                if current_idx == idx:
                    self.label_status.setText(
                        '<b>' + _('Warning: ') + '</b>{0}'.format(error))

                self._invalid_index_start = idx
                break
            else:
                self.label_status.setText('')
        else:
            self._invalid_index_start = idx

        self._refresh_buttons()

    def next(self):
        """Go to next page."""
        idx = self.pages_widget.currentIndex()
        is_last = idx == (self.pages_widget.count() - 1)
        if not is_last and idx <= self._invalid_index_start:
            self.pages_widget.setCurrentIndex(idx + 1)
        self._refresh_buttons()

    def previous(self):
        """Go to previous page."""
        idx = self.pages_widget.currentIndex()
        is_first = idx == 0
        if not is_first:
            self.pages_widget.setCurrentIndex(idx - 1)
        self._refresh_buttons()

    def create_project(self):
        """Create project."""
        context = {}
        for idx in range(self.pages_widget.count()):
            widget = self.pages_widget.widget(idx)
            context = widget.create(context)
            if not isinstance(context, dict):
                raise Exception(
                    'Project configuration context must be a dictionary!'
                )
        print(context)
        self.sig_project_creation_requested.emit(context)
        self.accept()


def test():
    """Local test."""
    from spyder.utils.qthelpers import qapplication
    app = qapplication()
    dlg = ProjectDialog(None)
    dlg.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    test()
