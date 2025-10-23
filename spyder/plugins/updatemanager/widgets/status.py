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
from qtpy.QtCore import Qt, Signal, Slot
from qtpy.QtWidgets import QLabel

# Local imports
from spyder.api.translations import _
from spyder.api.widgets.menus import SpyderMenu
from spyder.api.widgets.status import StatusBarWidget
from spyder.plugins.updatemanager.widgets.update import (
    CHECKING,
    DOWNLOAD_FINISHED,
    DOWNLOADING_INSTALLER,
    UPDATING_UPDATER,
    INSTALL_ON_CLOSE,
    NO_STATUS,
    PENDING
)
from spyder.utils.icon_manager import ima


# Setup logger
logger = logging.getLogger(__name__)


class UpdateManagerStatus(StatusBarWidget):
    """Status bar widget for update manager."""
    ID = 'update_manager_status'
    INTERACT_ON_CLICK = True

    sig_check_update = Signal()
    """Signal to request checking for updates."""

    sig_start_update = Signal()
    """Signal to start the update process."""

    sig_show_progress_dialog = Signal()
    """Signal to show the progress dialog."""

    CUSTOM_WIDGET_CLASS = QLabel

    def __init__(self, parent):

        self.tooltip = ""
        super().__init__(parent)

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
            self.custom_widget.show()
            self.show()
        elif value == CHECKING:
            self.tooltip = value
            self.custom_widget.hide()
            self.hide()
        elif value == PENDING:
            self.tooltip = value
            self.custom_widget.hide()
            self.show()
        elif value == UPDATING_UPDATER:
            self.tooltip = value
            self.custom_widget.hide()
            self.show()
        else:
            self.tooltip = ""
            if self.custom_widget:
                self.custom_widget.hide()
            self.hide()

        self.update_tooltip()
        logger.debug(f"Update manager status: {value}")
        super().set_value(value)

    def set_no_status(self):
        """Convenience method to set status to NO_STATUS"""
        self.set_value(NO_STATUS)

    def get_tooltip(self):
        """Reimplementation to get a dynamic tooltip."""
        return self.tooltip

    def get_icon(self):
        return ima.icon('update')

    def set_download_progress(self, percent_progress):
        """Set download progress in status bar"""
        self.custom_widget.setText(f"{percent_progress}%")

    @Slot()
    def show_dialog_or_menu(self):
        """Show download dialog or status bar menu."""
        if self.value in (DOWNLOADING_INSTALLER, UPDATING_UPDATER):
            self.sig_show_progress_dialog.emit()
        elif self.value in (PENDING, DOWNLOAD_FINISHED, INSTALL_ON_CLOSE):
            self.sig_start_update.emit()
