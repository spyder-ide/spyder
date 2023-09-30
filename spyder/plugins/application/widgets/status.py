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
from qtpy.QtCore import QPoint, Qt, Signal, Slot
from qtpy.QtWidgets import QMenu, QLabel

# Local imports
from spyder.api.translations import _
from spyder.api.widgets.status import StatusBarWidget
from spyder.plugins.application.widgets.install import (
    UpdateInstallerDialog, NO_STATUS, DOWNLOADING_INSTALLER, INSTALLING,
    PENDING, CHECKING, DOWNLOAD_FINISHED, INSTALL_ON_CLOSE)
from spyder.utils.icon_manager import ima
from spyder.utils.qthelpers import add_actions, create_action


# Setup logger
logger = logging.getLogger(__name__)


class ApplicationUpdateStatus(StatusBarWidget):
    """Status bar widget for application update status."""
    BASE_TOOLTIP = _("Application update status")
    ID = 'application_update_status'

    sig_check_for_updates_requested = Signal()
    """
    Signal to request checking for updates.
    """

    sig_install_on_close_requested = Signal(bool)
    """
    Signal to request running the downloaded installer on close.

    Parameters
    ----------
    install_on_close: bool
        Whether to install on close.
    """

    sig_quit_requested = Signal()
    """
    This signal can be emitted to request the main application to quit.
    """

    CUSTOM_WIDGET_CLASS = QLabel

    def __init__(self, parent):

        self.tooltip = self.BASE_TOOLTIP
        super().__init__(parent, show_spinner=True)

        # Installation dialog
        self.installer = UpdateInstallerDialog(self)

        # Check for updates action menu
        self.menu = QMenu(self)

        # Set aligment attributes for custom widget to match default label
        # values
        self.custom_widget.setAlignment(Qt.AlignRight | Qt.AlignVCenter)

        # Signals
        self.sig_clicked.connect(self.show_installation_dialog_or_menu)

        # Installer widget signals
        self.installer.sig_download_progress.connect(
            self.set_download_progress)
        self.installer.sig_installation_status.connect(
            self.set_value)
        self.installer.sig_install_on_close_requested.connect(
            self.sig_install_on_close_requested)
        self.installer.sig_quit_requested.connect(self.sig_quit_requested)

    def set_value(self, value):
        """Return update installation state."""
        if value == DOWNLOADING_INSTALLER or value == INSTALLING:
            self.tooltip = _("Update installation will continue in the "
                             "background.\n"
                             "Click here to show the installation "
                             "dialog again.")
            if value == DOWNLOADING_INSTALLER:
                self.spinner.hide()
                self.spinner.stop()
                self.custom_widget.show()
            else:
                self.custom_widget.hide()
                self.spinner.show()
                self.spinner.start()
            self.installer.show()
        elif value == PENDING:
            self.tooltip = value
            self.custom_widget.hide()
            self.spinner.hide()
            self.spinner.stop()
        else:
            self.tooltip = self.BASE_TOOLTIP
            if self.custom_widget:
                self.custom_widget.hide()
            if self.spinner:
                self.spinner.hide()
                self.spinner.stop()
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

    def start_update(self):
        self.installer.start_update()

    def start_download(self):
        self.installer.start_download()

    def confirm_installation(self):
        self.installer.confirm_installation()

    def start_installation(self):
        self.installer.start_installation()

    def set_download_progress(self, current_value, total):
        percentage_progress = 0
        if total > 0:
            percentage_progress = round((current_value / total) * 100)
        self.custom_widget.setText(f"{percentage_progress}%")

    def set_status_pending(self, latest_release):
        self.set_value(PENDING)
        self.installer.set_latest_release(latest_release)

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
        if self.tooltip != self.BASE_TOOLTIP and value != PENDING:
            self.installer.show()
        elif value == PENDING:
            self.installer.start_update()
        elif value in (DOWNLOAD_FINISHED, INSTALL_ON_CLOSE):
            self.installer.confirm_installation()
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
