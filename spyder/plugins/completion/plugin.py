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
from qtpy.QtCore import QObject, Slot, QMutex, QMutexLocker

# Local imports
from spyder.config.base import get_conf_path, running_under_pytest
from spyder.config.lsp import PYTHON_CONFIG
from spyder.api.completion import SpyderCompletionPlugin
from spyder.utils.misc import select_port, getcwd_or_home
from spyder.plugins.completion.languageserver.plugin import (
    LanguageServerPlugin)
from spyder.plugins.completion.kite.plugin import KiteCompletionPlugin
from spyder.plugins.completion.fallback.plugin import FallbackPlugin
from spyder.plugins.completion.languageserver import LSPRequestTypes


logger = logging.getLogger(__name__)


class CompletionManager(SpyderCompletionPlugin):
    STOPPED = 'stopped'
    RUNNING = 'running'
    BASE_PLUGINS = {
        'lsp': LanguageServerPlugin,
        'fallback': FallbackPlugin,
        'kite': KiteCompletionPlugin
    }

    def __init__(self, parent, plugins=['lsp', 'kite', 'fallback']):
        SpyderCompletionPlugin.__init__(self, parent)
        self.clients = {}
        self.requests = {}
        self.language_status = {}
        self.started = False
        self.first_completion = False
        self.req_id = 0
        self.completion_first_time = 500
        self.waiting_time = 1000
        self.collection_mutex = QMutex()

        self.plugin_priority = {
            LSPRequestTypes.DOCUMENT_COMPLETION: 'lsp',
            LSPRequestTypes.DOCUMENT_SIGNATURE: 'lsp',
            LSPRequestTypes.DOCUMENT_HOVER: 'lsp',
            'all': 'lsp'
        }

        self.response_priority = [
            'lsp', 'kite', 'fallback'
        ]

        for plugin in plugins:
            if plugin in self.BASE_PLUGINS:
                Plugin = self.BASE_PLUGINS[plugin]
                plugin_client = Plugin(self.main)
                self.register_completion_plugin(plugin_client)

    def register_completion_plugin(self, plugin):
        logger.debug("Completion plugin: Registering {0}".format(
            plugin.COMPLETION_CLIENT_NAME))
        plugin_name = plugin.COMPLETION_CLIENT_NAME
        self.clients[plugin_name] = {
            'plugin': plugin,
            'status': self.STOPPED
        }
        plugin.sig_response_ready.connect(self.receive_response)
        plugin.sig_plugin_ready.connect(self.client_available)
        for language in self.language_status:
            server_status = self.language_status[language]
            server_status[plugin_name] = False

    @Slot(str, int, dict)
    def receive_response(self, completion_source, req_id, resp):
        logger.debug("Completion plugin: Request {0} Got response "
                     "from {1}".format(req_id, completion_source))
        with QMutexLocker(self.collection_mutex):
            request_responses = self.requests[req_id]
            req_type = request_responses['req_type']
            language = request_responses['language']
            request_responses['sources'][completion_source] = resp
        corresponding_source = self.plugin_priority.get(req_type, 'lsp')
        is_src_ready = self.language_status[language].get(
            corresponding_source, False)
        if corresponding_source == completion_source:
            response_instance = request_responses['response_instance']
            self.gather_and_send(
                completion_source, response_instance, req_type, req_id)
        else:
            # Preferred completion source is not available
            # Requests are handled in a first come, first served basis
            if not is_src_ready:
                response_instance = request_responses['response_instance']
                self.gather_and_send(
                    completion_source, response_instance, req_type, req_id)

    @Slot(str)
    def client_available(self, client_name):
        client_info = self.clients[client_name]
        client_info['status'] = self.RUNNING

    def gather_completions(self, principal_source, req_id_responses):
        merge_stats = {source: 0 for source in req_id_responses}
        responses = req_id_responses[principal_source]['params']
        available_completions = {x['insertText'] for x in responses}
        priority_level = 1
        for source in req_id_responses:
            logger.debug(source)
            if source == principal_source:
                merge_stats[source] += len(
                    req_id_responses[source]['params'])
                continue
            source_responses = req_id_responses[source]['params']
            for response in source_responses:
                if response['insertText'] not in available_completions:
                    response['sortText'] = (
                        'z' + 'z' * priority_level + response['sortText'])
                    responses.append(response)
                    merge_stats[source] += 1
            priority_level += 1
        logger.debug('Responses statistics: {0}'.format(merge_stats))
        responses = {'params': responses}
        return responses

    def gather_default(self, responses, default=''):
        response = ''
        for source in self.response_priority:
            response = responses.get(source, {'params': default})
            response = response['params']
            if response is not None and len(response) > 0:
                break
        return {'params': response}

    def gather_and_send(self,
                        principal_source, response_instance, req_type, req_id):
        logger.debug('Gather responses for {0}'.format(req_type))
        responses = []
        req_id_responses = self.requests[req_id]['sources']
        if req_type == LSPRequestTypes.DOCUMENT_COMPLETION:
            # principal_source = self.plugin_priority[req_type]
            responses = self.gather_completions(
                principal_source, req_id_responses)
        elif req_type == LSPRequestTypes.DOCUMENT_HOVER:
            responses = self.gather_default(req_id_responses, '')
        elif req_type == LSPRequestTypes.DOCUMENT_SIGNATURE:
            responses = self.gather_default(req_id_responses, None)
        else:
            principal_source = self.plugin_priority['all']
            responses = req_id_responses[principal_source]
        response_instance.handle_response(req_type, responses)

    def send_request(self, language, req_type, req, req_id=None):
        req_id = self.req_id
        for client_name in self.clients:
            client_info = self.clients[client_name]
            if client_info['status'] == self.RUNNING:
                self.requests[req_id] = {
                    'req_type': req_type,
                    'response_instance': req['response_instance'],
                    'language': language,
                    'sources': {}
                }
                client_info['plugin'].send_request(
                    language, req_type, req, req_id)
        if req['requires_response']:
            self.req_id += 1

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

    def project_path_update(self, project_path, update_kind='addition'):
        for client_name in self.clients:
            client_info = self.clients[client_name]
            if client_info['status'] == self.RUNNING:
                client_info['plugin'].project_path_update(
                    project_path, update_kind
                )

    def register_file(self, language, filename, codeeditor):
        for client_name in self.clients:
            client_info = self.clients[client_name]
            if client_info['status'] == self.RUNNING:
                client_info['plugin'].register_file(
                    language, filename, codeeditor
                )

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
        started = False
        language_clients = self.language_status.get(language, {})
        for client_name in self.clients:
            client_info = self.clients[client_name]
            if client_info['status'] == self.RUNNING:
                client_started = client_info['plugin'].start_client(language)
                started |= client_started
                language_clients[client_name] = client_started
        self.language_status[language] = language_clients
        return started

    def stop_client(self, language):
        for client_name in self.clients:
            client_info = self.clients[client_name]
            if client_info['status'] == self.RUNNING:
                client_info['plugin'].stop_client(language)
        self.language_status.pop(language)

    def get_client(self, name):
        return self.clients[name]['plugin']
