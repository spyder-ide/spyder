
# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""
Backend plugin to manage multiple code completion and introspection clients.
"""

# Standard library imports
import logging
import os
import os.path as osp

# Third-party imports
from qtpy.QtCore import QObject, Slot

# Local imports
from spyder.config.base import get_conf_path, running_under_pytest
from spyder.config.lsp import PYTHON_CONFIG
from spyder.config.main import CONF
from spyder.api.completion import SpyderCompletionPlugin
from spyder.utils.misc import select_port, getcwd_or_home
from spyder.plugins.languageserver.plugin import LanguageServerPlugin
from spyder.plugins.fallback.plugin import FallbackPlugin
# from spyder.plugins.languageserver.client import LSPClient
# from spyder.plugins.languageserver.confpage import LanguageServerConfigPage


logger = logging.getLogger(__name__)


class CompletionPlugin(SpyderCompletionPlugin):
    STOPPED = 'stopped'
    RUNNING = 'running'

    def __init__(self, parent):
        SpyderCompletionPlugin.__init__(self, parent)
        self.clients = {}
        self.requests = {}
        self.started = False
        self.req_id = 0

        lsp_client = LanguageServerPlugin(self)
        fallback = FallbackPlugin(self)
        self.register_completion_plugin(lsp_client)
        self.register_completion_plugin(fallback)

    def register_completion_plugin(self, plugin):
        plugin_name = plugin.COMPLETION_CLIENT_NAME
        self.clients[plugin_name] = {
            'plugin': plugin,
            'status': self.STOPPED
        }
        plugin.sig_response_ready.connect(self.recieve_response)
        plugin.sig_plugin_ready.connect(self.client_available)

    @Slot(str, int, dict)
    def recieve_response(self, language, req_id, resp):
        pass

    @Slot(str)
    def client_available(self, client_name):
        client_info = self.clients[client_name]
        client_info['status'] = self.RUNNING

    def send_request(self, language, req_type, req, req_id=None):
        for client_name in self.clients:
            client_info = self.clients[client_name]
            if client_info['status'] == self.RUNNING:
                client_info['plugin'].send_request(
                    language, req_type, req, req_id=None)

    def send_broadcast(self, req_type, req, req_id=None):
        for client_name in self.clients:
            client_info = self.clients[client_name]
            if client_info['status'] == self.RUNNING:
                client_info['plugin'].send_broadcast(
                    req_type, req, req_id=req_id)

    def start(self):
        for client_name in self.clients:
            client_info = self.clients[client_name]
            if client_info['status'] == self.STOPPED:
                client_info['plugin'].start()

    def shutdown(self):
        for client_name in self.clients:
            client_info = self.clients[client_name]
            if client_info['status'] == self.RUNNING:
                client_info['plugin'].shutdown()

    def start_client(self, language):
        for client_name in self.clients:
            client_info = self.clients[client_name]
            if client_info['status'] == self.RUNNING:
                client_info['plugin'].start_client(language)

    def stop_client(self, language):
        for client_name in self.clients:
            client_info = self.clients[client_name]
            if client_info['status'] == self.RUNNING:
                client_info['plugin'].stop_client(language)
