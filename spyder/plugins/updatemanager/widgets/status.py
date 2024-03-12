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
from qtpy.QtWidgets import QLabel

# Local imports
from spyder.api.translations import _
from spyder.api.widgets.menus import SpyderMenu
from spyder.api.widgets.status import StatusBarWidget
from spyder.plugins.updatemanager.widgets.update import (
    CHECKING,
    DOWNLOAD_FINISHED,
    DOWNLOADING_INSTALLER,
    INSTALL_ON_CLOSE,
    NO_STATUS,
    PENDING
)
from spyder.utils.icon_manager import ima
from spyder.utils.qthelpers import add_actions, create_action


# Setup logger
logger = logging.getLogger(__name__)


class UpdateManagerStatus(StatusBarWidget):
    """Status bar widget for update manager."""
    BASE_TOOLTIP = _("Application update status")
    ID = 'update_manager_status'

    sig_check_update = Signal()
    """Signal to request checking for updates."""

    sig_start_update = Signal()
    """Signal to start the update process"""

    sig_show_progress_dialog = Signal(bool)
    """
    Signal to show the progress dialog.

    Parameters
    ----------
    show: bool
        True to show, False to hide.
    """

    CUSTOM_WIDGET_CLASS = QLabel

    def __init__(self, parent):

        self.tooltip = self.BASE_TOOLTIP
        super().__init__(parent, show_spinner=True)

        # Check for updates action menu
        self.menu = SpyderMenu(self)

        # Set aligment attributes for custom widget to match default label
        # values
        self.custom_widget.setAlignment(Qt.AlignRight | Qt.AlignVCenter)

        # Signals
        self.sig_clicked.connect(self.show_dialog_or_menu)

    def set_value(self, value):
        """Set update manager status."""
        if value == DOWNLOADING_INSTALLER:
            self.tooltip = _(
                "Downloading the update will continue in the background.\n"
                "Click here to show the download dialog again."
            )
            self.spinner.hide()
            self.spinner.stop()
            self.custom_widget.show()
        elif value == CHECKING:
            self.tooltip = self.BASE_TOOLTIP
            self.custom_widget.hide()
            self.spinner.show()
            self.spinner.start()
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
        logger.debug(f"Update manager status: {value}")
        super().set_value(value)

    def set_no_status(self):
        """Convenience method to set status to NO_STATUS"""
        self.set_value(NO_STATUS)

    def get_tooltip(self):
        """Reimplementation to get a dynamic tooltip."""
        return self.tooltip

    def get_icon(self):
        return ima.icon('spyder_about')

    def set_download_progress(self, percent_progress):
        """Set download progress in status bar"""
        self.custom_widget.setText(f"{percent_progress}%")

    @Slot()
    def show_dialog_or_menu(self):
        """Show download dialog or status bar menu."""
        value = self.value.split(":")[-1].strip()
        if value == DOWNLOADING_INSTALLER:
            self.sig_show_progress_dialog.emit(True)
        elif value in (PENDING, DOWNLOAD_FINISHED, INSTALL_ON_CLOSE):
            self.sig_start_update.emit()
        elif value == NO_STATUS:
            self.menu.clear()
            check_for_updates_action = create_action(
                self,
                text=_("Check for updates..."),
                triggered=self.sig_check_update.emit
            )

            add_actions(self.menu, [check_for_updates_action])
            rect = self.contentsRect()
            os_height = 7 if os.name == 'nt' else 12
            pos = self.mapToGlobal(
                rect.topLeft() + QPoint(-10, -rect.height() - os_height)
            )
            self.menu.popup(pos)
