# -----------------------------------------------------------------------------
# Copyright (c) 2021- Spyder Project Contributors
#
# Released under the terms of the MIT License
# (see LICENSE.txt in the project root directory for details)
# -----------------------------------------------------------------------------

"""Global registry for internal and external Spyder plugins."""

from __future__ import annotations

# Standard library imports
import logging
import sys
from typing import Any, Union, TYPE_CHECKING

if sys.version_info < (3, 10):
    from typing_extensions import TypeAlias
else:
    from typing import TypeAlias  # noqa: ICN003

# Third-party library imports
from qtpy.QtCore import QObject, Signal

# Local imports
from spyder import dependencies
from spyder.api.translations import _
from spyder.config.base import running_under_pytest
from spyder.config.manager import CONF
from spyder.api.config.mixins import SpyderConfigurationAccessor
from spyder.api.plugin_registration._confpage import PluginsConfigPage
from spyder.api.exceptions import SpyderAPIError
from spyder.api.plugins import Plugins, SpyderDockablePlugin, SpyderPluginV2
from spyder.utils.icon_manager import ima

if TYPE_CHECKING:
    from qtpy.QtGui import QIcon

    import spyder.app.mainwindow


SpyderPluginClass: TypeAlias = Union[SpyderPluginV2, SpyderDockablePlugin]
"""Type alias for the set of supported classes for Spyder plugin objects."""

ALL_PLUGINS: list[str] = [
    getattr(Plugins, attr)
    for attr in dir(Plugins)
    if not attr.startswith("_") and attr != "All"
]
"""List of all Spyder internal plugins."""

logger = logging.getLogger(__name__)


class PreferencesAdapter(SpyderConfigurationAccessor):
    """Class with constants for the plugin manager preferences page."""

    # Fake class constants used to register the configuration page
    CONF_WIDGET_CLASS = PluginsConfigPage
    """:meta private:"""
    NAME = "plugin_registry"
    CONF_VERSION = None
    ADDITIONAL_CONF_OPTIONS = None
    ADDITIONAL_CONF_TABS = None
    CONF_SECTION = ""
    """:meta private:"""

    def apply_plugin_settings(self, _unused):
        pass

    def apply_conf(self, _unused):
        pass


