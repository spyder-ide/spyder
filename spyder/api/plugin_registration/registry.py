# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""Global plugin registry."""

# Standard library imports
import logging
from typing import Dict, List, Union, Type, Any, Set, Optional, Tuple

# Third-party library imports
from qtpy.QtCore import QObject, Signal

# Local imports
from spyder import dependencies
from spyder.config.base import _, running_under_pytest
from spyder.config.manager import CONF
from spyder.api.config.mixins import SpyderConfigurationAccessor
from spyder.api.plugin_registration._confpage import PluginsConfigPage
from spyder.api.exceptions import SpyderAPIError
from spyder.api.plugins import (
    Plugins, SpyderPluginV2, SpyderDockablePlugin, SpyderPluginWidget,
    SpyderPlugin)
from spyder.utils.icon_manager import ima


# TODO: Remove SpyderPlugin and SpyderPluginWidget once the migration
# is complete.
Spyder5PluginClass = Union[SpyderPluginV2, SpyderDockablePlugin]
Spyder4PluginClass = Union[SpyderPlugin, SpyderPluginWidget]
SpyderPluginClass = Union[Spyder4PluginClass, Spyder5PluginClass]


ALL_PLUGINS = [getattr(Plugins, attr) for attr in dir(Plugins)
               if not attr.startswith('_') and attr != 'All']

logger = logging.getLogger(__name__)


class PreferencesAdapter(SpyderConfigurationAccessor):
    # Fake class constants used to register the configuration page
    CONF_WIDGET_CLASS = PluginsConfigPage
    NAME = 'plugin_registry'
    CONF_VERSION = None
    ADDITIONAL_CONF_OPTIONS = None
    ADDITIONAL_CONF_TABS = None
    CONF_SECTION = ""

    def apply_plugin_settings(self, _unused):
        pass

    def apply_conf(self, _unused):
        pass


