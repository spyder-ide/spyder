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
                            QRadioButton, QScrollArea, QTabWidget, QToolButton,
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
from spyder.utils.vcs import git_init, git_clone


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
        Actions to execute for project creation.

        This method has to return the context dictionary.
        """
        return context


class GeneralProjectPage(BaseProjectPage):

    def setup_page(self):
        current_python_version = '.'.join([to_text_string(sys.version_info[0]),
                                           to_text_string(sys.version_info[1])])
        python_versions = ['2.7', '3.6', '3.7']
        if current_python_version not in python_versions:
            python_versions.append(current_python_version)
            python_versions = sorted(python_versions)

        self.project_name = None
        self.location = get_home_dir()

        # Widgets
        self.groupbox = QGroupBox()
        self.radio_new_dir = QRadioButton(_("New directory"))
        self.radio_from_dir = QRadioButton(_("Existing directory"))

        self.label_project_name = QLabel(_('Project name'))
        self.label_location = QLabel(_('Location'))
        self.label_project_type = QLabel(_('Project type'))
        self.label_python_version = QLabel(_('Python version'))

        self.text_project_name = QLineEdit()
        self.text_location = QLineEdit(get_home_dir())
        self.combo_project_type = QComboBox()
        self.combo_python_version = QComboBox()
        self.button_select_location = QToolButton()

        # Widget setup
        self.combo_python_version.addItems(python_versions)
        self.radio_new_dir.setChecked(True)
        self.text_location.setEnabled(True)
        self.text_location.setReadOnly(True)
        self.button_select_location.setIcon(get_std_icon('DirOpenIcon'))
        self.combo_project_type.addItems(self._get_project_types())
        self.combo_python_version.setCurrentIndex(
            python_versions.index(current_python_version))
        self.setWindowTitle(_('Create new project'))
        self.setMinimumWidth(500)
        self.label_python_version.setVisible(False)
        self.combo_python_version.setVisible(False)

        # Layouts
        layout_top = QHBoxLayout()
        layout_top.addWidget(self.radio_new_dir)
        layout_top.addWidget(self.radio_from_dir)
        layout_top.addStretch(1)
        self.groupbox.setLayout(layout_top)

        layout_grid = QGridLayout()
        layout_grid.addWidget(self.label_project_name, 0, 0)
        layout_grid.addWidget(self.text_project_name, 0, 1, 1, 2)
        layout_grid.addWidget(self.label_location, 1, 0)
        layout_grid.addWidget(self.text_location, 1, 1)
        layout_grid.addWidget(self.button_select_location, 1, 2)
        layout_grid.addWidget(self.label_project_type, 2, 0)
        layout_grid.addWidget(self.combo_project_type, 2, 1, 1, 2)
        layout_grid.addWidget(self.label_python_version, 3, 0)
        layout_grid.addWidget(self.combo_python_version, 3, 1, 1, 2)

        layout = QVBoxLayout()
        layout.addWidget(self.groupbox)
        layout.addSpacing(10)
        layout.addLayout(layout_grid)
        layout.addStretch()
        self.setLayout(layout)

        # Signals and slots
        self.button_select_location.clicked.connect(self._select_location)
        self.radio_from_dir.clicked.connect(self.validate)
        self.radio_new_dir.clicked.connect(self.validate)
        self.text_project_name.textChanged.connect(self.validate)

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
        self.text_project_name.setEnabled(self.radio_new_dir.isChecked())
        name = self.text_project_name.text().strip()
        path = None
        error = ''

        if name and self.radio_new_dir.isChecked():
            path = osp.join(self.location, name)
            if osp.isdir(path):
                error = _('Directory already exists!')
                is_valid = False
            else:
                is_valid = True
        elif self.radio_from_dir.isChecked():
            path = self.location
            is_valid = True

        if path:
            self.text_location.setText(path)
    
        self.sig_validated.emit(is_valid, error)

        return is_valid, error

    def get_name(self):
        return _('Type')

    def create(self, context):
        from anaconda_project.api import AnacondaProject
        path = self.text_location.text()
        os.makedirs(path)
        aproj = AnacondaProject()
        project = aproj.create_project(path, make_directory=False)

        context['path'] = path
        context['project'] = project

        return context


class CondaProjectPage(BaseProjectPage):

    def setup_page(self):
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

        # Widget setup
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
        layout.setRowStretch(4, 1000)
 
        self.setLayout(layout)

        # Signals
        self.button_group.buttonClicked.connect(self.validate)

    def get_name(self):
        return _('Conda')

    def validate(self):
        error = ''
        if self.radio_use_existing.isChecked():
            self.combobox.setEnabled(True)
            self.label_warning.setText(_('This project is not reproducible!'))
            is_valid = True
            error = ''
        elif self.radio_use_project.isChecked():
            self.combobox.setEnabled(False)
            self.label_warning.setText('')
            is_valid = True
            error = ''
        else:
            self.combobox.setEnabled(False)
            self.label_warning.setText('')
            is_valid = False
            error = 'Select an option!'

        self.sig_validated.emit(is_valid, error)
        return is_valid, error

    def create(self, context):
        if self.radio_use_existing.isChecked():
            env = self.combobox.currentData()
        else:
            env = ''
    
        context['conda_enviroment'] = env

        return context


class VersionProjectPage(BaseProjectPage):

    def setup_page(self):
        self.button_group = QButtonGroup(self)
        vcs_label = QLabel(_("Select the version control settings "
                             "for the project:"))
        self.radio_vcs_disabled = QRadioButton(_("Do not use version control"), self,)
        self.radio_vcs_init = QRadioButton(
            _("Initialize a local git repository for the project"), self,
        )
        self.radio_vcs_clone = QRadioButton(
            _("Clone from existing git project"), self,
        )
        self.line_repository = QLineEdit()

        # Widget setup
        self.button_group.addButton(self.radio_vcs_disabled)
        self.button_group.addButton(self.radio_vcs_init)
        self.button_group.addButton(self.radio_vcs_clone)

        # Layouts
        layout = QVBoxLayout()
        layout.addWidget(vcs_label)
        layout.addWidget(self.radio_vcs_disabled)
        layout.addWidget(self.radio_vcs_init)
        layout.addWidget(self.radio_vcs_clone)
        layout.addWidget(self.line_repository)
        layout.addStretch(1)
        self.setLayout(layout)

        # Signals
        self.button_group.buttonClicked.connect(self.validate)
        self.line_repository.textChanged.connect(self.validate)

    def validate(self):
        error = ''
        if self.radio_vcs_clone.isChecked():
            self.line_repository.setEnabled(True)
            repo = self.line_repository.text()
            if repo:
                try:
                    r = requests.head(repo)
                    is_valid = r.status_code in [200, 301]
                except Exception as e:
                    print(e)
                    is_valid = False
                    error = 'Write a valid url for the repository!'
            else:
                is_valid = False
                error = 'Write a valid url for the repository!'
        elif self.radio_vcs_init.isChecked():
            is_valid = True
            self.line_repository.setEnabled(False)
        elif self.radio_vcs_disabled.isChecked():
            is_valid = True
            self.line_repository.setEnabled(False)
        else:
            is_valid = False
            self.line_repository.setEnabled(False)
            error = 'Select an option!'

        self.sig_validated.emit(is_valid, error)
        return is_valid, error

    def get_name(self):
        return _('Version')

    def create(self, context):
        path = context.get('path', None)
        repo = self.line_repository.text()
        context['repository'] = repo

        if path:
            if self.radio_vcs_init.isChecked():
                git_init(path)
            elif self.radio_vcs_clone.isChecked():
                git_clone(path, repo)

        return context


class ProjectDialog(QDialog):
    """Project creation dialog."""

    # Context with data from project creation
    sig_project_creation_requested = Signal(dict)

    def __init__(self, parent):
        """Project creation dialog."""
        super(ProjectDialog, self).__init__(parent=parent)

        # Widgets 
        self.label_status = QLabel()
        self.pages_widget = QTabWidget(self)
        self.page_general = GeneralProjectPage(self)
        self.page_vcs = VersionProjectPage(self)
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
        for page in [self.page_general, self.page_conda, self.page_vcs]:
            if page:
                page.setup_page()
                self.add_page(page)
        self.pages_widget.setTabEnabled(1, False)
        self.pages_widget.setTabEnabled(2, False)

        self.button_previous.setEnabled(False)
        self.button_next.setEnabled(False)
        self.button_create.setEnabled(False)
        self.button_create.setVisible(False)

        # Layouts
        layout = QVBoxLayout()
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

    def _refresh_buttons(self):
        """Update visibility and enabled state for buttons."""
        idx = self.pages_widget.currentIndex()
        is_first = idx == 0
        is_last = idx == (self.pages_widget.count() - 1)
        if is_first:
            self.button_create.setVisible(False)
            self.button_previous.setEnabled(False)
            self.button_next.setVisible(True)
            self.button_next.setEnabled(self.pages_widget.isTabEnabled(idx + 1))
        elif is_last:
            self.button_next.setVisible(False)
            self.button_create.setVisible(True)
        else:
            self.button_create.setVisible(False)
            self.button_previous.setEnabled(True)
            self.button_next.setEnabled(self.pages_widget.isTabEnabled(idx + 1))
            self.button_next.setVisible(True)
            self.button_create.setVisible(False)

        self.button_create.setEnabled(self._is_project_valid())

    def _is_project_valid(self):
        """Check if all the tabs are valid."""
        for idx in range(self.pages_widget.count()):
            widget = self.pages_widget.widget(idx)
            widget_enabled = self.pages_widget.isTabEnabled(idx)

            widget.blockSignals(True)
            valid, _ = widget.validate()
            widget.blockSignals(False)
 
            if valid is False or not widget_enabled:
                return False

        return True

    def add_page(self, widget):
        """Add a config page widget to the project dialog."""
        count = self.pages_widget.count()
        self.pages_widget.addTab(
            widget, '{}: {}'.format(count + 1, widget.get_name()))
        widget.sig_validated.connect(self.validate)

    def validate(self):
        """Validate the project options."""
        current_idx = self.pages_widget.currentIndex()
        # Iterate from current tabs to see what pages need to be disabled
        for idx in range(self.pages_widget.count()):
            widget = self.pages_widget.widget(idx)
            widget.blockSignals(True)
            valid, error = widget.validate()
            widget.blockSignals(False)
            if valid is False:
                if current_idx == idx:
                    self.label_status.setText(error)

                invalid_index_start = idx + 1
                break
            else:
                self.label_status.setText('')
        else:
            invalid_index_start = idx + 1

        # All pages after this one are invalid
        for idx in range(invalid_index_start, self.pages_widget.count()):
            self.pages_widget.setTabEnabled(idx, False)

        # All pages before this one are valid
        for idx in range(invalid_index_start):
            self.pages_widget.setTabEnabled(idx, True)

        self._refresh_buttons()

    def next(self):
        """Go to next page."""
        idx = self.pages_widget.currentIndex()
        is_last = idx == (self.pages_widget.count() - 1)
        if not is_last and self.pages_widget.isTabEnabled(idx + 1):
            self.pages_widget.setCurrentIndex(idx + 1)
        self._refresh_buttons()

    def previous(self):
        """Go to previous page."""
        idx = self.pages_widget.currentIndex()
        is_first = idx == 0
        if not is_first and self.pages_widget.isTabEnabled(idx - 1):
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
        self.sig_project_creation_requested.emit(context)
        print(context)
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
