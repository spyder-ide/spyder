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
from spyder.config.manager import CONF
from spyder.utils.programs import run_program
from spyder.api.completion import SpyderCompletionPlugin
from spyder.plugins.completion.kite.client import KiteClient
from spyder.plugins.completion.kite.utils.status import (
    check_if_kite_running, check_if_kite_installed)
from spyder.plugins.completion.kite.utils.install import (
    KiteInstallationThread, FINISHED)
from spyder.plugins.completion.kite.widgets.install import KiteInstallerDialog


logger = logging.getLogger(__name__)


class KiteCompletionPlugin(SpyderCompletionPlugin):
    COMPLETION_CLIENT_NAME = 'kite'

    def __init__(self, parent):
        SpyderCompletionPlugin.__init__(self, parent)
        self.available_languages = []
        enable_code_snippets = CONF.get('lsp-server', 'code_snippets')
        self.client = KiteClient(None, enable_code_snippets)
        self.kite_process = None
        self.kite_installation_thread = KiteInstallationThread(self)
        # TODO: Connect thread status to status bar
        self.kite_installer = KiteInstallerDialog(
            parent,
            self.kite_installation_thread)
        self.client.sig_client_started.connect(self.http_client_ready)
        self.client.sig_response_ready.connect(
            functools.partial(self.sig_response_ready.emit,
                              self.COMPLETION_CLIENT_NAME))
        self.kite_installation_thread.sig_installation_status.connect(
            lambda status: self.client.start() if status == FINISHED else None)
        self.main.sig_setup_finished.connect(self.mainwindow_setup_finished)

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
        :return:
        """
        self._show_installation_dialog()

    def _show_installation_dialog(self):
        """Show installation dialog."""
        kite_installation_enabled = self.get_option('install_enable', True)
        if kite_installation_enabled:
            self.kite_installer.show()
            self.kite_installer.center()

    def send_request(self, language, req_type, req, req_id):
        if language in self.available_languages:
            self.client.sig_perform_request.emit(req_id, req_type, req)

    def start_client(self, language):
        return language in self.available_languages

    def start(self):
        installed, path = check_if_kite_installed()
        if installed:
            logger.debug('Kite was found on the system: {0}'.format(path))
            running = check_if_kite_running()
            if not running:
                logger.debug('Starting Kite service...')
                self.kite_process = run_program(path)
            self.client.start()

    def shutdown(self):
        self.client.stop()
        if self.kite_process is not None:
            self.kite_process.kill()

    def update_configuration(self):
        enable_code_snippets = CONF.get('lsp-server', 'code_snippets')
        self.client.enable_code_snippets = enable_code_snippets

    def is_installing(self):
        """Check if an installation is taking place."""
        return self.kite_installation_thread.isRunning()
