# -*- coding: utf-8 -*-

# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""Kite completions HTTP client."""

# Standard library imports
import logging

# Qt imports
from qtpy.QtCore import QObject, QThread, Signal, QTimer, QMutex

# Local imports
from spyder.plugins.completion.kite import KITE_ENDPOINTS, KITE_REQUEST_MAPPING
from spyder.plugins.completion.kite.decorators import class_register
from spyder.plugins.completion.kite.providers import KiteMethodProviderMixIn

# Other imports
import requests


logger = logging.getLogger(__name__)


@class_register
class KiteClient(QObject, KiteMethodProviderMixIn):
    sig_response_ready = Signal(int, dict)
    sig_client_started = Signal(list)
    sig_client_not_responding = Signal()
    sig_perform_request = Signal(int, str, object)

    MAX_SERVER_CONTACT_RETRIES = 40

    def __init__(self, parent):
        QObject.__init__(self, parent)
        self.contact_retries = 0
        self.endpoint = None
        self.requests = {}
        self.languages = []
        self.mutex = QMutex()
        self.opened_files = {}
        self.alive = False
        self.thread_started = False
        self.thread = QThread()
        self.moveToThread(self.thread)
        self.thread.started.connect(self.started)
        self.sig_perform_request.connect(self.perform_request)

    def __wait_http_session_to_start(self):
        logger.debug('Waiting Kite HTTP endpoint to be available...')
        _, url = KITE_ENDPOINTS.ALIVE_ENDPOINT
        try:
            code = requests.get(url).status_code
        except Exception:
            code = 500

        if self.contact_retries == self.MAX_SERVER_CONTACT_RETRIES:
            logger.debug('Kite server is not answering')
            self.sig_client_not_responding.emit()
        elif code != 200:
            self.contact_retries += 1
            QTimer.singleShot(250, self.__wait_http_session_to_start)
        elif code == 200:
            self.alive = True
            self.start_client()

    def start(self):
        if not self.thread_started:
            self.thread.start()
        self.__wait_http_session_to_start()

    def start_client(self):
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
        return response

    def perform_http_request(self, verb, url, params=None):
        response = None
        success = False
        http_method = getattr(self.endpoint, verb)
        http_response = http_method(url, json=params)
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
            if self.alive:
                http_verb, path = KITE_REQUEST_MAPPING[method]
                path = path.format(**url_params)
                try:
                    success, response = self.perform_http_request(
                        http_verb, path, params)
                except (ConnectionRefusedError, ConnectionError):
                    self.alive = False
                    self.endpoint = None
                    self.contact_retries = 0
                    self.__wait_http_session_to_start()
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
                response = converter(response)
            if response is not None:
                self.sig_response_ready.emit(req_id, response)
