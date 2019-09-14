# -*- coding: utf-8 -*-

# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""Kite completions HTTP client."""

# Standard library imports
import logging

# Third party imports
from qtpy.QtCore import QObject, QThread, Signal, QTimer, QMutex
import requests

# Local imports
from spyder.plugins.completion.kite import KITE_ENDPOINTS, KITE_REQUEST_MAPPING
from spyder.plugins.completion.kite.decorators import class_register
from spyder.plugins.completion.kite.providers import KiteMethodProviderMixIn
from spyder.py3compat import ConnectionError, ConnectionRefusedError


logger = logging.getLogger(__name__)


@class_register
class KiteClient(QObject, KiteMethodProviderMixIn):
    sig_response_ready = Signal(int, dict)
    sig_client_started = Signal(list)
    sig_client_not_responding = Signal()
    sig_perform_request = Signal(int, str, object)

    def __init__(self, parent, enable_code_snippets=True):
        QObject.__init__(self, parent)
        self.endpoint = None
        self.requests = {}
        self.languages = []
        self.mutex = QMutex()
        self.opened_files = {}
        self.thread_started = False
        self.enable_code_snippets = enable_code_snippets
        self.thread = QThread()
        self.moveToThread(self.thread)
        self.thread.started.connect(self.started)
        self.sig_perform_request.connect(self.perform_request)

    def start(self):
        if not self.thread_started:
            self.thread.start()
        logger.debug('Starting Kite HTTP session...')
        self.endpoint = requests.Session()
        self.languages = self.get_languages()
        self.sig_client_started.emit(self.languages)

    def started(self):
        self.thread_started = True

    def stop(self):
        if self.thread_started:
            logger.debug('Closing Kite HTTP session...')
            self.endpoint.close()
            self.thread.quit()

    def get_languages(self):
        verb, url = KITE_ENDPOINTS.LANGUAGES_ENDPOINT
        success, response = self.perform_http_request(verb, url)
        if response is None:
            response = ['python']
        return response

    def perform_http_request(self, verb, url, params=None):
        response = None
        success = False
        http_method = getattr(self.endpoint, verb)
        try:
            http_response = http_method(url, json=params)
        except Exception as error:
            logger.debug('Kite request error: {0}'.format(error))
            return False, None
        success = http_response.status_code == 200
        if success:
            try:
                response = http_response.json()
            except Exception:
                response = http_response.text
                response = None if response == '' else response
        return success, response

    def send(self, method, params, url_params):
        response = None
        if self.endpoint is not None and method in KITE_REQUEST_MAPPING:
            http_verb, path = KITE_REQUEST_MAPPING[method]
            path = path.format(**url_params)
            try:
                success, response = self.perform_http_request(
                    http_verb, path, params)
            except (ConnectionRefusedError, ConnectionError):
                return response
        return response

    def perform_request(self, req_id, method, params):
        if method in self.sender_registry:
            logger.debug('Perform {0} request with id {1}'.format(
                method, req_id))
            handler_name = self.sender_registry[method]
            handler = getattr(self, handler_name)
            response = handler(params)
            if method in self.handler_registry:
                converter_name = self.handler_registry[method]
                converter = getattr(self, converter_name)
                if response is not None:
                    response = converter(response)
            if response is not None:
                self.sig_response_ready.emit(req_id, response)
