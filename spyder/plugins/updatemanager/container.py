# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""
Container Widget.

Holds references for base actions in the Application of Spyder.
"""

# Standard library imports
from __future__ import annotations
import logging
from typing import TYPE_CHECKING

# Third party imports
from qtpy.QtCore import Slot

# Local imports
from spyder.api.translations import _
from spyder.api.widgets.main_container import PluginMainContainer
from spyder.plugins.updatemanager.widgets.update import (
    UpdateManagerWidget,
    UpdateStatus,
)
from spyder.utils.qthelpers import DialogManager


if TYPE_CHECKING:
    from spyder.plugins.updatemanager.widgets.status import UpdateManagerStatus


# Logger setup
logger = logging.getLogger(__name__)


# Actions
class UpdateManagerActions:
    SpyderCheckUpdateAction = "spyder_check_update_action"


class UpdateManagerContainer(PluginMainContainer):

    def __init__(self, name, plugin, parent=None):
        super().__init__(name, plugin, parent)

        self.install_on_close = False

    # ---- PluginMainContainer API
    # -------------------------------------------------------------------------
    def setup(self):
        self.update_status: UpdateStatus = UpdateStatus.NoStatus
        self.dialog_manager = DialogManager()
        self.update_manager = UpdateManagerWidget(parent=self)

        # This is set by the plugin
        self.update_manager_status: UpdateManagerStatus | None = None

        # Actions
        self.check_update_action = self.create_action(
            UpdateManagerActions.SpyderCheckUpdateAction,
            _("Check for updates"),
            triggered=self.start_check_update
        )

        # Signals
        self.update_manager.sig_set_status.connect(self._set_status)
        self.update_manager.sig_disable_actions.connect(
            self._set_actions_state
        )
        self.update_manager.sig_exception_occurred.connect(
            self.sig_exception_occurred
        )
        self.update_manager.sig_install_on_close.connect(
            self._set_install_on_close
        )
        self.update_manager.sig_quit_requested.connect(self.sig_quit_requested)

    def update_actions(self):
        pass

    def on_close(self):
        """To call from Spyder when the plugin is closed."""
        self.update_manager.cleanup_threads()

        # Run installer after Spyder is closed
        if self.install_on_close:
            self.update_manager.start_install()

        self.dialog_manager.close_all()

    # ---- Public API
    # -------------------------------------------------------------------------
    @Slot()
    def start_check_update(self, startup=False):
        """Check for spyder updates."""
        self.update_manager.start_check_update(startup=startup)

    def connect_status_signals(self):
        self.update_manager.sig_block_status_signals.connect(
            self.update_manager_status.blockSignals
        )
        self.update_manager.sig_download_progress.connect(
            self.update_manager_status.set_download_progress
        )
        self.update_manager_status.sig_check_update.connect(
            self.start_check_update
        )
        self.update_manager_status.sig_start_update.connect(
            self._start_update
        )
        self.update_manager_status.sig_show_progress_dialog.connect(
            self.update_manager.show_progress_dialog
        )

    def disconnect_status_signals(self):
        self.update_manager.sig_block_status_signals.disconnect(
            self.update_manager_status.blockSignals
        )
        self.update_manager.sig_download_progress.disconnect(
            self.update_manager_status.set_download_progress
        )
        self.update_manager_status.sig_check_update.disconnect(
            self.start_check_update
        )
        self.update_manager_status.sig_start_update.disconnect(
            self._start_update
        )
        self.update_manager_status.sig_show_progress_dialog.disconnect(
            self.update_manager.show_progress_dialog
        )

    # ---- Private API
    # -------------------------------------------------------------------------
    def _set_status(self, status: UpdateStatus, latest_version=None):
        """Set Update Manager status"""
        self.update_status = status

        if self.update_manager_status is not None:
            self.update_manager_status.set_status(status)

    @Slot()
    def _start_update(self):
        """Start the update process"""
        self.update_manager.start_update()

    def _set_install_on_close(self, install_on_close):
        """Set whether start install on close."""
        self.install_on_close = install_on_close

    @Slot(bool)
    def _set_actions_state(self, is_disabled):
        self.check_update_action.setDisabled(is_disabled)

        # Change text to give better feedback to users about why the action is
        # disabled.
        if is_disabled:
            self.check_update_action.setText(_("Checking for updates..."))
        else:
            self.check_update_action.setText(_("Check for updates"))
