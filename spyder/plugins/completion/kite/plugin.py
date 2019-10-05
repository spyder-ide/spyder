# -*- coding: utf-8 -*-

# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""Kite completion HTTP client."""

# Standard library imports
import logging
import functools

# Qt imports
from qtpy.QtCore import Slot

# Local imports
from spyder.config.base import _, running_under_pytest
from spyder.config.manager import CONF
from spyder.utils.programs import run_program
from spyder.api.completion import SpyderCompletionPlugin
from spyder.plugins.completion.kite.client import KiteClient
from spyder.plugins.completion.kite.utils.status import (
    check_if_kite_running, check_if_kite_installed)
from spyder.plugins.completion.kite.utils.install import (
    KiteInstallationThread, FINISHED)
from spyder.plugins.completion.kite.utils.status import (
    status, RUNNING)
from spyder.plugins.completion.kite.widgets.install import KiteInstallerDialog
from spyder.plugins.completion.kite.widgets.status import KiteStatus


logger = logging.getLogger(__name__)


class KiteCompletionPlugin(SpyderCompletionPlugin):
    CONF_SECTION = 'kite'
    CONF_FILE = False

    COMPLETION_CLIENT_NAME = 'kite'

    def __init__(self, parent):
        SpyderCompletionPlugin.__init__(self, parent)
        self.available_languages = []
        self.client = KiteClient(None)
        self.kite_process = None

        # Installation
        self.kite_installation_thread = KiteInstallationThread(self)
        self.kite_installer = KiteInstallerDialog(
            parent,
            self.kite_installation_thread)

        # Status
        statusbar = parent.statusBar()  # MainWindow status bar
        self.open_file_updated = False
        self.kite_status = KiteStatus(None, statusbar, self)

        # Signals
        self.client.sig_client_started.connect(self.http_client_ready)
        self.client.sig_response_ready.connect(
            functools.partial(self.sig_response_ready.emit,
                              self.COMPLETION_CLIENT_NAME))
        self.kite_installation_thread.sig_installation_status.connect(
            lambda status: self.client.start() if status == FINISHED else None)
        self.kite_installer.sig_visibility_changed.connect(
            self.show_status_tooltip)
        self.kite_status.sig_clicked.connect(self.show_installation_dialog)
        self.main.sig_setup_finished.connect(self.mainwindow_setup_finished)

        # Config
        self.update_configuration()

    @Slot(list)
    def http_client_ready(self, languages):
        logger.debug('Kite client is available for {0}'.format(languages))
        self.available_languages = languages
        self.sig_plugin_ready.emit(self.COMPLETION_CLIENT_NAME)

    @Slot()
    def mainwindow_setup_finished(self):
        """
        Called when the setup of the main window finished
        to let us do onboarding if necessary
        """
        self.show_installation_dialog()

    @Slot(bool)
    def show_status_tooltip(self, visible):
        """Show tooltip over the status widget for the installation process."""
        if self.is_installing() and not visible:
            text = _("Kite installation will continue in the backgroud<br>"
                     "Click on the status bar to show again the "
                     "installation dialog")
            self.kite_status.show_tooltip(text)

    @Slot()
    def show_installation_dialog(self):
        """Show installation dialog."""
        kite_installation_enabled = self.get_option('show_installation_dialog')
        installed, path = check_if_kite_installed()
        if (not installed and kite_installation_enabled
                and not running_under_pytest()):
            self.kite_installer.show()

    def send_request(self, language, req_type, req, req_id):
        if self.enabled and language in self.available_languages:
            self.client.sig_perform_request.emit(req_id, req_type, req)
        else:
            self.sig_response_ready.emit(self.COMPLETION_CLIENT_NAME,
                                         req_id, {})

    def start_client(self, language):
        return language in self.available_languages

    def start(self):
        # Always start client to support possibly undetected Kite builds
        self.client.start()
        installed, path = check_if_kite_installed()
        if installed:
            logger.debug('Kite was found on the system: {0}'.format(path))
            running = check_if_kite_running()
            if not running:
                logger.debug('Starting Kite service...')
                self.kite_process = run_program(path)

    def shutdown(self):
        self.client.stop()
        if self.kite_process is not None:
            self.kite_process.kill()

    def update_configuration(self):
        self.client.enable_code_snippets = CONF.get('lsp-server',
                                                    'code_snippets')
        self.enabled = self.get_option('enable')

    def open_file_update(self):
        """Current opened file changed."""
        self.open_file_updated = True

    def get_kite_status(self):
        """
        Get Kite status.

        Takes into account the current file in the Editor and
        installation process status
        """
        kite_status = status()
        if self.main and kite_status == RUNNING and self.open_file_updated:
            filename = self.main.editor.get_current_filename()
            kite_status = self.client.get_status(filename)
            if (kite_status is not None and kite_status['status'] == 'ready'
                    or kite_status['status'] == 'unsupported'):
                self.open_file_updated = False
        elif self.is_installing():
            kite_status = self.kite_installation_thread.status
        return kite_status

    def is_installing(self):
        """Check if an installation is taking place."""
        return self.kite_installation_thread.isRunning()
