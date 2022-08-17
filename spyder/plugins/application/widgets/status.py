# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""
Status widget for Spyder updates.
"""

# Standard library imports
import logging

# Third party imports
from qtpy.QtCore import Slot

# Local imports
from spyder.api.widgets.status import StatusBarWidget
from spyder.config.base import _, is_pynsist
from spyder.plugins.application.widgets.install import (
    UpdateInstallerDialog, NO_STATUS, DOWNLOADING_INSTALLER, INSTALLING,
    FINISHED, PENDING, CHECKING, CANCELLED)
from spyder.utils.icon_manager import ima
from spyder import get_versions

logger = logging.getLogger(__name__)


class ApplicationUpdateStatus(StatusBarWidget):
    """Status bar widget for Application update status."""
    BASE_TOOLTIP = _("Application update status")
    ID = 'application_update_status'

    def __init__(self, parent):

        self.cancelled = False
        self.status = NO_STATUS
        self.thread_install_update = None
        self.tooltip = self.BASE_TOOLTIP
        self._container = parent
        super().__init__(parent)

        # Installation dialog
        self.installer = UpdateInstallerDialog(
            self)

        self.sig_clicked.connect(self.show_installation_dialog)

        self.installer.sig_installation_status.connect(
            self.set_value)

    def set_value(self, value):
        """Return update installation state."""
        versions = get_versions()
        if value == DOWNLOADING_INSTALLER or value == INSTALLING:
            self.tooltip = _("Update installation will continue in the "
                             "background.\n"
                             "Click here to show the installation "
                             "dialog again")
        elif value == PENDING:
            self.tooltip = value
        else:
            self.tooltip = self.BASE_TOOLTIP
        self.setVisible(True)
        self.update_tooltip()
        value = "Spyder: {0}".format(value)
        super().set_value(value)

    def get_tooltip(self):
        """Reimplementation to get a dynamic tooltip."""
        return self.tooltip

    def get_icon(self):
        return ima.icon('spyder')

    def start_installation(self):
        self.installer.start_installation_update()

    def set_status_pending(self):
        self.set_value(PENDING)

    def set_status_checking(self):
        self.set_value(CHECKING)

    def set_no_status(self):
        self.set_value(NO_STATUS)

    @Slot()
    def show_installation_dialog(self):
        """Show installation dialog."""
        if ((not self.tooltip == self.BASE_TOOLTIP and not
                self.tooltip == PENDING) and is_pynsist):
            self.installer.show()
        elif ((self.tooltip == PENDING) and is_pynsist):
            self.installer.continue_install()
