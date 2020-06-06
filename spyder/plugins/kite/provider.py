# -*- coding: utf-8 -*-

# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""Kite completion provider."""

# Standard library imports
import functools
import logging

# Third party imports
from qtpy.QtCore import Signal, Slot

# Local imports
from spyder.plugins.completion.api import SpyderCompletionProvider
from spyder.plugins.kite.client import KiteClient
from spyder.plugins.kite.utils.status import (check_if_kite_installed,
                                              check_if_kite_running)
from spyder.utils.programs import run_program

# Logging
logger = logging.getLogger(__name__)


class KiteCompletionProvider(SpyderCompletionProvider):
    NAME = 'kite'

    sig_errored = Signal()

    def __init__(self, parent):
        super().__init__(parent)

        self.enable = None
        self.enable_code_snippets = None
        self.kite_process = None
        self.available_languages = None
        self.client = KiteClient(None)

        # Signals
        self.client.sig_client_started.connect(self._http_client_ready)
        self.client.sig_response_ready.connect(
            functools.partial(self.sig_response_ready.emit, self.NAME))

    # --- Private API
    # ------------------------------------------------------------------------
    @Slot(list)
    def _http_client_ready(self, languages):
        """
        Inform the client is ready and provide languages available.

        Parameters
        ----------
        languages: list
            List of languages supported by Kite.
        """
        logger.debug('Kite client is available for {0}'.format(languages))
        self.available_languages = languages
        self.sig_provider_ready.emit(self.NAME)

    # --- SpyderCompletionProvider API
    # ------------------------------------------------------------------------
    def start(self):
        try:
            if not self.enable:
                return

            installed, path = check_if_kite_installed()
            if not installed:
                return

            logger.debug('Kite was found on the system: {0}'.format(path))
            running = check_if_kite_running()
            if running:
                return

            logger.debug('Starting Kite service...')
            self.kite_process = run_program(path)
        except OSError:
            self.sig_errored.emit()
        finally:
            # Always start client to support possibly undetected Kite builds
            self.client.start()

    def shutdown(self):
        self.client.stop()
        if self.kite_process is not None:
            self.kite_process.kill()

    def start_client(self, language):
        return language in self.available_languages

    def stop_client(self, language):
        pass

    def register_file(self, language, filename, codeeditor):
        pass

    def send_request(self, language, req_type, req, req_id):
        if self.enable and language in self.available_languages:
            self.client.sig_perform_request.emit(req_id, req_type, req)
        else:
            self.sig_response_ready.emit(self.NAME, req_id, {})

    def send_status_request(self, filename):
        self.client.sig_perform_status_request.emit(filename)

    def update_configuration(self, options=None):
        if options:
            self.enable = options.get('enable', False)
            self.client.enable_code_snippets = options.get('code_snippets',
                                                           False)
