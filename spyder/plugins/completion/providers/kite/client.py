# -*- coding: utf-8 -*-

# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""Kite completions HTTP client."""

# Standard library imports
import logging
from urllib.parse import quote

# Third party imports
from qtpy.QtCore import QObject, QThread, Signal, QMutex
from qtpy.QtWidgets import QMessageBox
import requests

# Local imports
from spyder.config.base import _, running_under_pytest
from spyder.plugins.completion.providers.kite import (
    KITE_ENDPOINTS, KITE_REQUEST_MAPPING)
from spyder.plugins.completion.providers.kite.decorators import class_register
from spyder.plugins.completion.providers.kite.providers import (
    KiteMethodProviderMixIn)
from spyder.plugins.completion.providers.kite.utils.status import (
    status, check_if_kite_running)
from spyder.py3compat import (
    ConnectionError, ConnectionRefusedError, TEXT_TYPES)


logger = logging.getLogger(__name__)


@class_register
class KiteClient(QObject, KiteMethodProviderMixIn):
    sig_response_ready = Signal(int, dict)
    sig_client_started = Signal(list)
    sig_client_not_responding = Signal()
    sig_perform_request = Signal(int, str, object)
    sig_perform_status_request = Signal(str)
    sig_status_response_ready = Signal((str,), (dict,))
    sig_perform_onboarding_request = Signal()
    sig_onboarding_response_ready = Signal(str)
    sig_client_wrong_response = Signal(str, object)

    def __init__(self, parent, enable_code_snippets=True):
        QObject.__init__(self, parent)
        self.endpoint = None
        self.requests = {}
        self.languages = []
        self.mutex = QMutex()
        self.opened_files = {}
        self.opened_files_status = {}
        self.thread_started = False
        self.enable_code_snippets = enable_code_snippets
        self.thread = QThread()
        self.moveToThread(self.thread)
        self.thread.started.connect(self.started)
        self.sig_perform_request.connect(self.perform_request)
        self.sig_perform_status_request.connect(self.get_status)
        self.sig_perform_onboarding_request.connect(self.get_onboarding_file)

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
        if not success:
            return []

        if response is None or isinstance(response, TEXT_TYPES):
            response = ['python']
        return response

    def _get_onboarding_file(self):
        """Perform a request to get kite's onboarding file."""
        verb, url = KITE_ENDPOINTS.ONBOARDING_ENDPOINT
        success, response = self.perform_http_request(verb, url)
        return response

    def get_onboarding_file(self):
        """Get onboarding file."""
        onboarding_file = self._get_onboarding_file()
        self.sig_onboarding_response_ready.emit(onboarding_file)

    def _get_status(self, filename):
        """Perform a request to get kite status for a file."""
        verb, url = KITE_ENDPOINTS.STATUS_ENDPOINT
        if filename:
            url_params = {'filename': filename}
        else:
            url_params = {'filetype': 'python'}
        success, response = self.perform_http_request(
            verb, url, url_params=url_params)
        return success, response

    def get_status(self, filename):
        """Get kite status for a given filename."""
        success_status, kite_status = self._get_status(filename)
        if not filename or kite_status is None:
            kite_status = status()
            self.sig_status_response_ready[str].emit(kite_status)
        elif isinstance(kite_status, TEXT_TYPES):
            status_str = status(extra_status=' with errors')
            long_str = _("<code>{error}</code><br><br>"
                         "Note: If you are using a VPN, "
                         "please don't route requests to "
                         "localhost/127.0.0.1 with it").format(
                             error=kite_status)
            kite_status_dict = {
                'status': status_str,
                'short': status_str,
                'long': long_str}
            self.sig_status_response_ready[dict].emit(kite_status_dict)
        else:
            self.sig_status_response_ready[dict].emit(kite_status)

    def perform_http_request(self, verb, url, url_params=None, params=None):
        response = None
        http_method = getattr(self.endpoint, verb)
        try:
            http_response = http_method(url, params=url_params, json=params)
        except Exception as error:
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
            encoded_url_params = {
                key: quote(value) if isinstance(value, TEXT_TYPES) else value
                for (key, value) in url_params.items()}
            path = path.format(**encoded_url_params)
            try:
                success, response = self.perform_http_request(
                    http_verb, path, params=params)
            except (ConnectionRefusedError, ConnectionError):
                return response
        return response

    def perform_request(self, req_id, method, params):
        response = None
        if method in self.sender_registry:
            logger.debug('Perform request {0} with id {1}'.format(
                method, req_id))
            handler_name = self.sender_registry[method]
            handler = getattr(self, handler_name)
            response = handler(params)
            if method in self.handler_registry:
                converter_name = self.handler_registry[method]
                converter = getattr(self, converter_name)
                if response is not None:
                    response = converter(response)
        if not isinstance(response, (dict, type(None))):
            if not running_under_pytest():
                self.sig_client_wrong_response.emit(method, response)
        else:
            self.sig_response_ready.emit(req_id, response or {})
