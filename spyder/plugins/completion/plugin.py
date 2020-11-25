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

logger = logging.getLogger(__name__)


class CompletionPlugin(SpyderPluginV2):
    """Spyder completion plugin."""

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

    def __init__(self, parent, configuration=None):
        super().__init__(parent, configuration)

        # Available completion providers
        self._available_providers = {}

        # Instantiated completion providers
        self._providers = {}

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
    def get_name(self):
        return _('Completion and linting')

    def get_description(self):
        return _('This plugin is on charge of handling and dispatching '
                 'completion and linting requests to multiple providers')


    # --------------- Private Completion Plugin methods -----------------------
    def _instantiate_and_register_provider(self, Provider):
        enabled_plugins = self.get_conf_option('enabled_plugins')
        provider_configurations = self.get_conf_option(
            'provider_configuration')

        provider_name = Provider.NAME
        is_provider_enabled = enabled_plugins.get(provider_name, True)
        if not is_provider_enabled:
            # Do not instantiate a disabled completion provider
            return

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
            for key in list(current_defaults.keys()):
                if current_defaults[key] != provider_defaults[key]:
                    current_defaults[key] = provider_defaults[key]
                    current_conf_values[key] = provider_defaults[key]
            if provider_conf_version.major != current_conf_version.major:
                # Check if keys were removed/renamed from the previous defaults
                pass


