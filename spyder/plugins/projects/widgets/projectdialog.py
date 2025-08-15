# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright © Spyder Project Contributors
#
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)
# -----------------------------------------------------------------------------
"""Project creation dialog."""

# Standard library imports
from __future__ import annotations
import os
import os.path as osp
import re
from pathlib import Path
import sys
from typing import TypedDict

# Third party imports
from qtpy.QtCore import Qt, Signal
from qtpy.QtWidgets import (
    QDialogButtonBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
)

# Local imports
from spyder.api.fonts import SpyderFontType, SpyderFontsMixin
from spyder.api.translations import _
from spyder.api.widgets.dialogs import SpyderDialogButtonBox
from spyder.plugins.projects.api import EmptyProject
from spyder.utils.icon_manager import ima
from spyder.utils.stylesheet import AppStyle, MAC, WIN
from spyder.widgets.config import SpyderConfigPage
from spyder.widgets.sidebardialog import SidebarDialog
from spyder.widgets.helperwidgets import MessageLabel


# =============================================================================
# ---- Auxiliary functions and classes
# =============================================================================
def is_writable(path):
    """
    Check if path has write access.

    Solution taken from https://stackoverflow.com/a/11170037
    """
    filepath = osp.join(path, "__spyder_write_test__.txt")

    try:
        filehandle = open(filepath, 'w')
        filehandle.close()
        os.remove(filepath)
    except (FileNotFoundError, PermissionError):
        return False

    return True


class ValidationReasons(TypedDict):
    missing_info: bool | None
    no_location: bool | None
    location_exists: bool | None
    location_not_writable: bool | None
    spyder_project_exists: bool | None
    wrong_name: bool | None


# =============================================================================
# ---- Pages
# =============================================================================
class BaseProjectPage(SpyderConfigPage, SpyderFontsMixin):
    """Base project page."""

    # SidebarPage API
    MIN_HEIGHT = 300
    MAX_WIDTH = 430 if MAC else (400 if WIN else 420)

    # SpyderConfigPage API
    LOAD_FROM_CONFIG = False

    # Own API
    LOCATION_TEXT = _("Location")
    LOCATION_TIP = None

    def __init__(self, parent):
        super().__init__(parent)

        self._location = self.create_browsedir(
            text=self.LOCATION_TEXT,
            option=None,
            alignment=Qt.Vertical,
            tip=self.LOCATION_TIP,
            status_icon=ima.icon("error"),
        )

        self._validation_label = MessageLabel(self)
        self._validation_label.setVisible(False)

        self._description_font = self.get_font(SpyderFontType.Interface)
        self._description_font.setPointSize(
            self._description_font.pointSize() + 1
        )

    # ---- Public API
    # -------------------------------------------------------------------------
    @property
    def project_location(self):
        """Where the project is going to be created."""
        raise NotImplementedError

    def validate_page(self):
        """Actions to take to validate the page contents."""
        raise NotImplementedError

    @property
    def project_type(self):
        """Project type associated to this page."""
        return EmptyProject

    # ---- Private API
    # -------------------------------------------------------------------------
    def _validate_location(
        self,
        location: str,
        reasons: ValidationReasons | None = None,
        name: str | None = None
    ) -> ValidationReasons:

        if reasons is None:
            reasons: ValidationReasons = {}

        if not location:
            self._location.status_action.setVisible(True)
            self._location.status_action.setToolTip(_("This is empty"))
            reasons["missing_info"] = True
        elif not osp.isdir(location):
            self._location.status_action.setVisible(True)
            self._location.status_action.setToolTip(
                _("This directory doesn't exist")
            )
            reasons["no_location"] = True
        elif not is_writable(location):
            self._location.status_action.setVisible(True)
            self._location.status_action.setToolTip(
                _("This directory is not writable")
            )
            reasons["location_not_writable"] = True
        elif os.name == "nt" and any(
            [re.search(r":", part) for part in Path(location).parts[1:]]
        ):
            # Prevent creating a project in directory with colons.
            # Fixes spyder-ide/spyder#16942
            reasons["wrong_name"] = True
        elif name is not None:
            project_path = osp.join(location, name)
            if os.name == "nt" and re.search(r":", name):
                # Prevent creating a project in directory with colons.
                # Fixes spyder-ide/spyder#16942
                reasons["wrong_name"] = True
            if osp.isdir(project_path):
                reasons["location_exists"] = True
        else:
            spyproject_path = osp.join(location, '.spyproject')
            if osp.isdir(spyproject_path):
                self._location.status_action.setVisible(True)
                self._location.status_action.setToolTip(
                    _("You selected a Spyder project")
                )
                reasons["spyder_project_exists"] = True

        return reasons

    def _compose_failed_validation_text(self, reasons: ValidationReasons):
        n_reasons = list(reasons.values()).count(True)
        prefix = "- " if n_reasons > 1 else ""
        suffix = "<br>" if n_reasons > 1 else ""

        text = ""
        if reasons.get("location_exists"):
            text += (
                prefix
                + _(
                    "The directory you selected for this project already "
                    "exists."
                )
                + suffix
            )
        elif reasons.get("spyder_project_exists"):
            text += (
                prefix
                + _("This directory is already a Spyder project.")
                + suffix
            )
        elif reasons.get("location_not_writable"):
            text += (
                prefix
                + _(
                    "You don't have write permissions in the location you "
                    "selected."
                )
                + suffix
            )
        elif reasons.get("no_location"):
            text += (
                prefix
                + _("The location you selected doesn't exist.")
                + suffix
            )

        if reasons.get("wrong_name"):
            text += (
                prefix
                + _("The directory name you selected is not valid.")
            )

        if reasons.get("missing_info"):
            text += (
                prefix
                + _("There are missing fields on this page.")
            )

        return text


