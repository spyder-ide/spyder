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
import os

# Third party imports
from qtpy.QtCore import QPoint, Signal, Slot
from qtpy.QtWidgets import QMenu

# Local imports
from spyder.api.widgets.status import StatusBarWidget
from spyder.config.base import _, is_pynsist, running_in_mac_app
from spyder.plugins.application.widgets.install import (
    UpdateInstallerDialog, NO_STATUS, DOWNLOADING_INSTALLER, INSTALLING,
    FINISHED, PENDING, CHECKING, CANCELLED)
from spyder.utils.icon_manager import ima
from spyder.utils.qthelpers import add_actions, create_action

logger = logging.getLogger(__name__)


class ApplicationUpdateStatus(StatusBarWidget):
    """Status bar widget for Application update status."""
    BASE_TOOLTIP = _("Application update status")
    ID = 'application_update_status'

    sig_check_for_updates_requested = Signal()

    def __init__(self, parent):

        self.tooltip = self.BASE_TOOLTIP
        super().__init__(parent, show_spinner=True)

        # Installation dialog
        self.installer = UpdateInstallerDialog(self)
        # Check for updates action menu
        self.menu = QMenu(self)

        self.sig_clicked.connect(self.show_installation_dialog_or_menu)

        self.installer.sig_installation_status.connect(
            self.set_value)

    def set_value(self, value):
        """Return update installation state."""
        if value == DOWNLOADING_INSTALLER or value == INSTALLING:
            self.tooltip = _("Update installation will continue in the "
                             "background.\n"
                             "Click here to show the installation "
                             "dialog again")
            self.spinner.show()
            self.spinner.start()
            self.installer.show()

        elif value == PENDING:
            self.tooltip = value
            self.spinner.hide()
            self.spinner.stop()
        else:
            self.tooltip = self.BASE_TOOLTIP
        self.setVisible(True)
        self.update_tooltip()
        value = f"Spyder: {value}"
        logger.debug(f"Application Update Status: {value}")
        super().set_value(value)

    def get_tooltip(self):
        """Reimplementation to get a dynamic tooltip."""
        return self.tooltip

    def get_icon(self):
        return ima.icon('spyder_about')

    def start_installation(self, latest_release):
        self.installer.start_installation_update(latest_release)

    def set_status_pending(self):
        self.set_value(PENDING)
        self.spinner.hide()
        self.spinner.stop()

    def set_status_checking(self):
        self.set_value(CHECKING)
        self.spinner.show()
        self.spinner.start()

    def set_no_status(self):
        self.set_value(NO_STATUS)
        self.spinner.hide()
        self.spinner.stop()

    @Slot()
    def show_installation_dialog_or_menu(self):
        """Show installation dialog or menu."""
        value = self.value.split(":")[-1].strip()
        if ((not self.tooltip == self.BASE_TOOLTIP
            and not value == PENDING)
                and (is_pynsist() or running_in_mac_app())):
            self.installer.show()
        elif (value == PENDING and
              (is_pynsist() or running_in_mac_app())):
            self.installer.continue_install()
        elif value == NO_STATUS:
            self.menu.clear()
            check_for_updates_action = create_action(
                self,
                text=_("Check for updates..."),
                triggered=self.sig_check_for_updates_requested.emit
            )
            add_actions(self.menu, [check_for_updates_action])
            rect = self.contentsRect()
            os_height = 7 if os.name == 'nt' else 12
            pos = self.mapToGlobal(
                rect.topLeft() + QPoint(-10, -rect.height() - os_height))
            self.menu.popup(pos)
