# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""
Spyder completion plugin.

This plugin is on charge of creating and managing multiple code completion and
introspection clients.
"""

# Standard library imports
from collections import defaultdict
from pkg_resources import parse_version, iter_entry_points
import logging

# Third-party imports
from qtpy.QtCore import QMutex, QMutexLocker, QTimer, Slot
from qtpy.QtWidgets import QMessageBox

# Local imports
from spyder.api.plugins import SpyderPluginV2
from spyder.config.base import _
from spyder.plugins.completion.api import (LSPRequestTypes,
                                           COMPLETION_ENTRYPOINT)
from spyder.utils import icon_manager as ima

logger = logging.getLogger(__name__)


class CompletionPlugin(SpyderPluginV2):
    """
    Spyder completion plugin.

    This class provides a completion and linting plugin for the editor in
    Spyder.

    This plugin works by forwarding all the completion/linting requests to a
    set of :class:`SpyderCompletionProvider` instances that are registered
    and discovered via entrypoints.

    This plugin can assume that `fallback`, `snippets` and `language_server`
    completion providers are available, since they are included as part of
    Spyder.

    TODO: Decide if Kite will be stripped from the core and moved into its
    own separate package.
    """

    NAME = 'completions'
    CONF_SECTION = 'completions'
    CONF_DEFAULTS = [
        ('enabled_plugins': {}),
        ('provider_configuration': {})
    ]
    CONF_VERSION = '0.1.0'

    # TODO: This should be implemented in order to have all completion plugins'
    # configuration pages under "Completion & Linting"
    CONF_WIDGET_CLASS = None

    # Ad Hoc polymorphism signals to make this plugin a completion provider
    # without inheriting from SpyderCompletionProvider

    # Use this signal to send a response back to the completion manager
    # str: Completion client name
    # int: Request sequence identifier
    # dict: Response dictionary
    sig_response_ready = Signal(str, int, dict)

    # Use this signal to indicate that the plugin is ready
    sig_plugin_ready = Signal(str)

    # Provider status constants
    RUNNING = 'running'
    STOPPED = 'stopped'

    def __init__(self, parent, configuration=None):
        super().__init__(parent, configuration)

        # Available completion providers
        self._available_providers = {}

        # Instantiated completion providers
        self._providers = {}

        # Mapping that indicates if there are completion services available
        # for a given language
        self.language_status = {}

        # Mapping that contains the ids and the current completion/linting
        # requests in progress
        self.requests = {}

        # Current request sequence identifier
        self.req_id = 0

        # Lock to prevent concurrent access to requests mapping
        self.collection_mutex = QMutex(QMutex.Recursive)

        # Timeout limit for a response to be received
        self.wait_for_ms = self.get_conf_option('completions_wait_for_ms',
                                                section='editor')

        # Find and instantiate all completion providers registered via
        # entrypoints
        for entry_point in iter_entry_points(COMPLETION_ENTRYPOINT):
            try:
                Provider = entry_point.load()
                self._instantiate_and_register_provider(Provider)
            except ImportError as e:
                logger.warning('Failed to load completion provider from entry '
                               f'point {entry_point}')

    # ---------------- Public Spyder API required methods ---------------------
    def get_name(self) -> str:
        return _('Completion and linting')

    def get_description(self) -> str:
        return _('This plugin is on charge of handling and dispatching, as '
                 'well of receiving the responses of completion and linting '
                 'requests sent to multiple providers.')

    def get_icon(self):
        return ima.get_icon('lspserver')

    def register(self):
        """Start all available completion providers."""
        for provider_name in self._providers:
            provider_info = self._providers[provider_name]
            if provider_info['status'] == self.STOPPED:
                # TODO: Register status bar widgets
                provider_info['instance'].start()

    def unregister(self):
        """Stop all running completion providers."""
        for provider_name in self._providers:
            provider_info = self._providers[provider_name]
            if provider_info['status'] == self.RUNNING:
                # TODO: Remove status bar widgets
                provider_info['instance'].shutdown()

    def on_close(self, cancelable=False) -> bool:
        """Check if any provider has any pending task before closing."""
        can_close = False
        for provider_name in self._providers:
            provider_info = self._providers[provider_name]
            if provider_info['status'] == self.RUNNING:
                provider = provider_info['instance']
                provider_can_close = provider.can_close()
                can_close |= provider_can_close
                if provider_can_close:
                    provider.shutdown()
        return can_close

    # ---------- Completion provider registering/start/stop methods -----------
    def _instantiate_and_register_provider(
            self, Provider: SpyderCompletionProvider):
        enabled_plugins = self.get_conf_option('enabled_plugins')
        provider_configurations = self.get_conf_option(
            'provider_configuration')

        provider_name = Provider.COMPLETION_CLIENT_NAME
        self._available_providers[provider_name] = Provider

        is_provider_enabled = enabled_plugins.get(provider_name, True)
        if not is_provider_enabled:
            # Do not instantiate a disabled completion provider
            return

        logger.debug("Completion plugin: Registering {0}".format(
            provider_name))

        provider_defaults = dict(Provider.CONF_DEFAULTS)
        if provider_name not in provider_configurations:
            # Pick completion provider default configuration options
            provider_config = {
                'version': provider_conf_version,
                'values': provider_defaults,
                'defaults': provider_defaults,
            }

            provider_configurations[provider_name] = provider_config

        # Check if there was any version changes between configurations
        provider_config = provider_configurations[provider_name]
        provider_conf_version = parse_version(Provider.CONF_VERSION)
        current_conf_version = parse_version(provider_config['version'])

        current_conf_values = provider_config['values']
        current_defaults = provider_config['defaults']

        # Check if there are new default values and copy them
        new_keys = provider_defaults.keys() - current_conf_values.keys()
        for new_key in new_keys:
            current_conf_values[new_key] = provider_defaults[new_key]
            current_defaults[new_key] = provider_defaults[new_key]

        if provider_conf_version > current_conf_version:
            # Check if default values were changed between versions,
            # causing an overwrite of the current options
            preserved_keys = current_defaults.keys() & provider_defaults.keys()
            for key in preserved_keys:
                if current_defaults[key] != provider_defaults[key]:
                    current_defaults[key] = provider_defaults[key]
                    current_conf_values[key] = provider_defaults[key]

            if provider_conf_version.major != current_conf_version.major:
                # Check if keys were removed/renamed from the previous defaults
                deleted_keys = (
                    current_defaults.keys() - provider_defaults.keys())
                for key in deleted_keys:
                    current_defaults.pop(key)
                    current_conf_values.pop(key)

        new_provider_config = {
            'version': provider_conf_version,
            'values': current_conf_values,
            'defaults': provider_defaults
        }
        provider_configurations[provider_name] = new_provider_config
        self.set_conf_option('provider_configuration', provider_configurations)

        provider_instance = Provider(self, new_provider_config)
        provider_instance.sig_provider_ready.connect(self.provider_available)
        provider_instance.sig_response_ready.connect(self.receive_response)

        self._providers[provider_name] = {
            'instance': provider_instance,
            'status': self.STOPPED
        }

    @Slot(str)
    def provider_available(self, provider_name: str):
        """Indicate that the completion provider `provider_name` is running."""
        client_info = self.clients[provider_name]
        client_info['status'] = self.RUNNING

    def start_provider(self, language: str) -> bool:
        """Start completion providers for a given programming language."""
        started = False
        language_clients = self.language_status.get(language, {})
        for provider_name in self._providers:
            provider_info = self._providers[provider_name]
            if provider_info['status'] == self.RUNNING:
                provider = provider_info['instance']
                provider_started = provider.start_provider(language)
                started |= provider_started
                language_providers[provider_name] = provider_started
        self.language_status[language] = language_providers
        return started

    def stop_provider(self, language: str):
        """Stop completion providers for a given programming language."""
        for provider_name in self._providers:
            provider_info = self._providers[provider_name]
            if provider_info['status'] == self.RUNNING:
                provider_info['instance'].stop_provider(language)
        self.language_status.pop(language)

    def get_provider(self, name: str) -> SpyderCompletionProvider:
        """Get the :class:`SpyderCompletionProvider` identified with `name`."""
        return self._providers[name]['instance']

    # --------------- Public completion API request methods -------------------
    def send_request(self, language: str, req_type: str, req: dict):
        """
        Send a completion or linting request to all available providers.

        The completion request `req_type` needs to have a response.

        Parameters
        ----------
        language: str
            Name of the programming language of the file that emits the
            request.
        req_type: str
            Type of request, one of
            :class:`spyder.plugins.completion.api.CompletionRequestTypes`
        req: dict
            Request body
            {
                'filename': str,
                **kwargs: request-specific parameters
            }
        req_id: int
            Request identifier for response
        """
        req_id = self.req_id
        self.req_id += 1

        self.requests[req_id] = {
            'language': language,
            'req_type': req_type,
            'response_instance': req['response_instance'],
            'sources': {},
            'timed_out': False,
        }

        # Start the timer on this request
        if self.wait_for_ms > 0:
            QTimer.singleShot(self.wait_for_ms,
                              lambda: self.receive_timeout(req_id))
        else:
            self.requests[req_id]['timed_out'] = True

        # Send request to all running completion providers
        for provider_name in self._providers:
            provider_info = self._providers[provider_name]
            provider_info['instance'].send_request(
                language, req_type, req, req_id)

    def send_notification(
            self, language: str, notification_type: str, notification: dict):
        """
        Send a notification to all available completion providers.

        Parameters
        ----------
        language: str
            Name of the programming language of the file that emits the
            request.
        notification_type: str
            Type of request, one of
            :class:`spyder.plugins.completion.api.CompletionRequestTypes`
        notification: dict
            Request body
            {
                'filename': str,
                **kwargs: notification-specific parameters
            }
        """
        for client_name in self.clients:
            client_info = self.clients[client_name]
            if client_info['status'] == self.RUNNING:
                client_info['plugin'].send_notification(
                    language, notification_type, notification)

    def broadcast_notification(self, req_type: str, req: dict):
        """
        Send a notification to all available completion providers for all
        programming languages.

        Parameters
        ----------
        req_type: str
            Type of request, one of
            :class:`spyder.plugins.completion.api.CompletionRequestTypes`
        req: dict
            Request body
            {
                'filename': str,
                **kwargs: notification-specific parameters
            }
        """
        for client_name in self.clients:
            client_info = self.clients[client_name]
            if client_info['status'] == self.RUNNING:
                client_info['plugin'].broadcast_notification(
                    req_type, req)

    # ----------------- Completion result processing methods ------------------
    @Slot(str, int, dict)
    def receive_response(
            self, completion_source: str, req_id: int, resp: dict):
        """Process request response from a completion provider."""
        logger.debug("Completion plugin: Request {0} Got response "
                     "from {1}".format(req_id, completion_source))

        if req_id not in self.requests:
            return

        with QMutexLocker(self.collection_mutex):
            request_responses = self.requests[req_id]
            request_responses['sources'][completion_source] = resp
            self.howto_send_to_codeeditor(req_id)