class NewDirectoryPage(BaseProjectPage):
    """New directory project page."""

    LOCATION_TIP = _(
        "Select the location where the project directory will be created"
    )
    PROJECTS_DOCS_URL = (
        "https://docs.spyder-ide.org/current/panes/projects.html"
    )

    def get_name(self):
        return _("New directory")

    def get_icon(self):
        return self.create_icon("folder_new")

    def setup_page(self):
        description = QLabel(_("Start a project in a new directory"))
        description.setWordWrap(True)
        description.setFont(self._description_font)

        docs_reference = QLabel(
            _(
                "To learn more about projects, see our "
                '<a href="{0}">documentation</a>.'
            ).format(self.PROJECTS_DOCS_URL)
        )
        docs_reference.setOpenExternalLinks(True)

        self._name = self.create_lineedit(
            text=_("Project directory"),
            option=None,
            tip=_(
                "A directory with this name will be created in the location "
                "below"
            ),
            status_icon=ima.icon("error"),
        )

        layout = QVBoxLayout()
        layout.addWidget(description)
        layout.addWidget(docs_reference)
        layout.addSpacing(5 * AppStyle.MarginSize)
        layout.addWidget(self._name)
        layout.addSpacing(5 * AppStyle.MarginSize)
        layout.addWidget(self._location)
        layout.addSpacing(7 * AppStyle.MarginSize)
        layout.addWidget(self._validation_label)
        layout.addStretch()
        self.setLayout(layout)

    @property
    def project_location(self):
        return osp.normpath(
            osp.join(self._location.textbox.text(), self._name.textbox.text())
        )

    def validate_page(self):
        name = self._name.textbox.text()

        # Avoid using "." as location, which is the result of os.normpath("")
        location_text = self._location.textbox.text()
        location = osp.normpath(location_text) if location_text else ""

        # Clear validation state
        self._validation_label.setVisible(False)
        for widget in [self._name, self._location]:
            widget.status_action.setVisible(False)

        # Perform validation
        reasons: ValidationReasons = {}
        if not name:
            self._name.status_action.setVisible(True)
            self._name.status_action.setToolTip(_("This is empty"))
            reasons["missing_info"] = True

        reasons = self._validate_location(location, reasons, name)
        if reasons:
            if reasons.get("location_exists"):
                self._name.status_action.setVisible(True)
                self._name.status_action.setToolTip(
                    _("A directory with this name already exists")
                )
            if reasons.get("wrong_name"):
                self._name.status_action.setVisible(True)
                self._name.status_action.setToolTip(
                    _("The project directory can't contain ':'")
                )
            self._validation_label.set_text(
                self._compose_failed_validation_text(reasons)
            )
            self._validation_label.setVisible(True)

        return False if reasons else True


