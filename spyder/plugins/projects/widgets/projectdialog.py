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
import sys
import tempfile

# Third party imports
from qtpy.compat import getexistingdirectory
from qtpy.QtCore import Qt, Signal
from qtpy.QtGui import QIcon
from qtpy.QtWidgets import (QVBoxLayout, QLabel, QLineEdit, QPushButton,
                            QDialog, QComboBox, QGridLayout, QToolButton,
                            QDialogButtonBox, QGroupBox, QRadioButton,
                            QHBoxLayout, QTabWidget, QWidget, QScrollArea,
                            QButtonGroup, QRadioButton)


# Local imports
from spyder.config.base import _, get_home_dir
from spyder.utils import icon_manager as ima
from spyder.utils.qthelpers import get_std_icon
from spyder.py3compat import to_text_string
from spyder.plugins.projects.widgets import get_available_project_types


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
    """"""
    sig_validated = Signal()

    def __init__(self, parent=None):
        """"""
        super(BaseProjectPage, self).__init__(parent=parent)
        self._parent = parent

    def setup_page(self):
        """"""

    def get_name(self):
        """Return the page name."""
        return None

    def get_icon(self):
        """Return the page icon."""
        return ima.icon('genprefs')

    def validate(self):
        """Validate the project page."""
        raise NotImplementedError


class GeneralProjectPage(BaseProjectPage):

    def setup_page(self):
        """"""
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
        self.setFixedWidth(500)
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
        self.button_select_location.clicked.connect(self.validate)
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

    def select_location(self):
        """Select directory."""
        location = osp.normpath(getexistingdirectory(self,
                                                     _("Select directory"),
                                                     self.location))

        if location:
            if is_writable(location):
                self.location = location
                self.update_location()

    def validate(self):
        """Update text of location."""
        self.text_project_name.setEnabled(self.radio_new_dir.isChecked())
        name = self.text_project_name.text().strip()

        if name and self.radio_new_dir.isChecked():
            path = osp.join(self.location, name)
        elif self.radio_from_dir.isChecked():
            path = self.location
        else:
            path = self.location

        self.text_location.setText(path)

        if path:
            self.sig_validated.emit()

    def get_name(self):
        """Return the page name."""
        return _('Type')


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
        # Widget setup
        self.button_group.addButton(self.radio_use_project)
        self.button_group.addButton(self.radio_use_existing)

        # Layouts
        layout = QVBoxLayout()
        layout.addWidget(self.label)
        layout.addWidget(self.radio_use_project)
        layout.addWidget(self.radio_use_existing)
        layout.addStretch()
        self.setLayout(layout)

    def get_name(self):
        """Return the page name."""
        return _('Conda')


class VersionProjectPage(BaseProjectPage):

    def setup_page(self):
        """"""
        vcs_group = QGroupBox(_("Version Control"))
        vcs_button_group = QButtonGroup(vcs_group)
        vcs_label = QLabel(_("Select if you want to use git version control "
                             "for the project:"))
        self.radio_vcs_disabled = QRadioButton(
            _("Do not use"),
            self,
        )
        self.radio_vcs_existing = QRadioButton(
            _("Use existing repository in project folder"), self,
        )
        self.radio_vcs_init = QRadioButton(
            _("Initialize a local repository for the project"), self,
        )
        self.radio_vcs_clone = QRadioButton(
            _("Clone from existing project"), self,
        )
        self.line_repository = QLineEdit(
            _(""),
        )

        vcs_layout = QVBoxLayout()
        vcs_layout.addWidget(vcs_label)
        vcs_layout.addWidget(self.radio_vcs_disabled)
        vcs_layout.addWidget(self.radio_vcs_init)
        vcs_layout.addWidget(self.radio_vcs_existing)
        vcs_layout.addWidget(self.radio_vcs_clone)
        vcs_layout.addWidget(self.line_repository)
        vcs_group.setLayout(vcs_layout)

        vlayout = QVBoxLayout()
        vlayout.addWidget(vcs_group)
        vlayout.addStretch(1)
        self.setLayout(vlayout)

    def get_name(self):
        """Return the page name."""
        return _('Version')


class ProjectDialog(QDialog):
    """Project creation dialog."""

    # path, type, packages
    sig_project_creation_requested = Signal(object, object, object)

    def __init__(self, parent):
        """Project creation dialog."""
        super(ProjectDialog, self).__init__(parent=parent)

        # Variables
        self.pages = []

        # Widgets 
        self.pages_widget = QTabWidget(self)
        self.page_general = GeneralProjectPage(self)
        self.page_vcs = VersionProjectPage(self)
        self.page_conda = CondaProjectPage(self)
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
            page.setup_page()
            self.add_page(page)
        self.pages_widget.setTabEnabled(1, False)
        self.pages_widget.setTabEnabled(2, False)

        self.button_previous.setVisible(False)
        self.button_create.setVisible(False)
        self.button_next.setEnabled(False)

        # Layouts
        layout = QVBoxLayout()
        layout.addWidget(self.pages_widget)
        layout.addWidget(self.bbox)
        self.setLayout(layout)

        # Signals
        self.button_create.clicked.connect(self.create_project)
        self.button_cancel.clicked.connect(self.close)

    def setup_pages(self):
        """"""

    def add_page(self, widget):
        """"""
        # self.check_settings.connect(widget.check_settings)
        # widget.show_this_page.connect(lambda row=self.contents_widget.count():
        #                               self.contents_widget.setCurrentRow(row))
        # widget.apply_button_enabled.connect(self.apply_btn.setEnabled)
        # scrollarea = QScrollArea(self)
        # scrollarea.setWidgetResizable(True)
        # scrollarea.setWidget(widget)
        # self.pages_widget.addWidget(scrollarea)
        self.pages_widget.addTab(widget, widget.get_name())
        widget.sig_validated.connect(self.validate)

        # item = QListWidgetItem(self.contents_widget)
        # try:
        #     item.setIcon(widget.get_icon())
        # except TypeError:
        #     pass
        # item.setText(widget.get_name())
        # item.setFlags(Qt.ItemIsSelectable|Qt.ItemIsEnabled)
        # item.setSizeHint(QSize(0, 25))

    def validate(self):
        """"""
        idx = self.pages_widget.currentIndex()

    def create_project(self):
        """Create project."""
        packages = ['python={0}'.format(self.combo_python_version.currentText())]
        self.sig_project_creation_requested.emit(
            self.text_location.text(),
            self.combo_project_type.currentText(),
            packages)
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