class SpyderPluginRegistry(QObject, PreferencesAdapter):
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
    2. A plugin should not depend on other plugin to perform its
       initialization since it could cause deadlocks.
    """

    sig_plugin_ready = Signal(str, bool)
    """
    This signal is used to let the main window know that a plugin is ready.

    Parameters
    ----------
    plugin_name: str
        Name of the plugin that is available.
    omit_conf: bool
        True if the plugin configuration does not need to be written.
    """

    def __init__(self):
        super().__init__()
        PreferencesAdapter.__init__(self)

        # Reference to the main window
        self.main = None

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
        self.enabled_plugins = set({})  # type: set[str]

        # Set that stores the names of the internal plugins
        self.internal_plugins = set({})  # type: set[str]

        # Set that stores the names of the external plugins
        self.external_plugins = set({})  # type: set[str]

        # Dictionary that contains all the internal plugins (enabled or not)
        self.all_internal_plugins = {}  # type: Dict[str, Tuple[str, Type[SpyderPluginClass]]]

        # Dictionary that contains all the external plugins (enabled or not)
        self.all_external_plugins = {}  # type: Dict[str, Tuple[str, Type[SpyderPluginClass]]]

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
        self.plugin_dependencies[plugin] = plugin_dependencies

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
            PluginClass: Type[Spyder5PluginClass],
            external: bool) -> Spyder5PluginClass:
        """Instantiate and register a Spyder 5+ plugin."""
        required_plugins = list(set(PluginClass.REQUIRES))
        optional_plugins = list(set(PluginClass.OPTIONAL))
        plugin_name = PluginClass.NAME

        logger.debug(f'Registering plugin {plugin_name} - {PluginClass}')

        if PluginClass.CONF_FILE:
            CONF.register_plugin(PluginClass)

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
            lambda: self.notify_plugin_availability(
                plugin_name, omit_conf=PluginClass.CONF_FILE))

        # Initialize plugin instance
        plugin_instance.initialize()

        # Register plugins that are already available
        self._notify_plugin_dependencies(plugin_name)

        # Register the plugin name under the external or internal
        # plugin set
        if external:
            self.external_plugins |= {plugin_name}
        else:
            self.internal_plugins |= {plugin_name}

        if external:
            # These attributes come from spyder.app.find_plugins
            module = PluginClass._spyder_module_name
            package_name = PluginClass._spyder_package_name
            version = PluginClass._spyder_version
            description = plugin_instance.get_description()
            dependencies.add(module, package_name, description,
                                version, None, kind=dependencies.PLUGIN)

        return plugin_instance

    def _instantiate_spyder4_plugin(
            self, main_window: Any,
            PluginClass: Type[Spyder4PluginClass],
            external: bool,
            args: tuple, kwargs: dict) -> Spyder4PluginClass:
        """Instantiate and register a Spyder 4 plugin."""
        plugin_name = PluginClass.NAME

        # Create old plugin instance
        plugin_instance = PluginClass(main_window, *args, **kwargs)

        if hasattr(plugin_instance, 'COMPLETION_PROVIDER_NAME'):
            if Plugins.Completions in self:
                completions = self.get_plugin(Plugins.Completions)
                completions.register_completion_plugin(plugin_instance)
        else:
            plugin_instance.register_plugin()

        # Register plugin in the registry
        self.plugin_registry[plugin_name] = plugin_instance

        # Register the name of the plugin under the external or
        # internal plugin set
        if external:
            self.external_plugins |= {plugin_name}
        else:
            self.internal_plugins |= {plugin_name}

        # Since Spyder 5+ plugins are loaded before old ones, preferences
        # will be available at this point.
        preferences = self.get_plugin(Plugins.Preferences)
        preferences.register_plugin_preferences(plugin_instance)

        # Notify new-API plugins that depend on old ones
        self.notify_plugin_availability(plugin_name, False)

        return plugin_instance

    def _notify_plugin_dependencies(self, plugin_name: str):
        """Notify a plugin of its available dependencies."""
        plugin_instance = self.plugin_registry[plugin_name]
        plugin_dependencies = self.plugin_dependencies.get(plugin_name, {})
        required_plugins = plugin_dependencies.get('requires', [])
        optional_plugins = plugin_dependencies.get('optional', [])

        for plugin in required_plugins + optional_plugins:
            if plugin in self.plugin_registry:
                if self.plugin_availability.get(plugin, False):
                    logger.debug(f'Plugin {plugin} has already loaded')
                    plugin_instance._on_plugin_available(plugin)

    def _notify_plugin_teardown(self, plugin_name: str):
        """Notify dependents of a plugin that is going to be unavailable."""
        plugin_dependents = self.plugin_dependents.get(plugin_name, {})
        required_plugins = plugin_dependents.get('requires', [])
        optional_plugins = plugin_dependents.get('optional', [])

        for plugin in required_plugins + optional_plugins:
            if plugin in self.plugin_registry:
                if self.plugin_availability.get(plugin, False):
                    logger.debug(f'Notifying plugin {plugin} that '
                                 f'{plugin_name} is going to be turned off')
                    plugin_instance = self.plugin_registry[plugin]
                    plugin_instance._on_plugin_teardown(plugin_name)

    def _teardown_plugin(self, plugin_name: str):
        """Disconnect a plugin from its dependencies."""
        plugin_instance = self.plugin_registry[plugin_name]
        plugin_dependencies = self.plugin_dependencies.get(plugin_name, {})
        required_plugins = plugin_dependencies.get('requires', [])
        optional_plugins = plugin_dependencies.get('optional', [])

        for plugin in required_plugins + optional_plugins:
            if plugin in self.plugin_registry:
                if self.plugin_availability.get(plugin, False):
                    logger.debug(f'Disconnecting {plugin_name} from {plugin}')
                    plugin_instance._on_plugin_teardown(plugin)

    # -------------------------- PUBLIC API -----------------------------------
    def register_plugin(
            self, main_window: Any,
            PluginClass: Type[SpyderPluginClass],
            *args: tuple, external: bool = False,
            **kwargs: dict) -> SpyderPluginClass:
        """
        Register a plugin into the Spyder registry.

        Parameters
        ----------
        main_window: spyder.app.mainwindow.MainWindow
            Reference to Spyder's main window.
        PluginClass: type[SpyderPluginClass]
            The plugin class to register and create. It must be one of
            `spyder.app.registry.SpyderPluginClass`.
        *args: tuple
            Positional arguments used to initialize the plugin
            instance.
        external: bool
            If True, then the plugin is stored as a external plugin. Otherwise
            it will be marked as an internal plugin. Default: False
        **kwargs: dict
            Optional keyword arguments used to initialize the plugin instance.

        Returns
        -------
        plugin: SpyderPluginClass
            The instance of the registered plugin.

        Raises
        ------
        TypeError
            If the `PluginClass` does not inherit from any of
            `spyder.app.registry.SpyderPluginClass`

        Notes
        -----
        The optional `*args` and `**kwargs` will be removed once all
        plugins are migrated.
        """
        if not issubclass(PluginClass, (SpyderPluginV2, SpyderPlugin)):
            raise TypeError(f'{PluginClass} does not inherit from '
                            f'{SpyderPluginV2} nor {SpyderPlugin}')

        instance = None
        if issubclass(PluginClass, SpyderPluginV2):
            # Register a Spyder 5+ plugin
            instance = self._instantiate_spyder5_plugin(
                main_window, PluginClass, external)
        elif issubclass(PluginClass, SpyderPlugin):
            # Register a Spyder 4 plugin
            instance = self._instantiate_spyder4_plugin(
                main_window, PluginClass, external, args, kwargs)

        return instance

    def notify_plugin_availability(self, plugin_name: str,
                                   notify_main: bool = True,
                                   omit_conf: bool = False):
        """
        Notify dependent plugins of a given plugin of its availability.

        Parameters
        ----------
        plugin_name: str
            Name of the plugin that is available.
        notify_main: bool
            If True, then a signal is emitted to the main window to perform
            further registration steps.
        omit_conf: bool
            If True, then the main window is instructed to not write the
            plugin configuration into the Spyder configuration file.
        """
        logger.debug(f'Plugin {plugin_name} has finished loading, '
                     'sending notifications')

        # Set plugin availability to True
        self.plugin_availability[plugin_name] = True

        # Notify the main window that the plugin is ready
        if notify_main:
            self.sig_plugin_ready.emit(plugin_name, omit_conf)

        # Notify plugin dependents
        plugin_dependents = self.plugin_dependents.get(plugin_name, {})
        required_plugins = plugin_dependents.get('requires', [])
        optional_plugins = plugin_dependents.get('optional', [])

        for plugin in required_plugins + optional_plugins:
            if plugin in self.plugin_registry:
                plugin_instance = self.plugin_registry[plugin]
                plugin_instance._on_plugin_available(plugin_name)

        if plugin_name == Plugins.Preferences and not running_under_pytest():
            plugin_instance = self.plugin_registry[plugin_name]
            plugin_instance.register_plugin_preferences(self)

    def can_delete_plugin(self, plugin_name: str) -> bool:
        """
        Check if a plugin from the registry can be deleted by its name.

        Paremeters
        ----------
        plugin_name: str
            Name of the plugin to check for deletion.

        Returns
        -------
        plugin_deleted: bool
            True if the plugin can be deleted. False otherwise.
        """
        plugin_instance = self.plugin_registry[plugin_name]
        # Determine if plugin can be closed
        can_delete = True
        if isinstance(plugin_instance, SpyderPluginV2):
            can_delete = plugin_instance.can_close()
        elif isinstance(plugin_instance, SpyderPlugin):
            can_delete = plugin_instance.closing_plugin(True)

        return can_delete

    def dock_undocked_plugin(
            self, plugin_name: str, save_undocked: bool = False):
        """
        Dock plugin if undocked and save undocked state if requested

        Parameters
        ----------
        plugin_name: str
            Name of the plugin to check for deletion.
        save_undocked : bool, optional
            True if the undocked state needs to be saved. The default is False.

        Returns
        -------
        None.
        """
        plugin_instance = self.plugin_registry[plugin_name]

        if isinstance(plugin_instance, SpyderDockablePlugin):
            # Close undocked plugin if needed and save undocked state
            plugin_instance.close_window(save_undocked=save_undocked)
        elif isinstance(plugin_instance, SpyderPluginWidget):
            # Save if plugin was undocked to restore it the next time.
            if plugin_instance._undocked_window and save_undocked:
                plugin_instance.set_option(
                    'undocked_on_window_close', True)
            else:
                plugin_instance.set_option(
                    'undocked_on_window_close', False)

            # Close undocked plugins.
            plugin_instance._close_window()

    def delete_plugin(self, plugin_name: str, teardown: bool = True,
                      check_can_delete: bool = True) -> bool:
        """
        Remove and delete a plugin from the registry by its name.

        Paremeters
        ----------
        plugin_name: str
            Name of the plugin to delete.
        teardown: bool
            True if the teardown notification to other plugins should be sent
            when deleting the plugin, False otherwise.
        check_can_delete: bool
            True if the plugin should validate if it can be closed when this
            method is called, False otherwise.

        Returns
        -------
        plugin_deleted: bool
            True if the registry was able to teardown and remove the plugin.
            False otherwise.
        """
        logger.debug(f'Deleting plugin {plugin_name}')
        plugin_instance = self.plugin_registry[plugin_name]

        # Determine if plugin can be closed
        if check_can_delete:
            can_delete = self.can_delete_plugin(plugin_name)
            if not can_delete:
                return False

        if isinstance(plugin_instance, SpyderPluginV2):
            # Cleanly delete plugin widgets. This avoids segfautls with
            # PyQt 5.15
            if isinstance(plugin_instance, SpyderDockablePlugin):
                try:
                    plugin_instance.get_widget().close()
                    plugin_instance.get_widget().deleteLater()
                except RuntimeError:
                    pass
            else:
                container = plugin_instance.get_container()
                if container:
                    try:
                        container.close()
                        container.deleteLater()
                    except RuntimeError:
                        pass

            # Delete plugin
            try:
                plugin_instance.deleteLater()
            except RuntimeError:
                pass
            if teardown:
                # Disconnect plugin from other plugins
                self._teardown_plugin(plugin_name)

                # Disconnect depending plugins from the plugin to delete
                self._notify_plugin_teardown(plugin_name)

            # Perform plugin closure tasks
            try:
                plugin_instance.on_close(True)
            except RuntimeError:
                pass
        elif isinstance(plugin_instance, SpyderPlugin):
            try:
                plugin_instance.deleteLater()
            except RuntimeError:
                pass
            if teardown:
                # Disconnect depending plugins from the plugin to delete
                self._notify_plugin_teardown(plugin_name)

        # Delete plugin from the registry and auxiliary structures
        self.plugin_dependents.pop(plugin_name, None)
        self.plugin_dependencies.pop(plugin_name, None)
        if plugin_instance.CONF_FILE:
            # This must be done after on_close() so that plugins can modify
            # their (external) config therein.
            CONF.unregister_plugin(plugin_instance)

        for plugin in self.plugin_dependents:
            all_plugin_dependents = self.plugin_dependents[plugin]
            for key in {'requires', 'optional'}:
                plugin_dependents = all_plugin_dependents.get(key, [])
                if plugin_name in plugin_dependents:
                    plugin_dependents.remove(plugin_name)

        for plugin in self.plugin_dependencies:
            all_plugin_dependencies = self.plugin_dependencies[plugin]
            for key in {'requires', 'optional'}:
                plugin_dependencies = all_plugin_dependencies.get(key, [])
                if plugin_name in plugin_dependencies:
                    plugin_dependencies.remove(plugin_name)

        self.plugin_availability.pop(plugin_name)
        self.old_plugins -= {plugin_name}
        self.enabled_plugins -= {plugin_name}
        self.internal_plugins -= {plugin_name}
        self.external_plugins -= {plugin_name}

        # Remove the plugin from the registry
        self.plugin_registry.pop(plugin_name)

        return True

    def dock_all_undocked_plugins(self, save_undocked: bool = False):
        """
        Dock undocked plugins and save undocked state if required.

        Parameters
        ----------
        save_undocked : bool, optional
            True if the undocked state needs to be saved. The default is False.

        Returns
        -------
        None.

        """
        for plugin_name in (
                set(self.external_plugins) | set(self.internal_plugins)):
            self.dock_undocked_plugin(
                plugin_name, save_undocked=save_undocked)

    def can_delete_all_plugins(self,
                               excluding: Optional[Set[str]] = None) -> bool:
        """
        Determine if all plugins can be deleted except the ones to exclude.

        Parameters
        ----------
        excluding: Optional[Set[str]]
            A set that lists plugins (by name) that will not be deleted.

        Returns
        -------
        bool
            True if all plugins can be closed. False otherwise.
        """
        excluding = excluding or set({})
        can_close = True

        # Check external plugins
        for plugin_name in (
                set(self.external_plugins) | set(self.internal_plugins)):
            if plugin_name not in excluding:
                plugin_instance = self.plugin_registry[plugin_name]
                if isinstance(plugin_instance, SpyderPlugin):
                    can_close &= self.can_delete_plugin(plugin_name)
                    if not can_close:
                        break

        return can_close

    def delete_all_plugins(self, excluding: Optional[Set[str]] = None,
                           close_immediately: bool = False) -> bool:
        """
        Remove all plugins from the registry.

        The teardown mechanism will remove external plugins first and then
        internal ones, where the Spyder 4 plugins will be removed first and
        then the Spyder 5 ones.

        Parameters
        ----------
        excluding: Optional[Set[str]]
            A set that lists plugins (by name) that will not be deleted.
        close_immediately: bool
            If true, then the `can_close` status will be ignored.

        Returns
        -------
        all_deleted: bool
            True if all the plugins were closed and deleted. False otherwise.
        """
        excluding = excluding or set({})
        can_close = True

        # Check if all the plugins can be closed
        can_close = self.can_delete_all_plugins(excluding=excluding)

        if not can_close and not close_immediately:
            return False

        # Dock undocked plugins
        self.dock_all_undocked_plugins(save_undocked=True)

        # Delete Spyder 4 external plugins
        for plugin_name in set(self.external_plugins):
            if plugin_name not in excluding:
                plugin_instance = self.plugin_registry[plugin_name]
                if isinstance(plugin_instance, SpyderPlugin):
                    can_close &= self.delete_plugin(
                        plugin_name, teardown=False, check_can_delete=False)
                    if not can_close and not close_immediately:
                        break

        if not can_close:
            return False

        # Delete Spyder 4 internal plugins
        for plugin_name in set(self.internal_plugins):
            if plugin_name not in excluding:
                plugin_instance = self.plugin_registry[plugin_name]
                if isinstance(plugin_instance, SpyderPlugin):
                    can_close &= self.delete_plugin(
                        plugin_name, teardown=False, check_can_delete=False)
                    if not can_close and not close_immediately:
                        break

        if not can_close:
            return False

        # Delete Spyder 5+ external plugins
        for plugin_name in set(self.external_plugins):
            if plugin_name not in excluding:
                plugin_instance = self.plugin_registry[plugin_name]
                if isinstance(plugin_instance, SpyderPluginV2):
                    can_close &= self.delete_plugin(
                        plugin_name, teardown=False, check_can_delete=False)
                    if not can_close and not close_immediately:
                        break

        if not can_close and not close_immediately:
            return False

        # Delete Spyder 5 internal plugins
        for plugin_name in set(self.internal_plugins):
            if plugin_name not in excluding:
                plugin_instance = self.plugin_registry[plugin_name]
                if isinstance(plugin_instance, SpyderPluginV2):
                    can_close &= self.delete_plugin(
                        plugin_name, teardown=False, check_can_delete=False)
                    if not can_close and not close_immediately:
                        break

        return can_close

    def get_plugin(self, plugin_name: str) -> SpyderPluginClass:
        """
        Get a reference to a plugin instance by its name.

        Parameters
        ----------
        plugin_name: str
            Name of the plugin to retrieve.

        Returns
        -------
        plugin: SpyderPluginClass
            The instance of the requested plugin.

        Raises
        ------
        SpyderAPIError
            If the plugin name was not found in the registry.
        """
        if plugin_name in self.plugin_registry:
            plugin_instance = self.plugin_registry[plugin_name]
            return plugin_instance
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

    def is_plugin_available(self, plugin_name: str) -> bool:
        """
        Determine if a given plugin was loaded and is available.

        Parameters
        ----------
        plugin_name: str
            Name of the plugin to query.

        Returns
        -------
        plugin_available: bool
            True if the plugin is available and False if not.
        """
        return self.plugin_availability.get(plugin_name, False)

    def reset(self):
        """Reset and empty the plugin registry."""
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

        # Set that stores the names of the internal plugins
        self.internal_plugins = set({})

        # Set that stores the names of the external plugins
        self.external_plugins = set({})

        try:
            self.sig_plugin_ready.disconnect()
        except (TypeError, RuntimeError):
            # Omit failures if there are no slots connected
            pass

    def set_all_internal_plugins(
            self, all_plugins: Dict[str, Type[SpyderPluginClass]]):
        self.all_internal_plugins = all_plugins

    def set_all_external_plugins(
            self, all_plugins: Dict[str, Type[SpyderPluginClass]]):
        self.all_external_plugins = all_plugins

    def set_main(self, main):
        self.main = main

    def get_icon(self):
        return ima.icon('plugins')

    def get_name(self):
        return _('Plugins')

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

    def __iter__(self):
        return iter(self.plugin_registry)


PLUGIN_REGISTRY = SpyderPluginRegistry()
