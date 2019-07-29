# -*- coding: utf-8 -*-

# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""Kite completion HTTP client."""

# Standard library imports
import os
import os.path as osp
import sys
import logging
import functools

# Qt imports
from qtpy.QtCore import Slot

# Local imports
from spyder.utils.programs import run_program
from spyder.api.completion import SpyderCompletionPlugin
from spyder.plugins.completion.kite.client import KiteClient

# Third-party imports
import psutil

logger = logging.getLogger(__name__)


class KiteCompletionPlugin(SpyderCompletionPlugin):
    COMPLETION_CLIENT_NAME = 'kite'

    def __init__(self, parent):
        SpyderCompletionPlugin.__init__(self, parent)
        self.available_languages = []
        self.client = KiteClient(None)
        self.kite_process = None
        self.client.sig_client_started.connect(self.http_client_ready)
        self.client.sig_response_ready.connect(
            functools.partial(self.sig_response_ready.emit,
                              self.COMPLETION_CLIENT_NAME))

    @Slot(list)
    def http_client_ready(self, languages):
        logger.debug('Kite client is available for {0}'.format(languages))
        self.available_languages = languages
        self.sig_plugin_ready.emit(self.COMPLETION_CLIENT_NAME)

    def send_request(self, language, req_type, req, req_id):
        if language in self.available_languages:
            self.client.sig_perform_request.emit(req_id, req_type, req)

    def start_client(self, language):
        return language in self.available_languages

    def start(self):
        installed, path = self._check_if_kite_installed()
        if installed:
            logger.debug('Kite was found on the system: {0}'.format(path))
            running = self._check_if_kite_running()
            if not running:
                logger.debug('Starting Kite service...')
                self.kite_process = run_program(path)
            self.client.start()

    def shutdown(self):
        self.client.stop()
        if self.kite_process is not None:
            self.kite_process.kill()

    def _check_if_kite_installed(self):
        path = ''
        if os.name == 'nt':
            path = 'C:\\Program Files\\Kite\\kited.exe'
        elif sys.platform.startswith('linux'):
            path = osp.expanduser('~/.local/share/kite/kited')
        elif sys.platform == 'darwin':
            path = '/opt/kite/kited'
        return osp.exists(osp.realpath(path)), path

    def _check_if_kite_running(self):
        running = False
        for proc in psutil.process_iter(attrs=['pid', 'name', 'username']):
            if 'kited' in proc.name():
                logger.debug('Kite process already '
                             'running with PID {0}'.format(proc.pid))
                running = True
                break
        return running
