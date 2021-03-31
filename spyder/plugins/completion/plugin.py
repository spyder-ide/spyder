# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""
Spyder completion plugin.

This plugin is in charge of creating and managing multiple code completion and
introspection providers.
"""

# Standard library imports
from collections import defaultdict
import functools
import inspect
import logging
import os
from pkg_resources import parse_version, iter_entry_points
from typing import List, Any, Union, Optional, Tuple

# Third-party imports
from qtpy.QtCore import QMutex, QMutexLocker, QTimer, Slot, Signal
from qtpy.QtWidgets import QMessageBox

# Local imports
from spyder.config.manager import CONF
from spyder.api.plugins import SpyderPluginV2, Plugins
from spyder.config.base import _, running_under_pytest
from spyder.config.user import NoDefault
from spyder.plugins.completion.api import (CompletionRequestTypes,
                                           SpyderCompletionProvider,
                                           COMPLETION_ENTRYPOINT)
from spyder.plugins.completion.confpage import CompletionConfigPage
from spyder.plugins.completion.container import CompletionContainer


logger = logging.getLogger(__name__)

# List of completion requests
# e.g., textDocument/didOpen, workspace/configurationDidChange, etc.
COMPLETION_REQUESTS = [getattr(CompletionRequestTypes, c)
                       for c in dir(CompletionRequestTypes) if c.isupper()]


def partialclass(cls, *args, **kwds):
    """Return a partial class constructor."""
    class NewCls(cls):
        __init__ = functools.partialmethod(cls.__init__, *args, **kwds)
    return NewCls


class CompletionPlugin(SpyderPluginV2):
    """
    Spyder completion plugin.

    This class provides a completion and linting plugin for the editor in
    Spyder.

    This plugin works by forwarding all the completion/linting requests to a
    set of :class:`SpyderCompletionProvider` instances that are discovered
    and registered via entrypoints.

    This plugin can assume that `fallback`, `snippets`, `lsp` and `kite`
    completion providers are available, since they are included as part of
    Spyder.
    """

    NAME = 'completions'
    CONF_SECTION = 'completions'
    REQUIRES = [Plugins.Preferences]
    OPTIONAL = [Plugins.StatusBar, Plugins.MainMenu]

    CONF_FILE = False

    # Additional configuration tabs for this plugin, this attribute is
    # initialized dynamically based on the provider information.
    ADDITIONAL_CONF_TABS = {}

    # The configuration page is created dynamically based on the providers
    # loaded
    CONF_WIDGET_CLASS = None

    # Container used to store graphical widgets
    CONTAINER_CLASS = CompletionContainer

    # ------------------------------- Signals ---------------------------------
    sig_response_ready = Signal(str, int, dict)
    """
    This signal is used to receive a response from a completion provider.

    Parameters
    ----------
    completion_client_name: str
        Name of the completion client that produced this response.
    request_seq: int
        Sequence number for the request.
    response: dict
        Actual request corpus response.
    """

    sig_provider_ready = Signal(str)
    """
    This signal is used to indicate that a completion provider is ready
    to handle requests.

    Parameters
    ----------
    completion_client_name: str
        Name of the completion client.
    """

    sig_pythonpath_changed = Signal(object, object)
    """
    This signal is used to receive changes on the PythonPath.

    Parameters
    ----------
    prev_path: dict
        Previous PythonPath settings.
    new_path: dict
        New PythonPath settings.
    """

    sig_main_interpreter_changed = Signal()
    """
    This signal is used to report changes on the main Python interpreter.
    """

    sig_language_completions_available = Signal(dict, str)
    """
    This signal is used to indicate that completion services are available
    for a given programming language.

    Parameters
    ----------
    completion_capabilites: dict
        Available configurations supported by the providers, it should conform
        to `spyder.plugins.completion.api.SERVER_CAPABILITES`.
    language: str
        Name of the programming language whose completion capabilites are
        available.
    """

    sig_open_file = Signal(str)
    """
    This signal is used to open a file in the editor.

    Parameters
    ----------
    path: str
        Path to a file to open with the editor.
    """

    sig_editor_rpc = Signal(str, tuple, dict)
    """
    This signal is used to perform remote calls in the editor.

    Parameters
    ----------
    method: str
        Name of the method to call in the editor.
    args: tuple
        Tuple containing the positional arguments to perform the call.
    kwargs: dict
        Dictionary containing the optional arguments to perform the call.
    """

    sig_stop_completions = Signal(str)
    """
    This signal is used to stop completion services on other Spyder plugins
    that depend on them.

    Parameters
    ----------
    language: str
        Name of the programming language whose completion services are not
        available.
    """

    # --------------------------- Other constants -----------------------------
    RUNNING = 'running'
    STOPPED = 'stopped'

    SKIP_INTERMEDIATE_REQUESTS = {
        CompletionRequestTypes.DOCUMENT_COMPLETION
    }

    AGGREGATE_RESPONSES = {
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

        # Completion provider speed: slow or fast
        self.provider_speed = {}

        # Timeout limit for a response to be received
        self.wait_for_ms = self.get_conf('completions_wait_for_ms')

        # Find and instantiate all completion providers registered via
        # entrypoints
        for entry_point in iter_entry_points(COMPLETION_ENTRYPOINT):
            try:
                logger.debug(f'Loading entry point: {entry_point}')
                Provider = entry_point.resolve()
                self._instantiate_and_register_provider(Provider)
            except Exception as e:
                logger.warning('Failed to load completion provider from entry '
                               f'point {entry_point}')
                raise e

        # Register statusbar widgets
        self.register_statusbar_widgets()

        # Define configuration page and tabs
        (conf_providers, conf_tabs) = self.gather_providers_and_configtabs()
        self.CONF_WIDGET_CLASS = partialclass(
            CompletionConfigPage, providers=conf_providers)
        self.ADDITIONAL_CONF_TABS = {'completions': conf_tabs}

    # ---------------- Public Spyder API required methods ---------------------
    def get_name(self) -> str:
        return _('Completion and linting')

    def get_description(self) -> str:
        return _('This plugin is in charge of handling and dispatching, as '
                 'well as of receiving the responses of completion and '
                 'linting requests sent to multiple providers.')

    def get_icon(self):
        return self.create_icon('lspserver')

    def register(self):
        """Start all available completion providers."""
        preferences = self.get_plugin(Plugins.Preferences)
        preferences.register_plugin_preferences(self)

        container = self.get_container()
        statusbar = self.get_plugin(Plugins.StatusBar)
        if statusbar:
            for sb in container.all_statusbar_widgets():
                statusbar.add_status_widget(sb, 0)

        if self.main:
            self.main.sig_pythonpath_changed.connect(
                self.sig_pythonpath_changed)

        # Do not start providers on tests unless necessary
        if running_under_pytest():
            if not os.environ.get('SPY_TEST_USE_INTROSPECTION'):
                # Prevent providers from receiving configuration updates
                for provider_name in self.providers:
                    provider_info = self.providers[provider_name]
                    CONF.unobserve_configuration(provider_info['instance'])
                return

        self.start_all_providers()

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

    def after_configuration_update(self, options: List[Union[tuple, str]]):
        """
        Update plugin and/or provider configurations.

        Settings are propagated from changes on the configuration page and/or
        provider tabs.
        """
        providers_to_update = set({})
        for option in options:
            if option == 'completions_wait_for_ms':
                self.wait_for_ms = self.get_conf(
                    'completions_wait_for_ms')
            elif isinstance(option, tuple):
                option_name, provider_name, *__ = option
                if option_name == 'enabled_providers':
                    provider_status = self.get_conf(
                        ('enabled_providers', provider_name))
                    if provider_status:
                        self.start_provider_instance(provider_name)
                    else:
                        self.shutdown_provider_instance(provider_name)
                elif option_name == 'provider_configuration':
                    providers_to_update |= {provider_name}

        # FIXME: Remove this after migrating the ConfManager to an observer
        # pattern.
        editor_method_sec_opts = {
            'set_code_snippets_enabled': (self.CONF_SECTION,
                                          'enable_code_snippets'),
            'set_hover_hints_enabled':  (self.CONF_SECTION,
                                         'provider_configuration',
                                         'lsp',
                                         'values',
                                         'enable_hover_hints'),
            'set_format_on_save': (self.CONF_SECTION,
                                   'provider_configuration',
                                   'lsp',
                                   'values',
                                   'format_on_save'),
            'set_automatic_completions_enabled': ('editor',
                                                  'automatic_completions'),
            'set_completions_hint_enabled': ('editor', 'completions_hint'),
            'set_completions_hint_after_ms': ('editor',
                                              'completions_hint_after_ms'),
            'set_underline_errors_enabled': ('editor', 'underline_errors'),
            'set_automatic_completions_after_chars': (
                'editor', 'automatic_completions_after_chars'),
            'set_automatic_completions_after_ms': (
                'editor', 'automatic_completions_after_ms'),
            'set_edgeline_columns': (self.CONF_SECTION,
                                     'provider_configuration',
                                     'lsp',
                                     'values',
                                     'pycodestyle/max_line_length'),
            'set_edgeline_enabled': ('editor', 'edge_line'),
        }

        for method_name, (sec, *opt) in editor_method_sec_opts.items():
            opt = tuple(opt)
            if len(opt) == 1:
                opt = opt[0]
            if opt in options:
                opt_value = self.get_conf(opt, section=sec)
                self.sig_editor_rpc.emit('call_all_editorstacks',
                                         (method_name, (opt_value,)),
                                         {})

        # Update entries in the source menu
        # FIXME: Delete this after CONF is moved to an observer pattern.
        # and the editor migration starts
        self.sig_editor_rpc.emit('update_source_menu', (options,), {})

    def on_mainwindow_visible(self):
        for provider_name in self.providers:
            provider_info = self.providers[provider_name]
            provider_info['instance'].on_mainwindow_visible()

    # ---------------------------- Status bar widgets -------------------------
    def register_statusbar_widgets(self):
        """Register status bar widgets for all providers with the container."""
        container = self.get_container()
        for provider_key in self.providers:
            provider = self.providers[provider_key]['instance']
            container.register_statusbar_widgets(provider.STATUS_BAR_CLASSES)

    # -------- Completion provider initialization redefinition wrappers -------
    def gather_providers_and_configtabs(self):
        """
        Gather and register providers and their configuration tabs.

        This method iterates over all completion providers, takes their
        corresponding configuration tabs, and patches the methods that
        interact with writing/reading/removing configuration options to
        consider provider options that are stored inside this plugin's
        `provider_configuration` option, which makes providers unaware
        of the CompletionPlugin existence.
        """
        conf_providers = []
        conf_tabs = []
        widget_funcs = self.gather_create_ops()

        for provider_key in self.providers:
            provider = self.providers[provider_key]['instance']
            for tab in provider.CONF_TABS:
                # Add set_option/get_option/remove_option to tab definition
                setattr(tab, 'get_option',
                        self.wrap_get_option(provider_key))
                setattr(tab, 'set_option',
                        self.wrap_set_option(provider_key))
                setattr(tab, 'remove_option',
                        self.wrap_remove_option(provider_key))

                # Wrap apply_settings to return settings correctly
                setattr(tab, 'apply_settings',
                        self.wrap_apply_settings(tab, provider_key))

                # Wrap create_* methods to consider provider
                for name, pos in widget_funcs:
                    setattr(tab, name,
                            self.wrap_create_op(name, pos, provider_key))

            conf_tabs += provider.CONF_TABS
            conf_providers.append((provider_key, provider.get_name()))

        return conf_providers, conf_tabs

    def gather_create_ops(self):
        """
        Extract all the create_* methods declared in the
        :class:`spyder.api.preferences.PluginConfigPage` class
        """
        # Filter widget creation functions in ConfigPage
        members = inspect.getmembers(CompletionConfigPage)
        widget_funcs = []
        for name, call in members:
            if name.startswith('create_'):
                sig = inspect.signature(call)
                parameters = sig.parameters
                if 'option' in sig.parameters:
                    pos = -1
                    for param in parameters:
                        if param == 'option':
                            break
                        pos += 1
                    widget_funcs.append((name, pos))
        return widget_funcs

    def wrap_get_option(self, provider):
        """
        Wraps `get_option` method for a provider config tab to consider its
        actual section nested inside the `provider_configuration` key of this
        plugin options.

        This wrapper method allows configuration tabs to not be aware about
        their presence behind the completion plugin.
        """
        plugin = self

        def wrapper(self, option, default=NoDefault, section=None):
            if section is None:
                if isinstance(option, tuple):
                    option = ('provider_configuration', provider, 'values',
                              *option)
                else:
                    option = ('provider_configuration', provider, 'values',
                              option)
            return plugin.get_conf(option, default, section)
        return wrapper

    def wrap_set_option(self, provider):
        """
        Wraps `set_option` method for a provider config tab to consider its
        actual section nested inside the `provider_configuration` key of this
        plugin options.

        This wrapper method allows configuration tabs to not be aware about
        their presence behind the completion plugin.
        """
        plugin = self

        def wrapper(self, option, value, section=None,
                    recursive_notification=False):
            if section is None:
                if isinstance(option, tuple):
                    option = ('provider_configuration', provider, 'values',
                              *option)
                else:
                    option = ('provider_configuration', provider, 'values',
                              option)
            return plugin.set_conf(
                option, value, section,
                recursive_notification=recursive_notification)
        return wrapper

    def wrap_remove_option(self, provider):
        """
        Wraps `remove_option` method for a provider config tab to consider its
        actual section nested inside the `provider_configuration` key of this
        plugin options.

        This wrapper method allows configuration tabs to not be aware about
        their presence behind the completion plugin.
        """
        plugin = self

        def wrapper(self, option, section=None):
            if section is None:
                if isinstance(option, tuple):
                    option = ('provider_configuration', provider, 'values',
                              *option)
                else:
                    option = ('provider_configuration', provider, 'values',
                              option)
                return plugin.remove_conf(option, section)
        return wrapper

    def wrap_create_op(self, create_name, opt_pos, provider):
        """
        Wraps `create_*` methods for a provider config tab to consider its
        actual section nested inside the `provider_configuration` key of this
        plugin options.

        This wrapper method allows configuration tabs to not be aware about
        their presence behind the completion plugin.
        """
        def wrapper(self, *args, **kwargs):
            if kwargs.get('section', None) is None:
                arg_list = list(args)
                if isinstance(args[opt_pos], tuple):
                    arg_list[opt_pos] = (
                        'provider_configuration', provider, 'values',
                        *args[opt_pos])
                else:
                    arg_list[opt_pos] = (
                        'provider_configuration', provider, 'values',
                        args[opt_pos])
                args = tuple(arg_list)
            call = getattr(self.parent, create_name)
            widget = call(*args, **kwargs)
            widget.setParent(self)
            return widget
        return wrapper

    def wrap_apply_settings(self, Tab, provider):
        """
        Wraps `apply_settings` method for a provider config tab to consider its
        actual section nested inside the `provider_configuration` key of this
        plugin options.

        This wrapper method allows configuration tabs to not be aware about
        their presence behind the completion plugin.
        """
        prev_method = Tab.apply_settings

        def wrapper(self):
            wrapped_opts = set({})
            for opt in prev_method(self):
                if isinstance(opt, tuple):
                    wrapped_opts |= {('provider_configuration',
                                      provider, 'values', *opt)}
                else:
                    wrapped_opts |= {(
                        'provider_configuration', provider, 'values', opt)}
            return wrapped_opts
        return wrapper

    # ---------- Completion provider registering/start/stop methods -----------
    @staticmethod
    def _merge_default_configurations(Provider: SpyderCompletionProvider,
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

        return (str(provider_conf_version), current_conf_values,
                current_defaults)

    def get_provider_configuration(self, Provider: SpyderCompletionProvider,
                                   provider_name: str) -> dict:
        """Get provider configuration dictionary."""

        provider_configurations = self.get_conf(
            'provider_configuration')

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
        self.set_conf('provider_configuration', provider_configurations)
        return new_provider_config

    def update_request_priorities(self, Provider: SpyderCompletionProvider,
                                  provider_name: str):
        """Sort request priorities based on Provider declared order."""
        source_priorities = self.get_conf('request_priorities')
        provider_priority = Provider.DEFAULT_ORDER

        for request in COMPLETION_REQUESTS:
            request_priorities = source_priorities.get(request, {})
            self.provider_speed[provider_name] = Provider.SLOW
            request_priorities[provider_name] = provider_priority - 1
            source_priorities[request] = request_priorities

        self.source_priority = source_priorities
        self.set_conf('request_priorities', source_priorities)

    def connect_provider_signals(self, provider_instance):
        """Connect SpyderCompletionProvider signals."""
        container = self.get_container()

        provider_instance.sig_provider_ready.connect(self.provider_available)
        provider_instance.sig_response_ready.connect(self.receive_response)
        provider_instance.sig_exception_occurred.connect(
            self.sig_exception_occurred)
        provider_instance.sig_language_completions_available.connect(
            self.sig_language_completions_available)
        provider_instance.sig_disable_provider.connect(
            self.shutdown_provider_instance)
        provider_instance.sig_show_widget.connect(
            container.show_widget
        )
        provider_instance.sig_call_statusbar.connect(
            container.statusbar_rpc)
        provider_instance.sig_open_file.connect(self.sig_open_file)

        self.sig_pythonpath_changed.connect(
            provider_instance.python_path_update)
        self.sig_main_interpreter_changed.connect(
            provider_instance.main_interpreter_changed)

    def _instantiate_and_register_provider(
            self, Provider: SpyderCompletionProvider):
        provider_name = Provider.COMPLETION_PROVIDER_NAME
        self._available_providers[provider_name] = Provider

        logger.debug("Completion plugin: Registering {0}".format(
            provider_name))

        # Merge configuration settings between a provider defaults and
        # the existing ones
        provider_config = self.get_provider_configuration(
            Provider, provider_name)

        # Merge and update source priority order
        self.update_request_priorities(Provider, provider_name)

        # Instantiate provider
        provider_instance = Provider(self, provider_config['values'])

        # Signals
        self.connect_provider_signals(provider_instance)

        self.providers[provider_name] = {
            'instance': provider_instance,
            'status': self.STOPPED
        }

        for language in self.language_status:
            server_status = self.language_status[language]
            server_status[provider_name] = False

    def start_all_providers(self):
        """Start all detected completion providers."""
        for provider_name in self.providers:
            provider_info = self.providers[provider_name]
            if provider_info['status'] == self.STOPPED:
                provider_enabled = self.get_conf(
                    ('enabled_providers', provider_name), True)
                if provider_enabled:
                    provider_info['instance'].start()

    @Slot(str)
    def provider_available(self, provider_name: str):
        """Indicate that the completion provider `provider_name` is running."""
        provider_info = self.providers[provider_name]
        provider_info['status'] = self.RUNNING
        self.sig_provider_ready.emit(provider_name)

    def start_completion_services_for_language(self, language: str) -> bool:
        """Start completion providers for a given programming language."""
        started = False
        language_providers = self.language_status.get(language, {})
        for provider_name in self.providers:
            provider_info = self.providers[provider_name]
            if provider_info['status'] == self.RUNNING:
                provider = provider_info['instance']
                provider_started = (
                    provider.start_completion_services_for_language(language))
                started |= provider_started
                language_providers[provider_name] = provider_started
        self.language_status[language] = language_providers
        return started

    def stop_completion_services_for_language(self, language: str):
        """Stop completion providers for a given programming language."""
        for provider_name in self.providers:
            provider_info = self.providers[provider_name]
            instance = provider_info['instance']
            if provider_info['status'] == self.RUNNING:
                instance.stop_completion_services_for_language(language)
        self.language_status.pop(language)

    def get_provider(self, name: str) -> SpyderCompletionProvider:
        """Get the :class:`SpyderCompletionProvider` identified with `name`."""
        return self.providers[name]['instance']

    def is_provider_running(self, name: str) -> bool:
        """Return if provider is running."""
        status = self.clients.get(name, {}).get('status', self.STOPPED)
        return status == self.RUNNING

    def available_providers_for_language(self, language: str) -> List[str]:
        """Return the list of providers available for a given language."""
        providers = []
        if language in self.language_status:
            provider_status = self.language_status[language]
            providers = [p for p in provider_status if provider_status[p]]
        return providers

    def is_fallback_only(self, language: str) -> bool:
        """
        Return if fallback and snippets are the only available providers for
        a given language.
        """
        available_providers = set(
            self.available_providers_for_language(language))
        fallback_providers = {'snippets', 'fallback'}
        return (available_providers - fallback_providers) == set()

    def sort_providers_for_request(
            self, providers: List[str], req_type: str) -> List[str]:
        """Sort providers for a given request type."""
        request_order = self.source_priority[req_type]
        return sorted(providers, key=lambda p: request_order[p])

    def start_provider_instance(self, provider_name: str):
        """Start a given provider."""
        provider_info = self.providers[provider_name]
        if provider_info['status'] == self.STOPPED:
            provider_info['instance'].start()

    def shutdown_provider_instance(self, provider_name: str):
        """Shutdown a given provider."""
        provider_info = self.providers[provider_name]
        if provider_info['status'] == self.RUNNING:
            provider_info['instance'].shutdown()
            provider_info['status'] = self.STOPPED

    # ---------- Methods to create/access graphical elements -----------
    def create_action(self, *args, **kwargs):
        container = self.get_container()
        kwargs['parent'] = container
        return container.create_action(*args, **kwargs)

    def get_application_menu(self, *args, **kwargs):
        main_menu = self.get_plugin(Plugins.MainMenu)
        if main_menu:
            return main_menu.get_application_menu(*args, **kwargs)

    def get_menu(self, *args, **kwargs):
        container = self.get_container()
        return container.get_menu(*args, **kwargs)

    def create_application_menu(self, *args, **kwargs):
        main_menu = self.get_plugin(Plugins.MainMenu)
        if main_menu:
            return main_menu.create_application_menu(*args, **kwargs)

    def create_menu(self, *args, **kwargs):
        container = self.get_container()
        return container.create_menu(*args, **kwargs)

    def add_item_to_application_menu(self, *args, **kwargs):
        main_menu = self.get_plugin(Plugins.MainMenu)
        if main_menu:
            main_menu.add_item_to_application_menu(*args, **kwargs)

    def add_item_to_menu(self, *args, **kwargs):
        container = self.get_container()
        container.add_item_to_menu(*args, **kwargs)

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

        # Check if there are two or more slow completion providers
        # in order to start the timeout counter.
        providers = self.available_providers_for_language(language.lower())
        slow_provider_count = sum([self.provider_speed[p] for p in providers])


        # Start the timer on this request
        if req_type in self.AGGREGATE_RESPONSES and slow_provider_count > 2:
            if self.wait_for_ms > 0:
                QTimer.singleShot(self.wait_for_ms,
                                  lambda: self.receive_timeout(req_id))
            else:
                self.requests[req_id]['timed_out'] = True

        # Send request to all running completion providers
        for provider_name in providers:
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
        providers = self.available_providers_for_language(language.lower())
        for provider_name in providers:
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
            :class:`spyder.plugins.completion.api.CompletionRequestTypes`.
        req: dict
            Request body:
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

    def project_path_update(self, project_path: str, update_kind='addition',
                            instance=None):
        """
        Handle project path updates on Spyder.

        Parameters
        ----------
        project_path: str
            Path to the project folder being added or removed.
        update_kind: str
            Path update kind, one of
            :class:`spyder.plugins.completion.WorkspaceUpdateKind`.
        instance: object
            Reference to :class:`spyder.plugins.projects.plugin.Projects`.
        """
        for provider_name in self.providers:
            provider_info = self.providers[provider_name]
            if provider_info['status'] == self.RUNNING:
                provider_info['instance'].project_path_update(
                    project_path, update_kind, instance
                )

    @Slot(str, str)
    def file_opened_closed_or_updated(self, filename: str, language: str):
        """
        Handle file modifications and file switching events, including when a
        new file is created.

        Parameters
        ----------
        filename: str
            Path to the file that was changed/opened/focused.
        language: str
            Name of the programming language of the file that was
            changed/opened/focused.
        """
        if filename is not None and language is not None:
            for provider_name in self.providers:
                provider_info = self.providers[provider_name]
                if provider_info['status'] == self.RUNNING:
                    provider_info['instance'].file_opened_closed_or_updated(
                        filename, language)

    def register_file(self, language: str, filename: str, codeeditor):
        """
        Register file to perform completions.
        If a language client is not available for a given file, then this
        method should keep a queue, such that files can be initialized once
        a server is available.

        Parameters
        ----------
        language: str
            Programming language of the given file.
        filename: str
            Filename to register.
        codeeditor: spyder.plugins.editor.widgets.codeeditor.CodeEditor
            Codeeditor to send the client configurations.
        """
        for provider_name in self.providers:
            provider_info = self.providers[provider_name]
            if provider_info['status'] == self.RUNNING:
                provider_info['instance'].register_file(
                    language, filename, codeeditor
                )

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

        if req_type in self.AGGREGATE_RESPONSES:
            # Wait only for the available providers for the given request
            available_providers = self.available_providers_for_language(
                language)
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
        else:
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
        Gather request responses from all providers and send them to the
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
        """Gather completion responses from providers."""
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
        """Gather responses other than completions from providers."""
        response = None
        for source in self.source_priority[req_type]:
            if source in responses:
                response = responses[source].get('params', None)
                if response:
                    break
        return {'params': response}
