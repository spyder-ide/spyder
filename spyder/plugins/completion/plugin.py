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
import logging
from pkg_resources import parse_version, iter_entry_points
from typing import List, Any

# Third-party imports
from qtpy.QtCore import QMutex, QMutexLocker, QTimer, Slot, Signal
from qtpy.QtWidgets import QMessageBox

# Local imports
from spyder.api.plugins import SpyderPluginV2
from spyder.config.base import _
from spyder.plugins.completion.api import (CompletionRequestTypes,
                                           SpyderCompletionProvider,
                                           COMPLETION_ENTRYPOINT)

logger = logging.getLogger(__name__)
COMPLETION_REQUESTS = [getattr(CompletionRequestTypes, c)
                       for c in dir(CompletionRequestTypes) if c.isupper()]


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

    TODO: Kite will be stripped from the Spyder core into its own completion
    provider.
    """

    NAME = 'completions'
    CONF_SECTION = 'completions'
    CONF_DEFAULTS = [
        ('enabled_providers', {}),
        ('provider_configuration', {}),
        ('request_priorities', {})
    ]
    CONF_VERSION = '0.1.0'
    CONF_FILE = False

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

    SKIP_INTERMEDIATE_REQUESTS = {
        CompletionRequestTypes.DOCUMENT_COMPLETION
    }

    def __init__(self, parent, configuration=None):
        super().__init__(parent, configuration)

        # Available completion providers
        self._available_providers = {}

        # Instantiated completion providers
        self.providers = {}

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

        # Completion request priority
        self.source_priority = {}

        # Projects plugin reference
        self.projects = None

        # Timeout limit for a response to be received
        self.wait_for_ms = self.get_conf_option('completions_wait_for_ms',
                                                section='editor')

        # Find and instantiate all completion providers registered via
        # entrypoints
        for entry_point in iter_entry_points(COMPLETION_ENTRYPOINT):
            try:
                logger.debug(f'Loading entry point: {entry_point}')
                Provider = entry_point.resolve()
                self._instantiate_and_register_provider(Provider)
            except ImportError as e:
                logger.warning('Failed to load completion provider from entry '
                               f'point {entry_point}')
                raise e

    # ---------------- Public Spyder API required methods ---------------------
    def get_name(self) -> str:
        return _('Completion and linting')

    def get_description(self) -> str:
        return _('This plugin is on charge of handling and dispatching, as '
                 'well of receiving the responses of completion and linting '
                 'requests sent to multiple providers.')

    def get_icon(self):
        return self.create_icon('lspserver')

    def register(self):
        """Start all available completion providers."""
        for provider_name in self.providers:
            provider_info = self.providers[provider_name]
            if provider_info['status'] == self.STOPPED:
                # TODO: Register status bar widgets
                provider_info['instance'].start()

    def unregister(self):
        """Stop all running completion providers."""
        for provider_name in self.providers:
            provider_info = self.providers[provider_name]
            if provider_info['status'] == self.RUNNING:
                # TODO: Remove status bar widgets
                provider_info['instance'].shutdown()

    def on_close(self, cancelable=False) -> bool:
        """Check if any provider has any pending task before closing."""
        can_close = False
        for provider_name in self.providers:
            provider_info = self.providers[provider_name]
            if provider_info['status'] == self.RUNNING:
                provider = provider_info['instance']
                provider_can_close = provider.can_close()
                can_close |= provider_can_close
                if provider_can_close:
                    provider.shutdown()
        return can_close

    # ---------- Completion provider registering/start/stop methods -----------
    def _merge_default_configurations(self,
                                      Provider: SpyderCompletionProvider,
                                      provider_name: str,
                                      provider_configurations: dict):
        provider_defaults = dict(Provider.CONF_DEFAULTS)
        provider_conf_version = Provider.CONF_VERSION
        if provider_name not in provider_configurations:
            # Pick completion provider default configuration options
            provider_config = {
                'version': provider_conf_version,
                'values': provider_defaults,
                'defaults': provider_defaults,
            }

            provider_configurations[provider_name] = provider_config

        # Check if there were any version changes between configurations
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

        return str(provider_conf_version), current_conf_values, provider_defaults

    def _instantiate_and_register_provider(
            self, Provider: SpyderCompletionProvider):
        enabled_plugins = self.get_conf_option('enabled_providers')
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

        # Merge configuration settings between a provider defaults and
        # the existing ones
        (provider_conf_version,
         current_conf_values,
         provider_defaults) = self._merge_default_configurations(
             Provider, provider_name, provider_configurations)

        new_provider_config = {
            'version': provider_conf_version,
            'values': current_conf_values,
            'defaults': provider_defaults
        }
        provider_configurations[provider_name] = new_provider_config

        # Update provider configurations
        self.set_conf_option('provider_configuration', provider_configurations)

        # Merge and update source priority order
        source_priorities = self.get_conf_option('request_priorities')
        provider_priority = Provider.DEFAULT_ORDER

        for request in COMPLETION_REQUESTS:
            request_priorities = source_priorities.get(request, {})
            if provider_name not in request_priorities:
                request_priorities[provider_name] = provider_priority - 1
            source_priorities[request] = request_priorities

        self.source_priority = source_priorities
        self.set_conf_option('request_priorities', source_priorities)

        provider_instance = Provider(self, new_provider_config['values'])
        provider_instance.sig_provider_ready.connect(self.provider_available)
        provider_instance.sig_response_ready.connect(self.receive_response)

        self.providers[provider_name] = {
            'instance': provider_instance,
            'status': self.STOPPED
        }

        for language in self.language_status:
            server_status = self.language_status[language]
            server_status[provider_name] = False

    @Slot(str)
    def provider_available(self, provider_name: str):
        """Indicate that the completion provider `provider_name` is running."""
        provider_info = self.providers[provider_name]
        provider_info['status'] = self.RUNNING

    def start_provider(self, language: str) -> bool:
        """Start completion providers for a given programming language."""
        started = False
        language_providers = self.language_status.get(language, {})
        for provider_name in self.providers:
            provider_info = self.providers[provider_name]
            if provider_info['status'] == self.RUNNING:
                provider = provider_info['instance']
                provider_started = provider.start_provider(language)
                started |= provider_started
                language_providers[provider_name] = provider_started
        self.language_status[language] = language_providers
        return started

    def stop_provider(self, language: str):
        """Stop completion providers for a given programming language."""
        for provider_name in self.providers:
            provider_info = self.providers[provider_name]
            if provider_info['status'] == self.RUNNING:
                provider_info['instance'].stop_provider(language)
        self.language_status.pop(language)

    def get_provider(self, name: str) -> SpyderCompletionProvider:
        """Get the :class:`SpyderCompletionProvider` identified with `name`."""
        return self.providers[name]['instance']

    def is_provider_running(self, name: str) -> bool:
        # TODO: Let LSP server emit sig_provider_ready
        # if name == LanguageServerPlugin.COMPLETION_CLIENT_NAME:
        #     # The LSP plugin does not emit a plugin ready signal
        #     return name in self.clients

        status = self.clients.get(name, {}).get('status', self.STOPPED)
        return status == self.RUNNING

    def available_providers_for_language(self, language: str) -> List[str]:
        providers = []
        if language in self.language_status:
            provider_status = self.language_status[language]
            providers = [p for p in provider_status if provider_status[p]]
        return providers

    def sort_providers_for_request(
            self, providers: List[str], req_type: str) -> List[str]:
        request_order = self.source_priority[req_type]
        return sorted(providers, key=lambda p: request_order[p])

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
        for provider_name in self.providers:
            provider_info = self.providers[provider_name]
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
        for provider_name in self.providers:
            provider_info = self.providers[provider_name]
            if provider_info['status'] == self.RUNNING:
                provider_info['instance'].send_notification(
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
        for provider_name in self.providers:
            provider_info = self.providers[provider_name]
            if provider_info['status'] == self.RUNNING:
                provider_info['instance'].broadcast_notification(
                    req_type, req)

    def project_path_update(self, project_path: str, update_kind='addition'):
        """
        Handle project path updates on Spyder.

        Parameters
        ----------
        project_path: str
            Path to the project folder modified
        update_kind: str
            Path update kind, one of
            :class:`spyder.plugins.completion.WorkspaceUpdateKind`
        """
        for provider_name in self.providers:
            provider_info = self.providers[provider_name]
            if provider_info['status'] == self.RUNNING:
                provider_info['instance'].project_path_update(
                    project_path, update_kind
                )

    def register_file(self, language: str, filename: str, codeeditor):
        """
        Register file to perform completions.
        If a language client is not available for a given file, then this
        method should keep a queue, such that files can be initialized once
        a server is available.

        Parameters
        ----------
        language: str
            Programming language of the given file
        filename: str
            Filename to register
        codeeditor: spyder.plugins.editor.widgets.codeeditor.CodeEditor
            Codeeditor to send the client configurations
        """
        for provider_name in self.providers:
            provider_info = self.providers[provider_name]
            if provider_info['status'] == self.RUNNING:
                provider_info['instance'].register_file(
                    language, filename, codeeditor
                )

    def update_configuration(self):
        """Handle completion option configuration updates."""
        self.wait_for_ms = self.get_conf_option('completions_wait_for_ms',
                                                section='editor')
        for provider_name in self.providers:
            provider_info = self.providers[provider_name]
            if provider_info['status'] == self.RUNNING:
                # TODO: Obtain individual provider settings
                conf = {}
                provider_info['instance'].update_configuration(conf)

    def get_global_option(
            self, option: str, default: Any = None, section: str) -> Any:
        """
        Retrieve an option value from the global Spyder configurations.

        Parameters
        ----------
        option: str
            Option name to lookup for in global Spyder configurations.
        default: Any
            Default value to return if `option_name` was not found.
        section: str
            Name of the configuration section in Spyder

        Returns
        -------
        Any
            Either the default value if `option_name` was not found on the
            settings or the actual value stored.
        """
        return self.get_conf_option(option, default=default, section=section)

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
            self.match_and_reply(req_id)

    @Slot(int)
    def receive_timeout(self, req_id: int):
        """Collect all provider completions and reply on timeout."""
        # On timeout, collect all completions and return to the user
        if req_id not in self.requests:
            return

        logger.debug("Completion plugin: Request {} timed out".format(req_id))

        with QMutexLocker(self.collection_mutex):
            request_responses = self.requests[req_id]
            request_responses['timed_out'] = True
            self.match_and_reply(req_id)

    def match_and_reply(self, req_id: int):
        """
        Decide how to send the responses corresponding to req_id to
        the instance that requested them.
        """
        if req_id not in self.requests:
            return
        request_responses = self.requests[req_id]
        language = request_responses['language'].lower()
        req_type = request_responses['req_type']

        # Wait only for the available providers for the given request
        available_providers = self.available_providers_for_language(language)
        sorted_providers = self.sort_providers_for_request(
            available_providers, req_type)
        timed_out = request_responses['timed_out']
        all_returned = all(source in request_responses['sources']
                           for source in sorted_providers)

        if not timed_out:
            # Before the timeout
            if all_returned:
                self.skip_and_reply(req_id)
        else:
            # After the timeout
            any_nonempty = any(request_responses['sources'].get(source)
                               for source in sorted_providers)
            if all_returned or any_nonempty:
                self.skip_and_reply(req_id)

    def skip_and_reply(self, req_id: int):
        """
        Skip intermediate responses coming from the same CodeEditor
        instance for some types of requests, and send the last one to
        it.
        """
        request_responses = self.requests[req_id]
        req_type = request_responses['req_type']
        response_instance = id(request_responses['response_instance'])
        do_send = True

        # This is necessary to prevent sending completions for old requests
        # See spyder-ide/spyder#10798
        if req_type in self.SKIP_INTERMEDIATE_REQUESTS:
            max_req_id = max(
                [key for key, item in self.requests.items()
                 if item['req_type'] == req_type
                 and id(item['response_instance']) == response_instance]
                or [-1])
            do_send = (req_id == max_req_id)

        logger.debug("Completion plugin: Request {} removed".format(req_id))
        del self.requests[req_id]

        # Send only recent responses
        if do_send:
            self.gather_and_reply(request_responses)

    def gather_and_reply(self, request_responses: dict):
        """
        Gather request responses from all plugins and send them to the
        CodeEditor instance that requested them.
        """
        req_type = request_responses['req_type']
        req_id_responses = request_responses['sources']
        response_instance = request_responses['response_instance']
        logger.debug('Gather responses for {0}'.format(req_type))

        if req_type == CompletionRequestTypes.DOCUMENT_COMPLETION:
            responses = self.gather_completions(req_id_responses)
        else:
            responses = self.gather_responses(req_type, req_id_responses)

        try:
            response_instance.handle_response(req_type, responses)
        except RuntimeError:
            # This is triggered when a codeeditor instance has been
            # removed before the response can be processed.
            pass


    def gather_completions(self, req_id_responses: dict):
        """Gather completion responses from plugins."""
        priorities = self.source_priority[
            CompletionRequestTypes.DOCUMENT_COMPLETION]
        priorities = sorted(list(priorities.keys()),
                            key=lambda p: priorities[p])

        merge_stats = {source: 0 for source in req_id_responses}
        responses = []
        dedupe_set = set()
        for priority, source in enumerate(priorities):
            if source not in req_id_responses:
                continue
            for response in req_id_responses[source].get('params', []):
                dedupe_key = response['label'].strip()
                if dedupe_key in dedupe_set:
                    continue
                dedupe_set.add(dedupe_key)

                response['sortText'] = (priority, response['sortText'])
                responses.append(response)
                merge_stats[source] += 1

        logger.debug('Responses statistics: {0}'.format(merge_stats))
        responses = {'params': responses}
        return responses

    def gather_responses(self, req_type: int, responses: dict):
        """Gather responses other than completions from plugins."""
        response = None
        for source in self.source_priority[req_type]:
            if source in responses:
                response = responses[source].get('params', None)
                if response:
                    break
        return {'params': response}
