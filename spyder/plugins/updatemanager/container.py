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
import logging

# Third party imports
from qtpy.QtCore import Slot

# Local imports
from spyder.api.translations import _
from spyder.api.widgets.main_container import PluginMainContainer
from spyder.plugins.updatemanager.widgets.status import UpdateManagerStatus
from spyder.plugins.updatemanager.widgets.update import UpdateManagerWidget
from spyder.utils.qthelpers import DialogManager

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
        self.dialog_manager = DialogManager()
        self.update_manager = UpdateManagerWidget(parent=self)
        self.update_manager_status = UpdateManagerStatus(parent=self)

        # Actions
        self.check_update_action = self.create_action(
            UpdateManagerActions.SpyderCheckUpdateAction,
            _("Check for updates..."),
            triggered=self.start_check_update
        )

        # Signals
        self.update_manager.sig_set_status.connect(self.set_status)
        self.update_manager.sig_disable_actions.connect(
            self._set_actions_state
        )
        self.update_manager.sig_block_status_signals.connect(
            self.update_manager_status.blockSignals)
        self.update_manager.sig_download_progress.connect(
            self.update_manager_status.set_download_progress)
        self.update_manager.sig_exception_occurred.connect(
            self.sig_exception_occurred
        )
        self.update_manager.sig_install_on_close.connect(
            self.set_install_on_close)
        self.update_manager.sig_quit_requested.connect(self.sig_quit_requested)

        self.update_manager_status.sig_check_update.connect(
            self.start_check_update)
        self.update_manager_status.sig_start_update.connect(self.start_update)
        self.update_manager_status.sig_show_progress_dialog.connect(
            self.update_manager.show_progress_dialog)

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
    def set_status(self, status, latest_version=None):
        """Set Update Manager status"""
        self.update_manager_status.set_value(status)

    @Slot()
    def start_check_update(self, startup=False):
        """Check for spyder updates."""
        self.update_manager.start_check_update(startup=startup)

    @Slot()
    def start_update(self):
        """Start the update process"""
        self.update_manager.start_update()

    def set_install_on_close(self, install_on_close):
        """Set whether start install on close."""
        self.install_on_close = install_on_close

    # ---- Private API
    # -------------------------------------------------------------------------
    @Slot(bool)
    def _set_actions_state(self, is_disabled):
        self.check_update_action.setDisabled(is_disabled)

        # Change text to give better feedback to users about why the action is
        # disabled.
        if is_disabled:
            self.check_update_action.setText(_("Checking for updates..."))
        else:
            self.check_update_action.setText(_("Check for updates..."))
