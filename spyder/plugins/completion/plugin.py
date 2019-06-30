
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
import functools

# Third-party imports
from qtpy.QtCore import QObject, Slot, QTimer

# Local imports
from spyder.config.base import get_conf_path, running_under_pytest
from spyder.config.lsp import PYTHON_CONFIG
from spyder.config.main import CONF
from spyder.api.completion import SpyderCompletionPlugin
from spyder.utils.misc import select_port, getcwd_or_home
from spyder.plugins.languageserver.plugin import LanguageServerPlugin
from spyder.plugins.fallback.plugin import FallbackPlugin
from spyder.plugins.languageserver import LSPRequestTypes
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
        self.first_completion = False
        self.req_id = 0
        self.completion_first_time = 1500
        self.waiting_time = 200

        self.plugin_priority = {
            LSPRequestTypes.DOCUMENT_COMPLETION: ['lsp-server', 'fallback'],
            LSPRequestTypes.DOCUMENT_SIGNATURE: ['lsp-server']
        }

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
    def recieve_response(self, completion_source, req_id, resp):
        request_responses = self.requests[req_id]
        request_responses.append((completion_source, resp))

    @Slot(str)
    def client_available(self, client_name):
        client_info = self.clients[client_name]
        client_info['status'] = self.RUNNING

    def gather_and_send(self, response_instance, req_type, req_id):
        responses = []
        if req_type == LSPRequestTypes.DOCUMENT_COMPLETION:
            pass
        elif req_type == LSPRequestTypes.DOCUMENT_SIGNATURE:
            pass

    def send_request(self, language, req_type, req, req_id):
        for client_name in self.clients:
            client_info = self.clients[client_name]
            if client_info['status'] == self.RUNNING:
                self.requests[req_id] = []
                client_info['plugin'].send_request(
                    language, req_type, req, req_id)
        wait_time = self.waiting_time
        if req_type == LSPRequestTypes.DOCUMENT_COMPLETION:
            if not self.first_completion:
                wait_time = self.completion_first_time
                self.first_completion = True
        response_instance = req['response_instance']
        timer = QTimer()
        timer.singleShot(
            wait_time, functools.partial(
                self.gather_and_send, response_instance, req_type, req_id))

    def send_notification(self, language, notification_type, notification):
        for client_name in self.clients:
            client_info = self.clients[client_name]
            if client_info['status'] == self.RUNNING:
                client_info['plugin'].send_notification(
                    language, notification_type, notification)

    def broadcast_notification(self, req_type, req):
        for client_name in self.clients:
            client_info = self.clients[client_name]
            if client_info['status'] == self.RUNNING:
                client_info['plugin'].broadcast_notification(
                    req_type, req)

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
