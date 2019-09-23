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


logger = logging.getLogger(__name__)


class KiteCompletionPlugin(SpyderCompletionPlugin):
    COMPLETION_CLIENT_NAME = 'kite'

    def __init__(self, parent):
        SpyderCompletionPlugin.__init__(self, parent)
        self.available_languages = []
        enable_code_snippets = CONF.get('lsp-server', 'code_snippets')
        self.client = KiteClient(None, enable_code_snippets)
        self.kite_process = None
        self.main_window_visible = False
        self.kite_initialized = False
        self.client.sig_client_started.connect(self.http_client_ready)
        self.client.sig_response_ready.connect(
            functools.partial(self.sig_response_ready.emit,
                              self.COMPLETION_CLIENT_NAME))
        self.main.sig_setup_finished.connect(self.mainwindow_setup_finished)

    @Slot(list)
    def http_client_ready(self, languages):
        logger.debug('Kite client is available for {0}'.format(languages))
        self.available_languages = languages
        self.sig_plugin_ready.emit(self.COMPLETION_CLIENT_NAME)
        self.kite_initialized = True
        self._kite_onboarding()

    @Slot()
    def mainwindow_setup_finished(self):
        """
        Called when the setup of the main window finished
        to let us do onboarding if necessary
        :return:
        """
        self.main_window_visible = True
        self._kite_onboarding()

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

    def _kite_onboarding(self):
        """
        Opens the onboarding file, which is retrieved
        from the Kite HTTP endpoint. This skips onboarding if onboarding
        is not possible yet or has already been displayed before.
        :return:
        """
        if not  self.main_window_visible \
                and self.kite_initialized \
                and self.get_option('kite_show_onboarding', True):
            onboarding_file = self.client.get_onboarding_file()
            if onboarding_file is None:
                # fixme: show onboarding notification
                pass
            else:
                self.set_option('kite_show_onboarding', False)
                self.main.open_file(onboarding_file)
