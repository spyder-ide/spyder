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

from spyder.api.exceptions import SpyderAPIError
from spyder.api.plugins import Plugins

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
        self._plugin_teardown_listeners = {}
        for method_name in dir(self):
            method = getattr(self, method_name, None)
            if hasattr(method, '_plugin_listen'):
                plugin_listen = method._plugin_listen

                # Check if plugin is listed among REQUIRES and OPTIONAL.
                # Note: We can't do this validation for the Layout plugin
                # because it depends on all plugins through the Plugins.All
                # wildcard.
                if (
                    self.NAME != Plugins.Layout and
                    (plugin_listen not in self.REQUIRES + self.OPTIONAL)
                ):
                    raise SpyderAPIError(
                        f"Method {method_name} of {self} is trying to watch "
                        f"plugin {plugin_listen}, but that plugin is not "
                        f"listed in REQUIRES nor OPTIONAL."
                    )

                logger.debug(
                    f'Method {method_name} is watching plugin {plugin_listen}'
                )
                self._plugin_listeners[plugin_listen] = method_name

            if hasattr(method, '_plugin_teardown'):
                plugin_teardown = method._plugin_teardown

                # Check if plugin is listed among REQUIRES and OPTIONAL.
                # Note: We can't do this validation for the Layout plugin
                # because it depends on all plugins through the Plugins.All
                # wildcard.
                if (
                    self.NAME != Plugins.Layout and
                    (plugin_teardown not in self.REQUIRES + self.OPTIONAL)
                ):
                    raise SpyderAPIError(
                        f"Method {method_name} of {self} is trying to watch "
                        f"plugin {plugin_teardown}, but that plugin is not "
                        f"listed in REQUIRES nor OPTIONAL."
                    )

                logger.debug(f'Method {method_name} will handle plugin '
                             f'teardown for {plugin_teardown}')
                self._plugin_teardown_listeners[plugin_teardown] = method_name

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

    def _on_plugin_teardown(self, plugin: str):
        """
        Handle plugin teardown and redirect it to plugin-specific teardown
        handlers.

        Parameters
        ----------
        plugin: str
            Name of the plugin that is going through its teardown process.
        """
        # Call plugin specific handler
        if plugin in self._plugin_teardown_listeners:
            method_name = self._plugin_teardown_listeners[plugin]
            method = getattr(self, method_name)
            logger.debug(f'Calling {method}')
            method()
