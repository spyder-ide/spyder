# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright © Spyder Project Contributors
#
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)
# -----------------------------------------------------------------------------
"""Project settings dialog."""

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
from spyder.widgets.helperwidgets import MessageLabel

# For logging
logger = logging.getLogger(__name__)


class ValidationReasons(TypedDict):
    no_location: bool | None


# =============================================================================
# ---- Pages
# =============================================================================
class SettingsPage(SpyderConfigPage, SpyderFontsMixin):
    """Settings page for projects."""

    # SidebarPage API
    MAX_WIDTH = 99999

    # SpyderConfigPage API
    LOAD_FROM_CONFIG = False

    def __init__(self, parent):
        super().__init__(parent)

        self._location = self.create_browsefile(
            text=_("Interpreter location"),
            option=None,
            alignment=Qt.Vertical,
            tip=_("Select the python executable to use for the project. Leave empty to use the default interpreter"),
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
    def interpreter(self):
        return osp.normpath(self._location.textbox.text())

    def load_configuration(self, config):
        """Load configuration inot the dialog"""
        self._location.textbox.setText(
            config.get('workspace', 'interpreter'))

    def save_configuration(self, config):
        config.set('workspace', 'interpreter', self.interpreter)

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

        if not osp.isfile(location):
            self._location.status_action.setVisible(True)
            self._location.status_action.setToolTip(
                _("This directory doesn't exist")
            )
            reasons["no_location"] = True

        return reasons

    def _compose_failed_validation_text(self, reasons: ValidationReasons):
        n_reasons = list(reasons.values()).count(True)
        prefix = "- " if n_reasons > 1 else ""
        suffix = "<br>" if n_reasons > 1 else ""

        text = ""
        if reasons.get("no_location"):
            text += (
                prefix
                + _("The location you selected doesn't exist.")
                + suffix
            )

        return text

    def get_name(self):
        return _("Existing directory")

    def get_icon(self):
        return self.create_icon("project_preferences")

    def setup_page(self):
        layout = QVBoxLayout()
        layout.addWidget(self._location)
        layout.addSpacing(7 * AppStyle.MarginSize)
        layout.addWidget(self._validation_label)
        layout.addStretch()
        self.setLayout(layout)

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
        self.setWindowTitle(_('Project settings')+f"[{self._project.get_name()}]")
        self.setWindowIcon(ima.icon("project_preferences"))

        self._page = SettingsPage(self)
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

    with tempfile.TemporaryDirectory() as project_path:
        dlg = ConfigDialog(None, EmptyProject(project_path))

        if not running_in_ci():
            from spyder.utils.stylesheet import APP_STYLESHEET
            app.setStyleSheet(str(APP_STYLESHEET))

        dlg.show()
        sys.exit(app.exec_())


if __name__ == "__main__":
    test()
