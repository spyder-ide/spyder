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
import sys
import logging
from typing import TypedDict

# Third party imports
from qtpy.QtCore import Qt, Signal, QSize
from qtpy.QtWidgets import (
    QDialog,
    QGridLayout,
    QWidget,
    QDialogButtonBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QSizePolicy,
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
from spyder.utils.conda import find_local_venv_interpreter


# For logging
logger = logging.getLogger(__name__)

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


# =============================================================================
# ---- Pages
# =============================================================================
class SettingsPage(SpyderConfigPage, SpyderFontsMixin):
    """Settings page for projects."""

    # SidebarPage API
    MAX_WIDTH = 99999

    # SpyderConfigPage API
    LOAD_FROM_CONFIG = False

    def __init__(self, parent, project_root=None):
        super().__init__(parent)
        self.project_root = project_root

        self._location = self.create_browsefile(
            text=_("Interpreter location"),
            option=None,
            alignment=Qt.Vertical,
            tip=_(
                "Select the Python executable to use for this project. "
                "Leave empty to use the global interpreter."
            ),
            status_icon=ima.icon("error"),
        )

        self._detect_button = QPushButton(_("Detect"))
        self._detect_button.setToolTip(
            _("Look for an environment in the project folder")
        )
        self._detect_button.clicked.connect(self._detect)

    # ---- Public API
    # -------------------------------------------------------------------------
    @property
    def interpreter(self):
        text = self._location.textbox.text().strip()
        return osp.normpath(text) if text else ""

    def load_configuration(self, config):
        """Load configuration into the dialog."""
        self._location.textbox.setText(config.get('workspace', 'interpreter'))

    def save_configuration(self, config):
        config.set('workspace', 'interpreter', self.interpreter)

    def get_name(self):
        return _("Interpreter")

    def get_icon(self):
        return self.create_icon("project_preferences")

    def setup_page(self):
        layout = QVBoxLayout()
        layout.addWidget(self._location)
        layout.addWidget(self._detect_button, alignment=Qt.AlignLeft)
        layout.addStretch()
        self.setLayout(layout)

    def validate_page(self):
        self._location.status_action.setVisible(False)

        text = self._location.textbox.text().strip()
        if text and not osp.isfile(text):
            self._location.status_action.setVisible(True)
            self._location.status_action.setToolTip(
                _("This file doesn't exist")
            )
        return True

    # ---- Private API
    # -------------------------------------------------------------------------
    def _detect(self):
        """Look for an environment in the project folder."""
        if not self.project_root:
            return

        found = find_local_venv_interpreter(self.project_root)
        if found:
            self._location.textbox.setText(found)


# =============================================================================
# ---- Dialog
# =============================================================================
class ConfigDialog(QDialog, SpyderFontsMixin):
    """Project settings dialog."""

    def __init__(self, parent, project):
        """Project settings dialog."""
        QDialog.__init__(self, parent=parent)

        assert project is not None

        self._project = project

        buttons = SpyderDialogButtonBox(
            QDialogButtonBox.Save|QDialogButtonBox.Cancel,
            parent=self)

        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        self.setWindowFlags(
            self.windowFlags() & ~Qt.WindowContextHelpButtonHint
        )
        self.setWindowTitle(
            _('Project settings') + f" [{self._project.get_name()}]"
        )
        self.setWindowIcon(ima.icon("project_preferences"))

        self._page = SettingsPage(self, project_root=project.root_path)
        self._page.initialize()
        self._page.load_configuration(self._project.config)

        layout = QVBoxLayout()
        layout.addWidget(self._page)
        layout.addWidget(buttons)
        self.setLayout(layout)

    @property
    def project(self):
        return self._project

    def load_configuration(self, config):
        self._page.load_configuration(config)

    def save_configuration(self):
        self._page.save_configuration(self._project.config)

def test():
    """Local test."""
    from spyder.utils.qthelpers import qapplication
    from spyder.config.base import running_in_ci
    from spyder.plugins.projects.api import EmptyProject
    import tempfile

    app = qapplication()

    project_dir = tempfile.mkdtemp() + osp.sep + '.spyproject'
    project = EmptyProject(project_dir, None)

    dlg = ConfigDialog(None, project)

    if not running_in_ci():
        from spyder.utils.stylesheet import APP_STYLESHEET
        app.setStyleSheet(str(APP_STYLESHEET))

    dlg.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    test()
