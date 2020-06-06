# -*- coding: utf-8 -*-

# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""Kite completion container."""

# Standard library imports
import logging
import os

# Third party imports imports
from qtpy.QtCore import Slot
from qtpy.QtWidgets import QMessageBox

# Local imports
from spyder.api.translations import get_translation
from spyder.api.widgets import PluginMainContainer
from spyder.config.base import running_under_pytest
from spyder.plugins.kite.provider import KiteCompletionProvider
from spyder.plugins.kite.utils.install import KiteInstallationThread
from spyder.plugins.kite.utils.status import check_if_kite_installed
from spyder.plugins.kite.widgets.install import KiteInstallerDialog
from spyder.plugins.kite.widgets.status import KiteStatusWidget
from spyder.widgets.helperwidgets import MessageCheckBox

# Logging
logger = logging.getLogger(__name__)

# Localization
_ = get_translation('spyder')


class KiteCompletionContainer(PluginMainContainer):

    DEFAULT_OPTIONS = {
        'code_snippets': True,
        'enable': True,
        'show_onboarding': True,
        'show_installation_error_message': True,
    }

    def __init__(self, name, plugin, parent=None, options=DEFAULT_OPTIONS):
        super().__init__(name, plugin, parent=parent, options=options)

        # Attributes
        self.open_file_updated = False  # Is this used?

        # Widgets/objects
        self.provider = KiteCompletionProvider(self)
        self.installation_thread = KiteInstallationThread(self)
        self.installer = KiteInstallerDialog(parent, self.installation_thread)
        self.status_widget = KiteStatusWidget(None, None, self)
        client = self.provider.client

        # Signals
        self.installation_thread.sig_installation_status.connect(
            self.set_status)
        self.provider.sig_provider_ready.connect(
            lambda x: self._request_onboarding)
        self.provider.sig_errored.connect(self._show_error_box)
        client.sig_onboarding_response_ready.connect(
            self._show_onboarding_file)
        client.sig_status_response_ready[str].connect(self.set_status)
        client.sig_status_response_ready[dict].connect(self.set_status)
        client.sig_status_response_ready.connect(self._request_onboarding)
        self.status_widget.sig_clicked.connect(self.show_installation_dialog)

    # --- Private API
    # ------------------------------------------------------------------------
    def _show_error_box(self):
        __, path = check_if_kite_installed()
        logger.debug(
            'Error starting Kite service at {path}...'.format(path=path))

        if self.get_option('show_installation_error_message'):
            box = MessageCheckBox(icon=QMessageBox.Critical, parent=self.main)
            box.setWindowTitle(_("Kite installation error"))
            box.set_checkbox_text(_("Don't show again."))
            box.setStandardButtons(QMessageBox.Ok)
            box.setDefaultButton(QMessageBox.Ok)
            box.set_checked(False)
            box.set_check_visible(True)
            box.setText(
                _("It seems that your Kite installation is faulty. "
                  "If you want to use Kite, please remove the "
                  "directory that appears bellow, "
                  "and try a reinstallation:<br><br>"
                  "<code>{kite_dir}</code>".format(
                      kite_dir=os.path.dirname(path))))
            box.exec_()

            # Update checkbox based on user interaction
            self.set_option(
                'show_installation_error_message', not box.is_checked())

    def _request_onboarding(self):
        """Request the onboarding file."""
        # No need to check installed status, since the get_onboarding_file
        # call fails fast.
        if not self.get_option('enabled'):
            return

        if not self.get_option('show_onboarding'):
            return

        # FIXME: Add some communication mechanism so the container know if the
        # plugin is on_Visible or on what state.
        if self.main.is_setting_up:
            return

        if not self.provider.available_languages:
            return

        # Don't send another request until this request fails.
        self.set_option('show_onboarding', False)
        self.client.sig_perform_onboarding_request.emit()

    @Slot(str)
    def _show_onboarding_file(self, onboarding_file):
        """
        Opens the onboarding file, which is retrieved from the Kite HTTP
        endpoint.

        This skips onboarding if onboarding is not possible yet or has
        already been displayed before.

        Parameters
        ----------
        onboarding_file: str
            Path to onboarding file.
        """
        if not onboarding_file:
            # Retry
            self.set_option('show_onboarding', True)
            return

        self.set_option('show_onboarding', False)

        # FIXME:
        self.main.open_file(onboarding_file)

    # --- PluginMainContainer API
    # ------------------------------------------------------------------------
    def setup(self, options=DEFAULT_OPTIONS):
        pass

    def on_option_update(self, option, value):
        if option in ['enable', 'code_snippets']:
            self.provider.update_configuration({option: value})

    def update_actions(self):
        pass

    # --- Public API
    # ------------------------------------------------------------------------
    @Slot(str)
    @Slot(dict)
    def set_status(self, status):
        """
        Show Kite status for the current file.

        Parameters
        ----------
        status: str
            Localized status text.
        """
        self.status_widget.set_value(status)

    @Slot()
    def show_installation_dialog(self):
        """Show installation dialog."""
        installed, __ = check_if_kite_installed()
        if not installed and not running_under_pytest():
            self.installer.show()

    def is_installing(self):
        """Check if an installation is taking place."""
        return (self.installation_thread.isRunning()
                and not self.installation_thread.cancelled)

    def installation_cancelled_or_errored(self):
        """Check if an installation was cancelled or failed."""
        return self.installation_thread.cancelled_or_errored()

    def send_status_request(self, *args, **kwargs):
        """Send status request on file open."""
        if not self.is_installing():
            self.provider.send_status_request(*args, **kwargs)