class ExistingDirectoryPage(BaseProjectPage):
    """Existing directory project page."""

    LOCATION_TEXT = _("Project path")
    LOCATION_TIP = _("Select the directory to use for the project")

    def get_name(self):
        return _("Existing directory")

    def get_icon(self):
        return self.create_icon("DirClosedIcon")

    def setup_page(self):
        description = QLabel(
            _("Create a Spyder project in an existing directory")
        )
        description.setWordWrap(True)
        description.setFont(self._description_font)

        layout = QVBoxLayout()
        layout.addWidget(description)
        layout.addSpacing(5 * AppStyle.MarginSize)
        layout.addWidget(self._location)
        layout.addSpacing(7 * AppStyle.MarginSize)
        layout.addWidget(self._validation_label)
        layout.addStretch()
        self.setLayout(layout)

    @property
    def project_location(self):
        return osp.normpath(self._location.textbox.text())

    def validate_page(self):
        # Clear validation state
        self._validation_label.setVisible(False)
        self._location.status_action.setVisible(False)

        # Avoid using "." as location, which is the result of os.normpath("")
        location_text = self._location.textbox.text()
        location = osp.normpath(location_text) if location_text else ""

        # Perform validation
        reasons = self._validate_location(location)
        if reasons:
            self._validation_label.set_text(
                self._compose_failed_validation_text(reasons)
            )
            self._validation_label.setVisible(True)

        return False if reasons else True


# =============================================================================
# ---- Dialog
# =============================================================================
class ProjectDialog(SidebarDialog):
    """Project creation dialog."""

    FIXED_SIZE = True
    MIN_WIDTH = 740 if MAC else (670 if WIN else 730)
    MIN_HEIGHT = 470 if MAC else (420 if WIN else 450)
    PAGES_MINIMUM_WIDTH = 450
    PAGE_CLASSES = [NewDirectoryPage, ExistingDirectoryPage]

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

    def __init__(self, parent):
        """Project creation dialog."""
        super().__init__(parent=parent)
        self.project_data = {}

        self.setWindowFlags(
            self.windowFlags() & ~Qt.WindowContextHelpButtonHint
        )
        self.setWindowTitle(_('Create new project'))
        self.setWindowIcon(ima.icon("project_new"))

    def create_buttons(self):
        bbox = SpyderDialogButtonBox(
            QDialogButtonBox.Cancel, orientation=Qt.Horizontal
        )

        self.button_create = QPushButton(_('Create'))
        self.button_create.clicked.connect(self.create_project)
        bbox.addButton(self.button_create, QDialogButtonBox.ActionRole)

        layout = QHBoxLayout()
        layout.addWidget(bbox)
        return bbox, layout

    def create_project(self):
        """Create project."""
        page = self.get_page()

        # Validate info
        if not page.validate_page():
            return

        self.project_data = {
            "root_path": osp.normpath(page.project_location),
            "project_type": page.project_type.ID,
        }
        self.sig_project_creation_requested.emit(
            page.project_location,
            page.project_type.ID,
            [],
        )
        self.accept()


def test():
    """Local test."""
    from spyder.utils.qthelpers import qapplication
    from spyder.config.base import running_in_ci

    app = qapplication()

    dlg = ProjectDialog(None)

    if not running_in_ci():
        from spyder.utils.stylesheet import APP_STYLESHEET
        app.setStyleSheet(str(APP_STYLESHEET))

    dlg.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    test()
