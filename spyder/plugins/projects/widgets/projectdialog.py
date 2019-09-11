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
                            QHBoxLayout, QLabel, QLineEdit, QMessageBox,
                            QPushButton, QRadioButton, QScrollArea,
                            QStackedWidget, QToolButton, QVBoxLayout,
                            QWidget)
import requests

# Local imports
from spyder.config.base import _, get_home_dir
from spyder.plugins.projects.widgets import get_available_project_types
from spyder.py3compat import PY3, to_text_string
from spyder.utils import icon_manager as ima
from spyder.utils import programs
from spyder.utils.programs import is_anaconda, find_program
from spyder.utils.qthelpers import create_waitspinner, get_std_icon
from spyder.utils.workers import WorkerManager


class DummyWorker:
    pass


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
    """Main project creation page."""

    # This signal updates any custom pages of the dialog
    sig_project_type_updated = Signal(str)

    # Constants
    PROJECT_PREFERENCES = 'project'
    APPLICATION_PREFERENCES = 'application'

    def setup_page(self):
        """Main project creation page."""
        self.project_name = None
        self.location = get_home_dir()
        self._worker_manager = WorkerManager()
        self._last_validated_url = None
        self._last_validated_url_result = None

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
            _('Use application preferences'), self.APPLICATION_PREFERENCES)
        # To be enabled in the subsequent PR
        # self.combo_project_preferences.addItem(
        #     _('Use project preferences'), self.PROJECT_PREFERENCES)
        self.setWindowTitle(_('Create new project'))
        self.setMinimumWidth(500)
        self.radio_from_vcs.setEnabled(bool(find_program('git')))

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
        if location and location != '.':
            if is_writable(location):
                self.location = location
                self.text_location.setText(location)
                self.validate()

    def _validate_url(self, url):
        """Validate url for repository."""
        import time
        time.sleep(1)
        try:
            r = requests.head(url)
            is_valid = r.status_code in [200, 301]
        except Exception:
            is_valid = False
        return is_valid

    def _finished(self, worker, output, error):
        """Callback for worker."""
        self._last_validated_url_result = output
        if output:
            error = ''
        else:
            error = _('Write a valid url for the repository!') or error
        self.sig_validated.emit(output, error)

    def validate(self):
        """Validate the project status."""
        is_valid = False
        name_or_url = self.text_project_name_or_url.text().strip()
        path = None
        error = ''
        validating_text = _('Validating url...')

        self.text_project_name_or_url.setFocus()

        if self.radio_new_dir.isChecked():
            self.label_project_name_or_url.setDisabled(False)
            self.text_project_name_or_url.setDisabled(False)
            self.text_project_name_or_url.setVisible(True)
            self.text_project_name_or_url.setDisabled(False)
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
            self.text_project_name_or_url.setDisabled(True)
            self.text_project_name_or_url.setText('')
            self.label_project_name_or_url.setText('<p>' + '&nbsp;'*26 + '</p>')
            path = self.location
            is_valid = True
            self.button_select_location.setFocus()

        if self.radio_from_vcs.isChecked():
            self.label_project_name_or_url.setDisabled(False)
            self.text_project_name_or_url.setDisabled(False)
            self.text_project_name_or_url.setDisabled(False)
            self.label_project_name_or_url.setText(_('Repository URL'))
            if name_or_url == '':
                is_valid = False
                error = _('URL cannot be empty!')
            else:
                if name_or_url.lower().endswith('.git'):
                    if self._last_validated_url != name_or_url:
                        # Reset values
                        self._last_validated_url = name_or_url
                        self._last_validated_url_result = None

                        if not self._worker_manager.is_busy():
                            worker = self._worker_manager.create_python_worker(
                                self._validate_url, name_or_url)
                            worker.sig_finished.connect(self._finished)
                            worker.start()
                            is_valid = None
                            error = validating_text
                        else:
                            is_valid = None
                            error = validating_text
                    else:
                        is_valid = self._last_validated_url_result
                        error = '' if is_valid else validating_text
                else:
                    is_valid = False
                    error = _('Valid url for the repository must end in `.git`!')

            path = self.location

        if path:
            self.text_location.setText(path)
    
        self.sig_validated.emit(is_valid, error)

        return is_valid, error

    def get_name(self):
        """Return the project name."""
        return _('Create project from:')

    def create(self, context):
        """
        Create project.

        This method only performs actions on the context dictionary.
        The plugin will be in charge of actually performing the final actions.
        """
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

        # TODO: Make language independent on future PR
        context['project_type'] = self.combo_project_type.currentText()

        return context


