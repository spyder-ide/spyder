# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""
Spyder API plugin registration mixins.
"""

# Standard library imports
import logging
from typing import Any, Union, Optional
import warnings

logger = logging.getLogger(__name__)


class SpyderPluginObserver:
    """
    This mixin enables a class to receive notifications when a plugin
    is available, by registering methods using the
    :function:`spyder.api.plugin_registration.decorators.on_plugin_available`
    decorator.

    When any of the requested plugins is ready, the corresponding registered
    method is called.

    Notes
    -----
    This mixin will only operate over the plugin requirements listed under
    `REQUIRES` and `OPTIONAL` class constants.
    """

    def __init__(self):
        self._plugin_listeners = {}
        for method_name in dir(self):
            method = getattr(self, method_name, None)
            if hasattr(method, '_plugin_listen'):
                info = method._plugin_listen
                logger.debug(f'Method {method_name} is watching plugin {info}')
                self._plugin_listeners[info] = method_name

    def _on_plugin_available(self, plugin: str):
        """
        Handle plugin availability and redirect it to plugin-specific
        startup handlers.

        Parameters
        ----------
        plugin: str
            Name of the plugin that was notified as available.
        """
        # Call plugin specific handler
        if plugin in self._plugin_listeners:
            method_name = self._plugin_listeners[plugin]
            method = getattr(self, method_name)
            logger.debug(f'Calling {method}')
            method()

        # Call global plugin handler
        if '__all' in self._plugin_listeners:
            method_name = self._plugin_listeners['__all']
            method = getattr(self, method_name)
            method(plugin)