class SpyderPluginRegistry(QObject, PreferencesAdapter):
    """
    Global Spyder plugin registry.

    This class handles a plugin's initialization/teardown lifetime, including
    notifications when a plugin is available or about to be torn down.

    This registry alleviates the limitations of a topological sort-based
    plugin initialization by enabling plugins to have bidirectional
    dependencies instead of unidirectional ones.

    .. caution::

        A plugin should not depend on other plugin to perform its
        initialization, since this could cause deadlocks.

    .. note::

        This class should be instantiated as a singleton.
    """

    sig_plugin_ready: Signal = Signal(str, bool)
    """
    Signal used to let the main window know that a plugin is ready for use.

    Parameters
    ----------
    plugin_name: str
        Name of the plugin that has become available.
    omit_conf: bool
        ``True`` if the plugin configuration does not need to be written;
        ``False`` otherwise.
    """

    def __init__(self) -> None:
        """
        Create a global registry for internal and external Spyder plugins.

        Returns
        -------
        None
        """
        super().__init__()
        PreferencesAdapter.__init__(self)

        self.main: spyder.app.mainwindow.MainWindow | None = None
        """Reference to the Spyder main window."""

        self.plugin_dependents: dict[str, dict[str, list[str]]] = {}
        """
        Mapping of plugin names to the names of plugins depending on them.

        The second-level dictionary holds lists of dependencies for the plugin
        by category, under the keys ``"requires"`` and ``"optional"``.
        """

        self.plugin_dependencies: dict[str, dict[str, list[str]]] = {}
        """
        Mapping of plugin names to the names of plugins they depend on.

        The second-level dictionary holds lists of dependencies for the plugin
        by category, under the keys ``"requires"`` and ``"optional"``.
        """

        self.plugin_registry: dict[str, SpyderPluginClass] = {}
        """Mapping of plugin names to plugin objects."""

        self.plugin_availability: dict[str, bool] = {}
        """Mapping of plugin name to whether it is ready for use."""

        self.enabled_plugins: set[str] = set()
        """Set of the names of all enabled plugins."""

        self.internal_plugins: set[str] = set()
        """Set of the names of all internal plugins (part of Spyder itself)."""

        self.external_plugins: set[str] = set()
        """Set of the names of all external plugins (installed separately)."""

        self.all_internal_plugins: dict[
            str, tuple[str, type[SpyderPluginClass]]
        ] = {}
        """Mapping of internal plugins to their name and plugin class.

        Includes all internal plugins that are part of Spyder's source tree,
        enabled or not.
        """

        self.all_external_plugins: dict[
            str, tuple[str, type[SpyderPluginClass]]
        ] = {}
        """Mapping of external plugins to their name and plugin class.

        Includes all externals plugins installed separately from Spyder,
        enabled or not.
        """

        # This is used to allow disabling external plugins through Preferences
        self._external_plugins_conf_section = "external_plugins"

    # ------------------------- PRIVATE API -----------------------------------
    def _update_dependents(self, plugin: str, dependent_plugin: str, key: str):
        """Add `dependent_plugin` to the list of dependents of `plugin`."""
        plugin_dependents = self.plugin_dependents.get(plugin, {})
        plugin_strict_dependents = plugin_dependents.get(key, [])
        plugin_strict_dependents.append(dependent_plugin)
        plugin_dependents[key] = plugin_strict_dependents
        self.plugin_dependents[plugin] = plugin_dependents

    def _update_dependencies(
        self, plugin: str, required_plugin: str, key: str
    ):
        """Add `required_plugin` to the list of dependencies of `plugin`."""
        plugin_dependencies = self.plugin_dependencies.get(plugin, {})
        plugin_strict_dependencies = plugin_dependencies.get(key, [])
        plugin_strict_dependencies.append(required_plugin)
        plugin_dependencies[key] = plugin_strict_dependencies
        self.plugin_dependencies[plugin] = plugin_dependencies

    def _update_plugin_info(
        self,
        plugin_name: str,
        required_plugins: list[str],
        optional_plugins: list[str],
    ):
        """Update the dependencies and dependents of `plugin_name`."""
        for plugin in required_plugins:
            self._update_dependencies(plugin_name, plugin, "requires")
            self._update_dependents(plugin, plugin_name, "requires")

        for plugin in optional_plugins:
            self._update_dependencies(plugin_name, plugin, "optional")
            self._update_dependents(plugin, plugin_name, "optional")

    def _instantiate_spyder_plugin(
        self,
        main_window: Any,
        PluginClass: type[SpyderPluginClass],
        external: bool,
    ) -> SpyderPluginClass:
        """Instantiate and register a Spyder plugin."""
        required_plugins = list(set(PluginClass.REQUIRES))
        optional_plugins = list(set(PluginClass.OPTIONAL))
        plugin_name = PluginClass.NAME

        logger.debug(f"Registering plugin {plugin_name} - {PluginClass}")

        if PluginClass.CONF_FILE:
            CONF.register_plugin(PluginClass)

        for plugin in list(required_plugins):
            if plugin == Plugins.All:
                required_plugins = list(set(required_plugins + ALL_PLUGINS))

        for plugin in list(optional_plugins):
            if plugin == Plugins.All:
                optional_plugins = list(set(optional_plugins + ALL_PLUGINS))

        # Update plugin dependency information
        self._update_plugin_info(
            plugin_name, required_plugins, optional_plugins
        )

        # Create and store plugin instance
        plugin_instance = PluginClass(main_window, configuration=CONF)
        self.plugin_registry[plugin_name] = plugin_instance

        # Connect plugin availability signal to notification system
        plugin_instance.sig_plugin_ready.connect(
            lambda: self.notify_plugin_availability(
                plugin_name, omit_conf=PluginClass.CONF_FILE
            )
        )

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
            dependencies.add(
                module,
                package_name,
                description,
                version,
                None,
                kind=dependencies.PLUGIN,
            )

        return plugin_instance

    def _notify_plugin_dependencies(self, plugin_name: str):
        """Notify a plugin of its available dependencies."""
        plugin_instance = self.plugin_registry[plugin_name]
        plugin_dependencies = self.plugin_dependencies.get(plugin_name, {})
        required_plugins = plugin_dependencies.get("requires", [])
        optional_plugins = plugin_dependencies.get("optional", [])

        for plugin in required_plugins + optional_plugins:
            if plugin in self.plugin_registry:
                if self.plugin_availability.get(plugin, False):
                    logger.debug(f"Plugin {plugin} has already loaded")
                    plugin_instance._on_plugin_available(plugin)

    def _notify_plugin_teardown(self, plugin_name: str):
        """Notify dependents of a plugin that is going to be unavailable."""
        plugin_dependents = self.plugin_dependents.get(plugin_name, {})
        required_plugins = plugin_dependents.get("requires", [])
        optional_plugins = plugin_dependents.get("optional", [])

        for plugin in required_plugins + optional_plugins:
            if plugin in self.plugin_registry:
                if self.plugin_availability.get(plugin, False):
                    logger.debug(
                        f"Notifying plugin {plugin} that "
                        f"{plugin_name} is going to be turned off"
                    )
                    plugin_instance = self.plugin_registry[plugin]
                    plugin_instance._on_plugin_teardown(plugin_name)

    def _teardown_plugin(self, plugin_name: str):
        """Disconnect a plugin from its dependencies."""
        plugin_instance = self.plugin_registry[plugin_name]
        plugin_dependencies = self.plugin_dependencies.get(plugin_name, {})
        required_plugins = plugin_dependencies.get("requires", [])
        optional_plugins = plugin_dependencies.get("optional", [])

        for plugin in required_plugins + optional_plugins:
            if plugin in self.plugin_registry:
                if self.plugin_availability.get(plugin, False):
                    logger.debug(f"Disconnecting {plugin_name} from {plugin}")
                    plugin_instance._on_plugin_teardown(plugin)

    # -------------------------- PUBLIC API -----------------------------------
    def register_plugin(
        self,
        main_window: spyder.app.mainwindow.MainWindow,
        PluginClass: type[SpyderPluginClass],
        *args: Any,
        external: bool = False,
        **kwargs: Any,
    ) -> SpyderPluginClass:
        """
        Register a plugin into the Spyder plugin registry.

        Parameters
        ----------
        main_window: spyder.app.mainwindow.MainWindow
            Reference to Spyder's main window.
        PluginClass: type[SpyderPluginClass]
            The plugin class to register and create. It must be one of
            :data:`SpyderPluginClass`.
        *args: Any, optional
            Arbitrary positional arguments passed to the plugin instance's
            initializer.

            .. deprecated:: 6.2

                No longer needed following completion of the Spyder plugin
                API migration in Spyder 6.0. Passing ``*args`` will raise a
                :exc:`DeprecationWarning` in Spyder 6.2 and be removed in
                Spyder 7.0.
        external: bool, optional
            If ``True``, then the plugin is stored as an external plugin.
            Otherwise, it will be marked as an internal plugin (the default).
        **kwargs: Any, optional
            Arbitrary positional arguments passed to the plugin instance's
            initializer.

            .. deprecated:: 6.2

                No longer needed following completion of the Spyder plugin
                API migration in Spyder 6.0. Passing ``**kwargs`` will raise a
                :exc:`DeprecationWarning` in Spyder 6.2 and be removed in
                Spyder 7.0.

        Returns
        -------
        plugin: SpyderPluginClass
            The initialized instance of the registered plugin.

        Raises
        ------
        TypeError
            If the ``PluginClass`` does not inherit from any of
            :data:`spyder.app.registry.SpyderPluginClass`.
        """
        if not issubclass(PluginClass, SpyderPluginV2):
            raise TypeError(
                f"{PluginClass} does not inherit from SpyderPluginV2"
            )

        # Register a Spyder plugin
        instance = self._instantiate_spyder_plugin(
            main_window, PluginClass, external
        )

        return instance

    def notify_plugin_availability(
        self,
        plugin_name: str,
        notify_main: bool = True,
        omit_conf: bool = False,
    ) -> None:
        """
        Notify a plugin's dependents that the plugin is ready for use.

        Parameters
        ----------
        plugin_name: str
            Name of the plugin that has become ready for use.
        notify_main: bool, optional
            If ``True``, then a signal is emitted to the main window to perform
            further registration steps (the default). Otherwise, no signal is
            emitted.
        omit_conf: bool, optional
            If ``True``, then the main window is instructed to not write the
            plugin configuration into the Spyder configuration file.
            Otherwise, configuration will be written as normal (the default).

        Returns
        -------
        None
        """
        logger.debug(
            f"Plugin {plugin_name} has finished loading, sending notifications"
        )

        # Set plugin availability to True
        self.plugin_availability[plugin_name] = True

        # Notify the main window that the plugin is ready
        if notify_main:
            self.sig_plugin_ready.emit(plugin_name, omit_conf)

        # Notify plugin dependents
        plugin_dependents = self.plugin_dependents.get(plugin_name, {})
        required_plugins = plugin_dependents.get("requires", [])
        optional_plugins = plugin_dependents.get("optional", [])

        for plugin in required_plugins + optional_plugins:
            if plugin in self.plugin_registry:
                plugin_instance = self.plugin_registry[plugin]
                plugin_instance._on_plugin_available(plugin_name)

        if plugin_name == Plugins.Preferences and not running_under_pytest():
            plugin_instance = self.plugin_registry[plugin_name]
            plugin_instance.register_plugin_preferences(self)

    def can_delete_plugin(self, plugin_name: str) -> bool:
        """
        Check if a plugin with the given name can be deleted from the registry.

        Calls :meth:`spyder.api.plugins.SpyderPluginV2.can_close` to
        perform the check.

        Parameters
        ----------
        plugin_name: str
            Name of the plugin to check for deletion.

        Returns
        -------
        can_close: bool
            ``True`` if the plugin can be removed; ``False`` otherwise.
        """
        plugin_instance = self.plugin_registry[plugin_name]
        # Determine if plugin can be closed
        return plugin_instance.can_close()

    def dock_undocked_plugin(
        self, plugin_name: str, save_undocked: bool = False
    ) -> None:
        """
        Dock plugin if undocked and save undocked state if requested.

        Parameters
        ----------
        plugin_name: str
            Name of the plugin to undock.
        save_undocked : bool, optional
            ``True`` if the undocked state should be saved. If ``False``,
            the default, don't persist the undocked state.

        Returns
        -------
        None
        """
        plugin_instance = self.plugin_registry[plugin_name]

        if isinstance(plugin_instance, SpyderDockablePlugin):
            # Close undocked plugin if needed and save undocked state
            plugin_instance.close_window(save_undocked=save_undocked)

    def delete_plugin(
        self,
        plugin_name: str,
        teardown: bool = True,
        check_can_delete: bool = True,
    ) -> bool:
        """
        Remove and delete the plugin with the given name from the registry.

        Parameters
        ----------
        plugin_name: str
            Name of the plugin to delete.
        teardown: bool, optional
            ``True`` if the teardown notification to other plugins should be
            sent when deleting the plugin (the default), ``False`` otherwise.
        check_can_delete: bool, optional
            ``True`` if the plugin should first check if it can be deleted
            (using :meth:`can_delete_plugin`) before closing and removing
            itself from the registry (the default). If this check then fails,
            the plugin's removal is aborted and this method returns ``False``.
            Otherwise, if this parameter is ``False``, the plugin is deleted
            unconditionally without a check.

        Returns
        -------
        plugin_deleted: bool
            ``True`` if the registry was able to teardown and remove the
            plugin; ``False`` otherwise. Will always return ``True``
            if ``check_can_delete`` is ``False``.
        """
        logger.debug(f"Deleting plugin {plugin_name}")
        plugin_instance = self.plugin_registry[plugin_name]

        # Determine if plugin can be closed
        if check_can_delete:
            can_delete = self.can_delete_plugin(plugin_name)
            if not can_delete:
                return False

        if isinstance(plugin_instance, SpyderPluginV2):
            # Cleanly delete plugin widgets. This avoids segfaults with
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

        # Delete plugin from the registry and auxiliary structures
        self.plugin_dependents.pop(plugin_name, None)
        self.plugin_dependencies.pop(plugin_name, None)
        if plugin_instance.CONF_FILE:
            # This must be done after on_close() so that plugins can modify
            # their (external) config therein.
            CONF.unregister_plugin(plugin_instance)

        for plugin in self.plugin_dependents:
            all_plugin_dependents = self.plugin_dependents[plugin]
            for key in {"requires", "optional"}:
                plugin_dependents = all_plugin_dependents.get(key, [])
                if plugin_name in plugin_dependents:
                    plugin_dependents.remove(plugin_name)

        for plugin in self.plugin_dependencies:
            all_plugin_dependencies = self.plugin_dependencies[plugin]
            for key in {"requires", "optional"}:
                plugin_dependencies = all_plugin_dependencies.get(key, [])
                if plugin_name in plugin_dependencies:
                    plugin_dependencies.remove(plugin_name)

        self.plugin_availability.pop(plugin_name)
        self.enabled_plugins -= {plugin_name}
        self.internal_plugins -= {plugin_name}
        self.external_plugins -= {plugin_name}

        # Remove the plugin from the registry
        self.plugin_registry.pop(plugin_name)

        return True

    def dock_all_undocked_plugins(self, save_undocked: bool = False) -> None:
        """
        Dock undocked plugins and save the undocked state if requested.

        Parameters
        ----------
        save_undocked: bool, optional
            ``True`` if the undocked state should be saved. If ``False``,
            the default, don't persist the undocked state.

        Returns
        -------
        None
        """
        for plugin_name in set(self.external_plugins) | set(
            self.internal_plugins
        ):
            self.dock_undocked_plugin(plugin_name, save_undocked=save_undocked)

    def can_delete_all_plugins(
        self,
        excluding: set[str] | None = None,
    ) -> bool:
        """
        Determine if all plugins can be deleted (except any specified).

        Calls :meth:`spyder.api.plugins.SpyderPluginV2.can_close` to
        perform the check.

        Parameters
        ----------
        excluding: set[str] | None, optional
            A set that lists plugins (by name) that will not be checked for
            deletion. If ``None`` (the default) or an empty set, no plugins
            are excluded from the check.

        Returns
        -------
        bool
            ``True`` if all plugins can be closed. ``False`` otherwise.
        """
        excluding = excluding or set({})
        can_close = True

        # Check external plugins
        for plugin_name in set(self.external_plugins) | set(
            self.internal_plugins
        ):
            if plugin_name not in excluding:
                can_close &= self.can_delete_plugin(plugin_name)
                if not can_close:
                    break

        return can_close

    def delete_all_plugins(
        self,
        excluding: set[str] | None = None,
        close_immediately: bool = False,
    ) -> bool:
        """
        Remove all plugins from the registry.

        The teardown mechanism will remove external plugins then internal ones.

        Parameters
        ----------
        excluding: set[str] | None, optional
            A set that lists plugins (by name) that will not be deleted.
            If ``None`` (the default) or an empty set, no plugins
            are excluded from being deleted.
        close_immediately: bool, optional
            If ``True``, then the
            :meth:`~spyder.api.plugins.SpyderPluginV2.can_close` status
            will be ignored, and all plugins will be closed unconditionally.
            If ``False`` (the default), Spyder will not close any plugins
            if they report they cannot be closed, i.e. if
            :meth:`can_delete_all_plugins` returns ``False``.

        Returns
        -------
        all_deleted: bool
            ``True`` if all the plugins were deleted. ``False`` otherwise.
        """
        excluding = excluding or set({})

        # Check if all the plugins can be closed
        can_close = self.can_delete_all_plugins(excluding=excluding)

        # Delete external plugins first, then internal plugins
        for plugins in [self.external_plugins, self.internal_plugins]:
            if not can_close and not close_immediately:
                return False

            # Delete Spyder plugins
            for plugin_name in set(plugins):
                if plugin_name not in excluding:
                    plugin_instance = self.plugin_registry[plugin_name]
                    if isinstance(plugin_instance, SpyderPluginV2):
                        can_close &= self.delete_plugin(
                            plugin_name, teardown=False, check_can_delete=False
                        )
                        if not can_close and not close_immediately:
                            break

        return can_close

    def get_plugin(self, plugin_name: str) -> SpyderPluginClass:
        """
        Get a reference to a plugin instance by its name.

        Parameters
        ----------
        plugin_name: str
            Name of the plugin to retrieve the plugin object of.

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
            raise SpyderAPIError(
                f"Plugin {plugin_name} was not found in the registry"
            )

    def set_plugin_enabled(self, plugin_name: str) -> None:
        """
        Add a plugin by name to the set of enabled plugins.

        Parameters
        ----------
        plugin_name: str
            Name of the plugin to add.

        Returns
        -------
        None
        """
        self.enabled_plugins |= {plugin_name}

    def is_plugin_enabled(self, plugin_name: str) -> bool:
        """
        Determine if a given plugin is enabled and is going to be loaded.

        Parameters
        ----------
        plugin_name: str
            Name of the plugin to check.

        Returns
        -------
        plugin_enabled: bool
            ``True`` if the plugin is enabled and ``False`` if not.
        """
        return plugin_name in self.enabled_plugins

    def is_plugin_available(self, plugin_name: str) -> bool:
        """
        Determine if a given plugin is loaded and ready for use.

        Parameters
        ----------
        plugin_name: str
            Name of the plugin to check.

        Returns
        -------
        plugin_available: bool
            ``True`` if the plugin is available and ``False`` if not.
        """
        return self.plugin_availability.get(plugin_name, False)

    def reset(self) -> None:
        """
        Reset and empty the plugin registry.

        Returns
        -------
        None
        """
        self.plugin_dependents = {}
        self.plugin_dependencies = {}

        self.plugin_registry = {}
        self.plugin_availability = {}

        self.enabled_plugins = set()
        self.internal_plugins = set()
        self.external_plugins = set()

        try:
            self.sig_plugin_ready.disconnect()
        except (TypeError, RuntimeError):
            # Omit failures if there are no slots connected
            pass

        dependencies.DEPENDENCIES = []

    def set_all_internal_plugins(
        self, all_plugins: dict[str, tuple[str, type[SpyderPluginClass]]]
    ) -> None:
        """
        Set the :attr:`all_internal_plugins` attribute to the given plugins.

        .. deprecated:: 6.2

            Will raise a :exc:`DeprecationWarning` in Spyder 6.2 and be
            removed in Spyder 7.0. Set the :attr:`all_internal_plugins`
            attribute directly instead.

        Parameters
        ----------
        all_plugins : dict[str, tuple[str, type[SpyderPluginClass]]]
            Mapping of plugin name to plugin class to set the attribute to.

        Returns
        -------
        None
        """
        self.all_internal_plugins = all_plugins

    def set_all_external_plugins(
        self, all_plugins: dict[str, tuple[str, type[SpyderPluginClass]]]
    ) -> None:
        """
        Set the :attr:`all_external_plugins` attribute to the given plugins.

        .. deprecated:: 6.2

            Will raise a :exc:`DeprecationWarning` in Spyder 6.2 and be
            removed in Spyder 7.0. Set the :attr:`all_external_plugins`
            attribute directly instead.

        Parameters
        ----------
        all_plugins : dict[str, tuple[str, type[SpyderPluginClass]]]
            Mapping of plugin name to plugin class to set the attribute to.

        Returns
        -------
        None
        """
        self.all_external_plugins = all_plugins

    def set_main(self, main: spyder.app.mainwindow.MainWindow) -> None:
        """
        Set the reference to the Spyder main window for the plugin registry.

        .. deprecated:: 6.2

            Will raise a :exc:`DeprecationWarning` in Spyder 6.2 and be removed
            in Spyder 7.0. Set the :attr:`main` attribute directly instead.

        Parameters
        ----------
        main : spyder.app.mainwindow.MainWindow
            The Spyder main window instance to set the reference to.

        Returns
        -------
        None
        """
        self.main = main

    def get_icon(self) -> QIcon:
        """Icon of the plugin registry, for use in the Spyder interface."""
        return ima.icon("plugins")

    def get_name(self) -> str:
        """Name of the plugin registry, translated to the locale language."""
        return _("Plugins")

    def __contains__(self, plugin_name: str) -> bool:
        """
        Determine if a plugin with a given name is contained in the registry.

        Parameters
        ----------
        plugin_name: str
            Name of the plugin to check.

        Returns
        -------
        is_contained: bool
            If ``True``, `plugin_name` is contained in the registry;
            ``False`` otherwise.
        """
        return plugin_name in self.plugin_registry

    def __iter__(self):
        return iter(self.plugin_registry)


PLUGIN_REGISTRY: SpyderPluginRegistry = SpyderPluginRegistry()
"""The global Spyder plugin registry instance."""
