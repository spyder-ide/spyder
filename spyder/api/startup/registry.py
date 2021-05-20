# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""Global plugin registry."""

# Standard library imports
import logging
from typing import Dict, List, Union, Type, Any
import weakref

# Third-party library imports
from qtpy.QtCore import QObject, Signal

# Local imports
from spyder.config.manager import CONF
from spyder.api.enum import Plugins
from spyder.api.exceptions import SpyderAPIError
from spyder.api.plugins import (
    SpyderPluginV2, SpyderDockablePlugin, SpyderPluginWidget,
    SpyderPlugin)


# TODO: Remove SpyderPlugin and SpyderPluginWidget once the migration
# is complete.
Spyder5PluginClass = Union[SpyderPluginV2, SpyderDockablePlugin]
Spyder4PluginClass = Union[SpyderPlugin, SpyderPluginWidget]
SpyderPluginClass = Union[Spyder4PluginClass, Spyder5PluginClass]


ALL_PLUGINS = [getattr(Plugins, attr) for attr in dir(Plugins)
               if not attr.startswith('_') and attr != 'All']

logger = logging.getLogger(__name__)


class SpyderPluginRegistry(QObject):
    """
    Global plugin registry.

    This class handles a plugin initialization/teardown lifetime, including
    notifications when a plugin is available or not.

    This registry alleviates the limitations of a topological sort-based
    plugin initialization by enabling plugins to have bidirectional
    dependencies instead of unidirectional ones.

    Notes
    -----
    1. This class should be instantiated as a singleton.
    2. This class is the only that has hard references to all Spyder plugins.
       If another object wants to access a plugin, it should call the
       `get_plugin` method of this class, which will return a weak reference
       to the plugin.
    3. A plugin should not depend on other plugin to perform its
       initialization since it could cause deadlocks.
    """

    sig_plugin_ready = Signal(str)
    """
    This signal is used to signal the main window that a plugin is ready.

    Parameters
    ----------
    plugin_name: str
        Name of the plugin that is available.
    """

    def __init__(self):
        super().__init__()
        # Dictionary that maps a plugin name to a list of the plugin names
        # that depend on it.
        self.plugin_dependents = {}  # type: Dict[str, Dict[str, List[str]]]

        # Dictionary that maps a plugin name to a list of the plugin names
        # that the plugin depends on.
        self.plugin_dependencies = {}  # type: Dict[str, Dict[str, List[str]]]

        # Plugin dictionary mapped by their names
        self.plugin_registry = {}  # type: Dict[str, SpyderPluginClass]

        # Dictionary that maps a plugin name to its availability.
        self.plugin_availability = {}  # type: Dict[str, bool]

        # Set that stores the plugin names of all Spyder 4 plugins.
        self.old_plugins = set({})  # type: set[str]

        # Set that stores the names of the plugins that are enabled
        self.enabled_plugins = set({})

    # ------------------------- PRIVATE API -----------------------------------
    def _update_dependents(self, plugin: str, dependent_plugin: str, key: str):
        """Add `dependent_plugin` to the list of dependents of `plugin`."""
        plugin_dependents = self.plugin_dependents.get(plugin, {})
        plugin_strict_dependents = plugin_dependents.get(key, [])
        plugin_strict_dependents.append(dependent_plugin)
        plugin_dependents[key] = plugin_strict_dependents
        self.plugin_dependents[plugin] = plugin_dependents

    def _update_dependencies(self, plugin: str, required_plugin: str,
                             key: str):
        """Add `required_plugin` to the list of dependencies of `plugin`."""
        plugin_dependencies = self.plugin_dependencies.get(plugin, {})
        plugin_strict_dependencies = plugin_dependencies.get(key, [])
        plugin_strict_dependencies.append(required_plugin)
        plugin_dependencies[key] = plugin_strict_dependencies
        plugin_dependencies[plugin] = plugin_dependencies

    def _update_plugin_info(self, plugin_name: str,
                            required_plugins: List[str],
                            optional_plugins: List[str]):
        """Update the dependencies and dependents of `plugin_name`."""
        for plugin in required_plugins:
            self._update_dependencies(plugin_name, plugin, 'requires')
            self._update_dependents(plugin, plugin_name, 'requires')

        for plugin in optional_plugins:
            self._update_dependencies(plugin_name, plugin, 'optional')
            self._update_dependents(plugin, plugin_name, 'optional')

    def _instantiate_spyder5_plugin(
            self, main_window: Any,
            PluginClass: Type[Spyder5PluginClass]) -> Spyder5PluginClass:
        """Instantiate and register a Spyder 5+ plugin."""
        required_plugins = list(set(PluginClass.REQUIRES))
        optional_plugins = list(set(PluginClass.OPTIONAL))
        plugin_name = PluginClass.NAME

        logger.debug(f'Registering plugin {plugin_name} - {PluginClass}')

        for plugin in list(required_plugins):
            if plugin == Plugins.All:
                required_plugins = list(set(required_plugins + ALL_PLUGINS))

        for plugin in list(optional_plugins):
            if plugin == Plugins.All:
                optional_plugins = list(set(optional_plugins + ALL_PLUGINS))

        # Update plugin dependency information
        self._update_plugin_info(plugin_name, required_plugins,
                                 optional_plugins)

        # Create and store plugin instance
        plugin_instance = PluginClass(main_window, configuration=CONF)
        self.plugin_registry[plugin_name] = plugin_instance

        # Connect plugin availability signal to notification system
        plugin_instance.sig_plugin_ready.connect(
            lambda: self.notify_plugin_availability(plugin_name))

        # Initialize plugin instance
        plugin_instance.initialize()

        # Register plugins that are already available
        for plugin in required_plugins + optional_plugins:
            if self.plugin_availability.get(plugin, False):
                plugin_instance._on_plugin_available(plugin)

        return plugin_instance

    def _instantiate_spyder4_plugin(
            self, main_window: Any,
            PluginClass: Type[Spyder4PluginClass],
            args: tuple, kwargs: dict) -> weakref.ProxyType:
        """Instantiate and register a Spyder 4 plugin."""
        plugin_name = PluginClass.NAME

        # Create old plugin instance
        plugin_instance = PluginClass(main_window, *args, **kwargs)
        plugin_instance.register_plugin()

        # Register plugin in the registry
        self.plugin_registry[plugin_name] = plugin_instance

        # Since Spyder 5+ plugins are loaded before old ones, preferences
        # will be available at this point.
        preferences = self.get_plugin(Plugins.Preferences)
        preferences.register_plugin_preferences(plugin_instance)

        # Notify new-API plugins that depend on old ones
        plugin_dependents = self.plugin_dependents.get(plugin_name, {})
        required_plugins = plugin_dependents.get('requires', [])
        optional_plugins = plugin_dependents.get('optional', [])

        for plugin in required_plugins + optional_plugins:
            plugin_instance = self.plugin_registry[plugin]
            plugin._on_plugin_available(plugin_name)

        return plugin_instance

    # -------------------------- PUBLIC API -----------------------------------
    def register_plugin(
            self, main_window: Any,
            PluginClass: Type[SpyderPluginClass],
            *args: tuple, **kwargs: dict) -> weakref.ProxyType:
        """
        Register a plugin into the Spyder registry.

        Parameters
        ----------
        main_window: spyder.app.mainwindow.MainWindow
            Reference to Spyder's main window.
        PluginClass: type[SpyderPluginClass]
            The class of the plugin to register and create. It must be
            one of `spyder.app.registry.SpyderPluginClass`.
        *args: tuple
            Positional arguments used to initialize the plugin
            instance.
        **kwargs: dict
            Optional keyword arguments used to initialize the plugin instance.

        Returns
        -------
        plugin: weakref.ProxyType
            The instance of the plugin registered.

        Raises
        ------
        TypeError
            If the `PluginClass` does not inherit from any of
            `spyder.app.registry.SpyderPluginClass`

        Notes
        -----
        The optional `*args` and `**kwargs` will be removed once all the
        plugins are migrated.
        """
        if not issubclass(PluginClass, (SpyderPluginV2, SpyderPlugin)):
            raise TypeError(f'{PluginClass} does not inherit from '
                            f'{SpyderPluginV2} nor {SpyderPlugin}')

        instance = None
        if issubclass(PluginClass, SpyderPluginV2):
            # Register a Spyder 5+ plugin
            instance = self._instantiate_spyder5_plugin(
                main_window, PluginClass)
        elif issubclass(PluginClass, SpyderPlugin):
            # Register a Spyder 4 plugin
            instance = self._instantiate_spyder4_plugin(
                main_window, PluginClass, args, kwargs)

        return weakref.proxy(instance)

    def notify_plugin_availability(self, plugin_name: str):
        """
        Notify dependent plugins of a given plugin of its availability.

        Parameters
        ----------
        plugin_name: str
            Name of the plugin that is available.
        """
        # Set plugin availability to True
        self.plugin_availability[plugin_name] = True

        # Notify the main window that the plugin is ready
        self.sig_plugin_ready.emit(plugin_name)

        # Notify plugin dependencies
        plugin_dependencies = self.plugin_dependencies.get(plugin_name, {})
        required_plugins = plugin_dependencies.get('requires', [])
        optional_plugins = plugin_dependencies.get('optional', [])

        for plugin in required_plugins + optional_plugins:
            if plugin in self.plugin_registry:
                plugin_instance = self.plugin_registry[plugin]
                plugin._on_plugin_available(plugin_name)

    def get_plugin(self, plugin_name: str) -> weakref.ProxyType:
        """
        Get a reference to a plugin instance by its name.

        Parameters
        ----------
        plugin_name: str
            Name of the plugin to retrieve.

        Returns
        -------
        plugin: weakref.ProxyType
            A weak reference to the plugin requested

        Raises
        ------
        SpyderAPIError
            If the plugin name was not found in the registry.
        """
        if plugin_name in self.plugin_registry:
            plugin_instance = self.plugin_registry[plugin_name]
            return weakref.proxy(plugin_instance)
        else:
            raise SpyderAPIError(f'Plugin {plugin_name} was not found in '
                                 'the registry')

    def set_plugin_enabled(self, plugin_name: str):
        """
        Add a plugin name to the set of enabled plugins.

        Parameters
        ----------
        plugin_name: str
            Name of the plugin to add.
        """
        self.enabled_plugins |= {plugin_name}

    def is_plugin_enabled(self, plugin_name: str) -> bool:
        """
        Determine if a given plugin is enabled and is going to be
        loaded.

        Parameters
        ----------
        plugin_name: str
            Name of the plugin to query.

        Returns
        -------
        plugin_enabled: bool
            True if the plugin is enabled and False if not.
        """
        return plugin_name in self.enabled_plugins

    def __contains__(self, plugin_name: str) -> bool:
        """
        Determine if a plugin name is contained in the registry.

        Parameters
        ----------
        plugin_name: str
            Name of the plugin to seek.

        Returns
        -------
        is_contained: bool
            If True, the plugin name is contained on the registry, False
            otherwise.
        """
        return plugin_name in self.plugin_registry


PLUGIN_REGISTRY = SpyderPluginRegistry()