class ProjectDialog(QDialog):
    """Project creation dialog."""

    # Context with data from project creation
    sig_project_created = Signal(dict)

    def __init__(self, parent):
        """Project creation dialog."""
        super(ProjectDialog, self).__init__(parent=parent)
        self._invalid_index_start = -1

        # Widgets 
        self.spinner = create_waitspinner(size=16, parent=self)
        self.label_title = QLabel()
        self.label_status = QLabel()
        self._worker_manager = WorkerManager()

        self.pages_widget = QStackedWidget(self)
        self.page_general = GeneralProjectPage(self)

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
        for page in [self.page_general]:
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
        layout_status = QHBoxLayout()
        layout_status.addWidget(self.label_status)
        layout_status.addWidget(self.spinner)
        layout_status.addStretch()
        layout.addLayout(layout_status)
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
        self.page_general.sig_validated.connect(self.validate)
        self.page_general.sig_project_type_updated.connect(self.load_project_type)

        self.validate()

    def _refresh_buttons(self):
        """Update visibility and enabled state for buttons."""
        idx = self.pages_widget.currentIndex()
        is_first = idx == 0
        is_last = idx == (self.pages_widget.count() - 1)

        if is_last and is_first:
            self.button_previous.setVisible(False)

        if is_last:
            self.button_next.setVisible(False)
            self.button_create.setVisible(True)
            self.button_previous.setEnabled(True)
        elif is_first:
            self.button_create.setVisible(False)
            self.button_previous.setEnabled(False)
            self.button_next.setVisible(True)
            self.button_next.setEnabled(self._invalid_index_start != 0)
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
            if valid in [False, None]:
                return False

        return True

    def load_project_type(self, project):
        """Load project type additional pages if any."""
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
        self._invalid_index_start = None
        for idx in range(self.pages_widget.count()):
            widget = self.pages_widget.widget(idx)
            widget.blockSignals(True)
            valid, error = widget.validate()
            widget.blockSignals(False)
            if valid is None:
                self.spinner.start()
                if current_idx == idx:
                    self.label_status.setText(
                        '<b>' + _('Status: ') + '</b>{0}'.format(error))
                self._invalid_index_start = idx
                break
            elif valid is False:
                self.spinner.stop()
                if current_idx == idx:
                    self.label_status.setText(
                        '<b>' + _('Warning: ') + '</b>{0}'.format(error))

                self._invalid_index_start = idx
                break
            else:
                self.spinner.stop()
                self.label_status.setText('')
        else:
            self.spinner.stop()
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
        self.spinner.start()
        context = {}
        for idx in range(self.pages_widget.count()):
            widget = self.pages_widget.widget(idx)
            context = widget.create(context)
            if not isinstance(context, dict):
                raise Exception(
                    'Project configuration context must be a dictionary!'
                )
        self._create_project(context)

    def _create_project(self, context):
        """Create a new project."""
        self.label_status.setText('Creating project')
        self.button_create.setDisabled(True)
        repository_url = context['repository_url']
        path = context['path']
        self.pages_widget.setDisabled(True)

        if repository_url:
            git = find_program('git')
            worker = self._worker_manager.create_process_worker(
                [git, 'clone', repository_url], cwd=path)
            worker.context = context
            worker.sig_partial.connect(self._project_creation_partial)
            worker.sig_finished.connect(self._project_creation_finished)
            worker.start()
        else:
            worker = DummyWorker()
            worker.context = context
            self._project_creation_finished(worker, None, None)

        self._is_busy = True

    def _project_creation_partial(self, worker, output, error):
        """Callback for worker partial status."""
        error_lines = error.split('\n') if error else []
        error_lines = [line for line in error_lines if line.strip()]
        self.label_status.setText(error_lines[-1])

    def _project_creation_finished(self, worker, output, error):
        """Callback for worker."""
        self._is_busy = False
        self.spinner.stop()
        self.button_create.setDisabled(False)

        error_lines = error.split('\n') if error else []
        error_lines = [line for line in error_lines if line.strip()]
        context = worker.context

        if any(['fatal' in line for line in error_lines]):
            self.pages_widget.setDisabled(False)
            self.label_status.setText(error_lines[-1])
        else:
            self.label_status.setText('')
            url = context['repository_url']
            url = url.split('/')[-1]
            folder = url.split('.git')[0]
            context['path'] = os.path.join(context['path'], folder)
            self.sig_project_created.emit(worker.context)
            if not self._is_asking:
                self.accept()

    def close(self):
        """Override Qt method."""
        if self._is_busy:
            # Confirm closing
            self._is_asking = True
            answer = QMessageBox.warning(
                self,
                _("Warning"),
                (_("Spyder is in the process of creating a project") + '<br><br>' +
                 _("Do you want to abort?")),
                QMessageBox.Yes | QMessageBox.No)

        if answer == QMessageBox.Yes or not self._is_busy:
            self._worker_manager.terminate_all()
            super(ProjectDialog, self).reject()
        else:
            super(ProjectDialog, self).close()


def test():
    """Local test."""
    from spyder.utils.qthelpers import qapplication
    app = qapplication()
    dlg = ProjectDialog(None)
    dlg.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    test()
