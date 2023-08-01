# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright © Spyder Project Contributors
#
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)
# -----------------------------------------------------------------------------
"""Project creation dialog."""

# Standard library imports
import errno
import os.path as osp
import sys
import tempfile

# Third party imports
from qtpy.compat import getexistingdirectory
from qtpy.QtCore import Qt, Signal
from qtpy.QtWidgets import (QComboBox, QDialog, QDialogButtonBox, QGridLayout,
                            QGroupBox, QHBoxLayout, QLabel, QLineEdit,
                            QPushButton, QRadioButton, QVBoxLayout)

# Local imports
from spyder.config.base import _, get_home_dir
from spyder.utils.icon_manager import ima
from spyder.utils.qthelpers import create_toolbutton


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

    sig_project_creation_requested = Signal(str, str, object)
    """
    This signal is emitted to request the Projects plugin the creation of a
    project.

    Parameters
    ----------
    project_path: str
        Location of project.
    project_type: str
        Type of project as defined by project types.
    project_packages: object
        Package to install. Currently not in use.
    """

    def __init__(self, parent, project_types):
        """Project creation dialog."""
        super(ProjectDialog, self).__init__(parent=parent)
        self.plugin = parent
        self._project_types = project_types
        self.project_data = {}

        self.setWindowFlags(
            self.windowFlags() & ~Qt.WindowContextHelpButtonHint)

        self.project_name = None
        self.location = get_home_dir()

        # Widgets
        projects_url = "http://docs.spyder-ide.org/current/panes/projects.html"
        self.description_label = QLabel(
            _("Select a new or existing directory to create a new Spyder "
              "project in it. To learn more about projects, take a look at "
              "our <a href=\"{0}\">documentation</a>.").format(projects_url)
        )
        self.description_label.setOpenExternalLinks(True)
        self.description_label.setWordWrap(True)

        self.groupbox = QGroupBox()
        self.radio_new_dir = QRadioButton(_("New directory"))
        self.radio_from_dir = QRadioButton(_("Existing directory"))

        self.label_project_name = QLabel(_('Project name'))
        self.label_location = QLabel(_('Location'))
        self.label_project_type = QLabel(_('Project type'))

        self.text_project_name = QLineEdit()
        self.text_location = QLineEdit(get_home_dir())
        self.combo_project_type = QComboBox()

        self.label_information = QLabel("")
        self.label_information.hide()

        self.button_select_location = create_toolbutton(
            self,
            triggered=self.select_location,
            icon=ima.icon('DirOpenIcon'),
            tip=_("Select directory")
        )
        self.button_cancel = QPushButton(_('Cancel'))
        self.button_create = QPushButton(_('Create'))

        self.bbox = QDialogButtonBox(Qt.Horizontal)
        self.bbox.addButton(self.button_cancel, QDialogButtonBox.ActionRole)
        self.bbox.addButton(self.button_create, QDialogButtonBox.ActionRole)

        # Widget setup
        self.radio_new_dir.setChecked(True)
        self.text_location.setEnabled(True)
        self.text_location.setReadOnly(True)
        self.button_cancel.setDefault(True)
        self.button_cancel.setAutoDefault(True)
        self.button_create.setEnabled(False)
        for (id_, name) in [(pt_id, pt.get_name()) for pt_id, pt
                            in project_types.items()]:
            self.combo_project_type.addItem(name, id_)

        self.setWindowTitle(_('Create new project'))

        # Layouts
        layout_top = QHBoxLayout()
        layout_top.addWidget(self.radio_new_dir)
        layout_top.addSpacing(15)
        layout_top.addWidget(self.radio_from_dir)
        layout_top.addSpacing(200)
        self.groupbox.setLayout(layout_top)

        layout_grid = QGridLayout()
        layout_grid.addWidget(self.label_project_name, 0, 0)
        layout_grid.addWidget(self.text_project_name, 0, 1, 1, 2)
        layout_grid.addWidget(self.label_location, 1, 0)
        layout_grid.addWidget(self.text_location, 1, 1)
        layout_grid.addWidget(self.button_select_location, 1, 2)
        layout_grid.addWidget(self.label_project_type, 2, 0)
        layout_grid.addWidget(self.combo_project_type, 2, 1, 1, 2)
        layout_grid.addWidget(self.label_information, 3, 0, 1, 3)

        layout = QVBoxLayout()
        layout.addWidget(self.description_label)
        layout.addSpacing(3)
        layout.addWidget(self.groupbox)
        layout.addSpacing(8)
        layout.addLayout(layout_grid)
        layout.addSpacing(8)
        layout.addWidget(self.bbox)
        layout.setSizeConstraint(layout.SetFixedSize)

        self.setLayout(layout)

        # Signals and slots
        self.button_create.clicked.connect(self.create_project)
        self.button_cancel.clicked.connect(self.close)
        self.radio_from_dir.clicked.connect(self.update_location)
        self.radio_new_dir.clicked.connect(self.update_location)
        self.text_project_name.textChanged.connect(self.update_location)

    def select_location(self):
        """Select directory."""
        location = osp.normpath(
            getexistingdirectory(
                self,
                _("Select directory"),
                self.location,
            )
        )

        if location and location != '.':
            if is_writable(location):
                self.location = location
                self.text_project_name.setText(osp.basename(location))
                self.update_location()

    def update_location(self, text=''):
        """Update text of location and validate it."""
        msg = ''
        path_validation = False
        path = self.location
        name = self.text_project_name.text().strip()

        # Setup
        self.text_project_name.setEnabled(self.radio_new_dir.isChecked())
        self.label_information.setText('')
        self.label_information.hide()

        if name and self.radio_new_dir.isChecked():
            # Allow to create projects only on new directories.
            path = osp.join(self.location, name)
            path_validation = not osp.isdir(path)
            if not path_validation:
                msg = _("This directory already exists!")
        elif self.radio_from_dir.isChecked():
            # Allow to create projects in current directories that are not
            # Spyder projects.
            path = self.location
            path_validation = not osp.isdir(osp.join(path, '.spyproject'))
            if not path_validation:
                msg = _("This directory is already a Spyder project!")

        # Set path in text_location
        self.text_location.setText(path)

        # Validate project name with the method from the currently selected
        # project.
        project_type_id = self.combo_project_type.currentData()
        validate_func = self._project_types[project_type_id].validate_name
        project_name_validation, project_msg = validate_func(path, name)
        if not project_name_validation:
            if msg:
                msg = msg + '\n\n' + project_msg
            else:
                msg = project_msg

        # Set message
        if msg:
            self.label_information.show()
            self.label_information.setText('\n' + msg)

        # Allow to create project if validation was successful
        validated = path_validation and project_name_validation
        self.button_create.setEnabled(validated)

        # Set default state of buttons according to validation
        # Fixes spyder-ide/spyder#16745
        if validated:
            self.button_create.setDefault(True)
            self.button_create.setAutoDefault(True)
        else:
            self.button_cancel.setDefault(True)
            self.button_cancel.setAutoDefault(True)

    def create_project(self):
        """Create project."""
        self.project_data = {
            "root_path": self.text_location.text(),
            "project_type": self.combo_project_type.currentData(),
        }
        self.sig_project_creation_requested.emit(
            self.text_location.text(),
            self.combo_project_type.currentData(),
            [],
        )
        self.accept()


def test():
    """Local test."""
    from spyder.utils.qthelpers import qapplication
    from spyder.plugins.projects.api import BaseProjectType

    class MockProjectType(BaseProjectType):

        @staticmethod
        def get_name():
            return "Boo"

        @staticmethod
        def validate_name(path, name):
            return False, "BOOM!"

    app = qapplication()
    dlg = ProjectDialog(None, {"empty": MockProjectType})
    dlg.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    test()
