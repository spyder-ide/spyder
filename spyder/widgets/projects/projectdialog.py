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
from qtpy.QtWidgets import (QVBoxLayout, QLabel, QLineEdit, QPushButton,
                            QDialog, QComboBox, QGridLayout, QToolButton,
                            QDialogButtonBox, QGroupBox, QRadioButton,
                            QHBoxLayout)


# Local imports
from spyder.config.base import _, get_home_dir
from spyder.utils.qthelpers import get_std_icon
from spyder.py3compat import to_text_string
from spyder.widgets.projects import get_available_project_types


def is_writable(path):
    """Check if path has write access"""
    try:
        testfile = tempfile.TemporaryFile(dir=path)
        testfile.close()
    except OSError as e:
        if e.errno == errno.EACCES:  # 13
            return False
    return True


class ProjectDialog(QDialog):
    """Project creation dialog."""

    # path, type, packages
    sig_project_creation_requested = Signal(object, object, object)

    def __init__(self, parent):
        """Project creation dialog."""
        super(ProjectDialog, self).__init__(parent=parent)

        # Variables
        current_python_version = '.'.join([to_text_string(sys.version_info[0]),
                                           to_text_string(sys.version_info[1])])
        python_versions = ['2.7', '3.4', '3.5']
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
        self.button_cancel = QPushButton(_('Cancel'))
        self.button_create = QPushButton(_('Create'))

        self.bbox = QDialogButtonBox(Qt.Horizontal)
        self.bbox.addButton(self.button_cancel, QDialogButtonBox.ActionRole)
        self.bbox.addButton(self.button_create, QDialogButtonBox.ActionRole)

        # Widget setup
        self.combo_python_version.addItems(python_versions)
        self.radio_new_dir.setChecked(True)
        self.text_location.setEnabled(True)
        self.text_location.setReadOnly(True)
        self.button_select_location.setIcon(get_std_icon('DirOpenIcon'))
        self.button_cancel.setDefault(True)
        self.button_cancel.setAutoDefault(True)
        self.button_create.setEnabled(False)
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
        layout.addSpacing(20)
        layout.addWidget(self.bbox)

        self.setLayout(layout)

        # Signals and slots
        self.button_select_location.clicked.connect(self.select_location)
        self.button_create.clicked.connect(self.create_project)
        self.button_cancel.clicked.connect(self.close)
        self.radio_from_dir.clicked.connect(self.update_location)
        self.radio_new_dir.clicked.connect(self.update_location)
        self.text_project_name.textChanged.connect(self.update_location)

    def _get_project_types(self):
        """Get all available project types."""
        project_types = get_available_project_types()
        projects = []

        for project in project_types:
            projects.append(project.PROJECT_TYPE_NAME)

        return projects

    def select_location(self):
        """Select directory."""
        location = getexistingdirectory(self, _("Select directory"),
                                        self.location)
        if location:
            if is_writable(location):
                self.location = location
                self.update_location()

    def update_location(self, text=''):
        """Update text of location."""
        self.text_project_name.setEnabled(self.radio_new_dir.isChecked())
        name = self.text_project_name.text().strip()

        if name and self.radio_new_dir.isChecked():
            path = osp.join(self.location, name)
            self.button_create.setDisabled(os.path.isdir(path))
        elif self.radio_from_dir.isChecked():
            self.button_create.setEnabled(True)
            path = self.location
        else:
            self.button_create.setEnabled(False)
            path = self.location
        
        self.text_location.setText(path)
        
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
