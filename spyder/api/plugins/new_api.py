# -----------------------------------------------------------------------------
# Copyright (c) 2021- Spyder Project Contributors
#
# Released under the terms of the MIT License
# (see LICENSE.txt in the project root directory for details)
# -----------------------------------------------------------------------------

"""
The current API for Spyder plugins, originally introduced in Spyder 5.

All Spyder plugins must inherit from the classes present in this file.

.. deprecated:: 6.2

    This module will be renamed to the private :mod:`!_api` in Spyder 6.2,
    while the current public name will become an alias raising a
    :exc:`DeprecationWarning` on import and be removed in 7.0.

    Use the canonical location, the top-level :mod:`spyder.api.plugins` instead
    which already exports all the public objects of this module.

    For example, ``import spyder.api.plugins`` instead of
    ``import spyder.api.plugins.new_api``, or
    ``from spyder.api.plugins import SpyderDockablePlugin`` instead of
    ``from spyder.api.plugins.new_api import SpyderDockablePlugin``.
"""

from __future__ import annotations

# Standard library imports
import inspect
import logging
import os
import os.path as osp
import sys
from typing import TYPE_CHECKING

# Third party imports
from qtpy.QtCore import QObject, Qt, Signal, Slot
from qtpy.QtGui import QCursor, QFont, QIcon
from qtpy.QtWidgets import QApplication, QWidget

# Local imports
from spyder.api.config.mixins import BasicTypes, SpyderConfigurationObserver
from spyder.api.exceptions import SpyderAPIError
from spyder.api.fonts import SpyderFontType
from spyder.api.plugin_registration.mixins import SpyderPluginObserver
from spyder.api.widgets.main_widget import PluginMainWidget
from spyder.api.widgets.mixins import SpyderActionMixin, SpyderWidgetMixin
from spyder.app.cli_options import get_options
from spyder.config.gui import get_color_scheme, get_font
from spyder.config.user import NoDefault
from spyder.utils.icon_manager import ima
from spyder.utils.image_path_manager import IMAGE_PATH_MANAGER

# Package imports
from spyder.api.plugins.enum import Plugins

if TYPE_CHECKING:
    import argparse

    import spyder.app.mainwindow
    import spyder.config.manager
    import spyder.config.types
    import spyder.config.user
    import spyder.plugins.layout.api
    import spyder.utils.qthelpers
    import spyder.widgets.dock
    from spyder.api.preferences import PluginConfigPage, SpyderPreferencesTab
    from spyder.api.widgets.main_container import PluginMainContainer
    from spyder.api.widgets.menus import PluginMainWidgetOptionsMenu


# Logging
logger = logging.getLogger(__name__)


class SpyderPluginV2(
    QObject,
    SpyderActionMixin,
    SpyderConfigurationObserver,
    SpyderPluginObserver,
):
    """
    Base class for all Spyder plugins.

    Use this class directly for plugins that extend functionality without a
    dockable widget. To create a plugin that adds a new pane to the interface,
    use :class:`SpyderDockablePlugin`.
    """

    # --- API: Mandatory attributes ------------------------------------------
    # ------------------------------------------------------------------------

    NAME: str = None  # type: ignore # Must always be set for plugin subclasses
    """
    Name of the plugin that will be used to refer to it.

    This name must be unique and will only be loaded once.
    """

    # --- API: Optional attributes ------------------------------------------
    # -----------------------------------------------------------------------

    REQUIRES: list[str] = []
    """
    List of names of required dependencies for this plugin.

    .. note::

        Plugin names are defined in the :class:`~spyder.api.plugins.Plugins`
        pseudo-enum class.

    Examples
    --------

    .. code-block:: python

        REQUIRES = [Plugins.Plots, Plugins.IPythonConsole, ...]
    """

    OPTIONAL: list[str] = []
    """
    List of names of optional dependencies for this plugin.

    Optional dependencies are useful for when a plugin can offer specific
    features by connecting to another plugin, but does not depend on the
    other plugin for its core functionality. For example, the :guilabel:`Help`
    plugin might render information from the :guilabel:`Editor`,
    :guilabel:`IPython Console` or another source, but it does not depend on
    either of those plugins to work.

    .. note::

        Plugin names are defined in the :class:`~spyder.api.plugins.Plugins`
        pseudo-enum class.

    Examples
    --------

    .. code-block:: python

        OPTIONAL = [Plugins.Plots, Plugins.IPythonConsole, ...]
    """

    CONTAINER_CLASS: type[PluginMainContainer] | None = None
    """
    Container class object to instantiate for the plugin.

    This must subclass a
    :class:`~spyder.api.widgets.main_container.PluginMainContainer` for
    non-dockable plugins that create a widget, like a status bar widget,
    a toolbar, a menu, etc.

    For non-dockable plugins that do not define widgets of any kind,
    for example a plugin that only exposes a configuration page,
    this can be ``None``,
    """

    CONF_SECTION: str | None = None
    """
    Name of the Spyder configuration section for the plugin's data.

    Used to record the plugin's permanent data in Spyder config system
    (i.e. in :file:`spyder.ini`).
    """

    CONF_FILE: bool = True
    """
    Whether to use a separate configuration file for the plugin.

    Should always be set to ``True`` for external plugins.

    If ``True`` (the default), use a separate configuration file.
    If ``False``, use the main Spyder config file.
    """

    CONF_DEFAULTS: (
        list[
            tuple[
                str,
                dict[
                    spyder.config.types.ConfigurationKey,
                    BasicTypes | spyder.config.user.NoDefault,
                ],
            ]
        ]
        | None
    ) = None
    """
    Define configuration defaults if using a separate file.

    List of tuples, with the first item in the tuple being the section
    name and the second item being the default options dictionary.

    Examples
    --------

    .. code-block:: python

        CONF_DEFAULTS = [
            (
                "section-name",
                {
                    "option-1": "some-value",
                    "option-2": True,
                },
            ),
            (
                "another-section-name",
                {
                    "option-3": "some-other-value",
                    "option-4": [1, 2, 3],
                },
            ),
        ]
    """

    CONF_VERSION: str | None = None
    """
    Define the configuration version if using a separate file.

    * If you want to *change* the default value of a current option, you need
      to do a MINOR update in config version, e.g. from ``3.0.0`` to ``3.1.0``.
    * If you want to *remove* options that are no longer needed or if you
      want to *rename* options, then you need to do a MAJOR update in
      version, e.g. from ``3.0.0`` to ``4.0.0``.
    * You don't need to touch this value if you're just adding a new option.
    """

    CONF_WIDGET_CLASS: type[PluginConfigPage] | None = None
    """
    Widget to be used as this plugin's entry in Spyder Preferences dialog.

    If ``None``, the default, the plugin will not have a configuration
    page in Spyder's :guilabel:`Preferences`.
    """

    ADDITIONAL_CONF_OPTIONS: (
        dict[
            str,
            dict[
                spyder.config.types.ConfigurationKey,
                BasicTypes | spyder.config.user.NoDefault,
            ],
        ]
        | None
    ) = None
    """
    Configuration options added by this plugin for other plugins.

    Examples
    --------

    .. code-block:: python

        ADDITIONAL_CONF_OPTIONS = {
            "section": {
                "option_1": True,
                "option_2": "default_value",
            },
        }
    """

    ADDITIONAL_CONF_TABS: (
        dict[str, list[type[SpyderPreferencesTab]]] | None
    ) = None
    """
    Define additional tabs of options for other plugins' configuration pages.

    All configuration tabs should inherit from
    :class:`~spyder.api.preferences.SpyderPreferencesTab`.

    Examples
    --------

    .. code-block:: python

        ADDITIONAL_CONF_TABS = {"plugin_name": [MyPluginsSpyderPrefsTab]}
    """

    CUSTOM_LAYOUTS: list[
        type[spyder.plugins.layout.api.BaseGridLayoutType]
    ] = []
    """
    Define custom layout classes that the plugin wants to be registered.

    The custom classes should extend from
    :class:`spyder.plugins.layout.api.BaseGridLayoutType`.
    """

    IMG_PATH: str | None = None
    """
    Path for images relative to the plugin path.

    A Python package can include one or several Spyder plugins. If the latter,
    the package may be using images from a directory outside that of the
    plugin itself.
    """

    MONOSPACE_FONT_SIZE_DELTA: int = 0
    """
    The monospace (code) font size delta relative to Spyder default, in points.
    """

    INTERFACE_FONT_SIZE_DELTA: int = 0
    """
    The interface (UI) font size delta relative to Spyder default, in points.
    """

    CONTEXT_NAME: str | None = None
    """
    The name under which to store actions, toolbars, toolbuttons and menus.
    """

    CAN_BE_DISABLED: bool = True
    """
    Define if a plugin can be disabled in the Spyder :guilabel:`Preferences`.

    If ``False``, the plugin is considered "core" and cannot be disabled.
    ``True`` by default, meaning the plugin can be disabled.
    """

    REQUIRE_WEB_WIDGETS: bool = False
    """
    Declare whether the plugin needs to use Qt web widgets (QtWebEngine).

    Qt Web Widgets is a heavy dependency for many packagers, e.g. Conda-Forge.
    We thus ask plugins to declare whether or not they need
    web widgets to make it easier to distribute Spyder without them.

    See `Spyder issue #22196 <https://github.com/spyder-ide/spyder/pull/22196#issuecomment-2189377043>`__
    for more information.
    """

    # --- API: Signals -------------------------------------------------------
    # ------------------------------------------------------------------------
    # Signals here are automatically connected by the Spyder main window and
    # connected to the the respective global actions defined on it.
    sig_free_memory_requested: Signal = Signal()
    """
    Request the main application garbage collect deleted objects.
    """

    sig_plugin_ready: Signal = Signal()
    """
    Emitted once the plugin is initialized.
    """

    sig_quit_requested: Signal = Signal()
    """
    Request that the main Spyder application quit.
    """

    sig_restart_requested: Signal = Signal()
    """
    Request that the main Spyder application perform a restart.
    """

    sig_status_message_requested: Signal = Signal(str, int)
    """
    Request that the main application display a status bar message.

    Parameters
    ----------
    message: str
        The message to display.
    timeout: int
        The timeout before the message disappears, in milliseconds.
    """

    sig_redirect_stdio_requested: Signal = Signal(bool)
    """
    Request the main app redirect standard out/error within file pickers.
    
    This will redirect :data:`~sys.stdin`, :data:`~sys.stdout`, and
    :data:`~sys.stderr` when using :guilabel:`Open`, :guilabel:`Save`,
    and :guilabel:`Browse` dialogs within a plugin's widgets.

    Parameters
    ----------
    enable: bool
        Enable (``True``) or disable (``False``) standard input/output
        redirection.
    """

    sig_exception_occurred: Signal = Signal(dict)
    """
    Report an exception from a plugin.

    Parameters
    ----------
    error_data: dict[str, str | bool]
        The dictionary containing error data. The expected keys are:

        .. code-block:: python

            error_data = {
                "text": str,
                "is_traceback": bool,
                "repo": str,
                "title": str,
                "label": str,
                "steps": str,
            }

        The ``is_traceback`` key indicates if ``text`` contains plain text or a
        Python error traceback.

        The ``title`` and ``repo`` keys indicate how the error data should
        customize the report dialog and GitHub error submission.

        The ``label`` and ``steps`` keys allow customizing the content of the
        error dialog.
    """

    sig_mainwindow_resized: Signal = Signal("QResizeEvent")
    """
    Emitted when the main window is resized.

    Used by plugins to track main window size changes.

    Parameters
    ----------
    resize_event: QResizeEvent
        The event triggered on main window resize.
    """

    sig_mainwindow_moved: Signal = Signal("QMoveEvent")
    """
    Emitted when the main window is moved.

    Used by plugins to track main window position changes.

    Parameters
    ----------
    move_event: QMoveEvent
        The event triggered on main window move.
    """

    sig_unmaximize_plugin_requested: Signal = Signal((), (object,))
    """
    Request the main window unmaximize the currently maximized plugin, if any.

    Parameters
    ----------
    plugin_instance: SpyderDockablePlugin
        Unmaximize current plugin only if it is not ``plugin_instance``.
    """

    sig_mainwindow_state_changed: Signal = Signal(object)
    """
    Emitted when the main window state has changed (e.g. maximized/minimized).

    Parameters
    ----------
    window_state: Qt.WindowStates
        The new main window state.
    """

    sig_focused_plugin_changed: Signal = Signal(object)
    """
    Emitted when the plugin with keyboard focus changes.

    Parameters
    ----------
    plugin: SpyderDockablePlugin | None
        The plugin that currently has keyboard focus, or ``None`` if no
        dockable plugin has focus.
    """

    # ---- Private attributes
    # -------------------------------------------------------------------------

    _CONF_NAME_MAP = None
    """
    Define config name map for plugin to split config among several files.

    See :mod:`spyder.config.main`.
    """

    # ---- Private methods
    # -------------------------------------------------------------------------

    def __init__(
        self,
        parent: spyder.app.mainwindow.MainWindow,
        configuration: (
            spyder.config.manager.ConfigurationManager | None
        ) = None,
    ):
        """
        Initialize the plugin object (called automatically by Spyder).

        .. important::

            Plugins are initialized automatically by Spyder, so they shouldn't
            call or override this method directly.

        Parameters
        ----------
        parent : spyder.app.mainwindow.MainWindow
            Parent Spyder window of this plugin.
        configuration : spyder.config.manager.ConfigurationManager
            The Spyder configuration manager object for the plugin to access.

        Returns
        -------
        None
        """
        super().__init__(parent)

        # This is required since the MRO of this class does not call
        # SpyderPluginObserver and SpyderConfigurationObserver when using
        # super(), see https://fuhm.net/super-harmful/
        SpyderPluginObserver.__init__(self)
        SpyderConfigurationObserver.__init__(self)

        self._main = parent
        self._conf = configuration
        self._plugin_path = os.path.dirname(inspect.getfile(self.__class__))

        self._widget: PluginMainWidget | PluginMainContainer | None = None
        self._container: PluginMainWidget | PluginMainContainer | None = None

        self.PLUGIN_NAME: str = self.NAME
        """
        Plugin name in the action, toolbar, toolbutton & menu registries.

        Usually the same as :attr:`NAME`, but may be different from
        :attr:`CONTEXT_NAME`.
        """

        self.is_compatible: bool | None = None
        """Whether the plugin has passed Spyder's compatibility checks.

        ``True`` if it has, ``False`` if it hasn't, and ``None`` if the checks
        haven't been run yet.
        """

        self.is_registered: bool | None = None
        """Whether the plugin is enabled and registered with Spyder.

        ``True`` if it has been registered, ``False`` if it has been
        unregistered, and ``None`` if the plugin hasn't been set up yet.
        """

        if self.CONTAINER_CLASS is not None:
            self._container = container = self.CONTAINER_CLASS(
                name=self.NAME, plugin=self, parent=parent
            )

            if hasattr(container, "_setup"):
                container._setup()

            if isinstance(container, SpyderWidgetMixin):
                container.setup()
                container.update_actions()

            # Default signals to connect in main container or main widget.
            container.sig_free_memory_requested.connect(
                self.sig_free_memory_requested
            )
            container.sig_quit_requested.connect(self.sig_quit_requested)
            container.sig_restart_requested.connect(self.sig_restart_requested)
            container.sig_redirect_stdio_requested.connect(
                self.sig_redirect_stdio_requested
            )
            container.sig_exception_occurred.connect(
                self.sig_exception_occurred
            )
            container.sig_unmaximize_plugin_requested.connect(
                self.sig_unmaximize_plugin_requested
            )

            self.after_container_creation()

        # Load the custom images of the plugin
        if self.IMG_PATH:
            plugin_path = osp.join(self.get_path(), self.IMG_PATH)
            IMAGE_PATH_MANAGER.add_image_path(plugin_path)

    def _register(self, omit_conf: bool = False) -> None:
        """
        Setup and register the plugin and connect it to other plugins.
        """
        # Checks
        # --------------------------------------------------------------------
        if self.NAME is None:
            raise SpyderAPIError("A Spyder Plugin must define a `NAME`!")

        # Setup configuration
        # --------------------------------------------------------------------
        if self._conf is not None and not omit_conf:
            self._conf.register_plugin(self)

        # Signals
        # --------------------------------------------------------------------
        self.is_registered = True

        self.update_font()

    def _unregister(self) -> None:
        """
        Disconnect signals & clean up plugin to stop it while Spyder's running.
        """

        if self._conf is not None:
            self._conf.unregister_plugin(self)

        self._container = None
        self.is_compatible = None
        self.is_registered = False

    # ---- Convinience attributes as properties
    # -------------------------------------------------------------------------
    @property
    def main(self) -> spyder.app.mainwindow.MainWindow:
        """Spyder main window to which this plugin belongs; i.e. its parent."""
        return self._main

    @main.setter
    def main(self, value: spyder.app.mainwindow.MainWindow) -> None:
        """Spyder main window to which this plugin belongs; i.e. its parent."""
        self._main = value

    # ---- API: available methods
    # -------------------------------------------------------------------------
    def get_path(self) -> str:
        """
        Return the path on disk to the plugin's root module directory.

        Returns
        -------
        str
            The path to the directory containing the module with the plugin
            class (:class:`SpyderPluginV2` or :class:`SpyderDockablePlugin`).
        """
        return self._plugin_path

    def get_container(self) -> PluginMainWidget | PluginMainContainer | None:
        """
        Return the plugin's main container object.

        Returns
        -------
        PluginMainContainer | None
            The plugin's main container object (i.e. an instance of
            :attr:`CONTAINER_CLASS`), or ``None`` if it doesn't have one set
            (e.g. for simple plugins that don't define any widgets).
        """
        return self._container

    def get_configuration(
        self,
    ) -> spyder.config.manager.ConfigurationManager | None:
        """
        Return the Spyder configuration object.

        Returns
        -------
        spyder.config.manager.ConfigurationManager
            The Spyder configuration manager object.
        """
        return self._conf

    def get_main(self) -> spyder.app.mainwindow.MainWindow:
        """
        Return the Spyder main window.

        Returns
        -------
        spyder.app.mainwindow.MainWindow
            The Spyder main window.
        """
        return self._main

    def get_plugin(self, plugin_name, error=True) -> SpyderPluginV2 | None:
        """
        Get a plugin instance object by its name.

        Parameters
        ----------
        plugin_name: str
            Name of the plugin from which its instance will be returned.
        error: bool, optional
            If ``True`` (the default), raise an error if the plugin instance
            with the given ``plugin_name`` cannot be found, and the plugin
            is a required dependency of this one (listed in :attr`REQUIRES`).
            If ``False``, runtime errors finding ``plugin_name`` pass silently
            (unless ``plugin_name`` is not listed in :attr:`REQUIRES` or
            :attr:`OPTIONAL`, which raises an error unconditionally).

        Returns
        -------
        SpyderPluginV2 | None
            The plugin object with name ``plugin_name``, or ``None`` if it
            cannot be found and is either an optional dependency of this plugin
            (listed under :attr:`OPTIONAL`), or ``error`` is ``False``.

        Raises
        ------
        SpyderAPIError
            If ``plugin_name`` is not listed under either the :attr:`REQUIRES`
            or :attr:`OPTIONAL` attributes of this plugin, or ``plugin_name``
            is not found (if a required dependency and ``error`` is ``True``).
        """
        # Ensure that this plugin has the plugin corresponding to
        # `plugin_name` listed as required or optional.
        requires = set(self.REQUIRES or [])
        optional = set(self.OPTIONAL or [])
        full_set = requires | optional

        if plugin_name in full_set or Plugins.All in full_set:
            try:
                return self._main.get_plugin(plugin_name, error=error)
            except SpyderAPIError as e:
                if plugin_name in optional:
                    return None
                else:
                    raise e
        else:
            raise SpyderAPIError(
                'Plugin "{}" not part of REQUIRES or '
                "OPTIONAL requirements!".format(plugin_name)
            )

    def is_plugin_enabled(self, plugin_name: str) -> bool:
        """
        Determine if a given plugin is going to be loaded.

        Parameters
        ----------
        plugin_name : str
            The name of the plugin to check.

        Returns
        -------
        bool
            ``True`` if ``plugin_name`` will be loaded, else ``False``.
        """
        return self._main.is_plugin_enabled(plugin_name)

    def is_plugin_available(self, plugin_name: str) -> bool:
        """
        Determine if a given plugin is loaded and ready.

        Parameters
        ----------
        plugin_name : str
            The name of the plugin to check.

        Returns
        -------
        bool
            ``True`` if ``plugin_name`` is loaded and ready, else ``False``.
        """
        return self._main.is_plugin_available(plugin_name)

    def get_dockable_plugins(self) -> list[SpyderDockablePlugin]:
        """
        Get a list of dockable plugin instances that this plugin depends on.

        Only required plugins (listed under :attr:`REQUIRES`) that extend
        :class:`SpyderDockablePlugin` are returned.

        Returns
        -------
        list[SpyderDockablePlugin]
            List of dockable plugin object instances (those with graphical
            panes in the UI) that this plugin requires as dependencies.
        """
        requires = set(self.REQUIRES or [])
        dockable_plugins_required = []
        for name, plugin_instance in self._main.get_dockable_plugins():
            if (name in requires or Plugins.All in requires) and isinstance(
                plugin_instance, SpyderDockablePlugin
            ):
                dockable_plugins_required.append(plugin_instance)
        return dockable_plugins_required

    def get_conf(
        self,
        option: spyder.config.types.ConfigurationKey,
        default: spyder.config.user.NoDefault | BasicTypes = NoDefault,
        section: str | None = None,
        secure: bool = False,
    ) -> BasicTypes | None:
        """
        Retrieve an option's value from the Spyder configuration system.

        Parameters
        ----------
        option: spyder.config.types.ConfigurationKey
            Name/tuple path of the configuration option value to get.
        default: spyder.api.config.mixins.BasicTypes | spyder.config.user.NoDefault, optional
            Fallback value to return if the option is not found on the
            configuration system. No default value if not passed.
        section: str | None, optional
            Name of the configuration section to use, e.g. ``"shortcuts"``.
            If ``None``, the default, then the value of :attr:`CONF_SECTION`
            is used.
        secure: bool, optional
            If ``True``, the option will be retrieved from secure storage
            using the :mod:`!keyring` Python package. Otherwise, will be
            retrieved from Spyder's normal configuration (the default).

        Returns
        -------
        value: spyder.api.config.mixins.BasicTypes | None
            Value of ``option`` in the configuration ``section``, or ``None``
            if the Spyder configuration object is not available (typically only
            the case in tests).

        Raises
        ------
        SpyderAPIError
            If ``section`` is not passed and :attr:`CONF_SECTION` is not
            defined.
        configparser.NoOptionError
            If the ``section`` does not exist in Spyder's configuration.
        """
        if self._conf is None:
            return None

        section = self.CONF_SECTION if section is None else section
        if section is None:
            raise SpyderAPIError(
                "A spyder plugin must define a `CONF_SECTION` class "
                "attribute!"
            )
        return self._conf.get(section, option, default, secure=secure)

    @Slot(str, object)
    @Slot(str, object, str)
    def set_conf(
        self,
        option: spyder.config.types.ConfigurationKey,
        value: BasicTypes,
        section: str | None = None,
        recursive_notification: bool = True,
        secure: bool = False,
    ) -> None:
        """
        Set an option's value in the Spyder configuration system.

        Parameters
        ----------
        option: spyder.config.types.ConfigurationKey
            Name/tuple path of the configuration option to set.
        value: spyder.api.config.mixins.BasicTypes
            Value to set for the given configuration option.
        section: str | None, optional
            Name of the configuration section to use, e.g. ``"shortcuts"``.
            If ``None``, the default, then the value of :attr:`CONF_SECTION`
            is used.
        recursive_notification: bool, optional
            If ``True``, all objects that observe all changes on the
            configuration ``section`` as well as objects that observe
            partial tuple paths are notified. For example, if the
            option ``opt`` of section ``sec`` changes, then
            all observers for section ``sec`` are notified. Likewise,
            if the option ``("a", "b", "c")`` changes, then observers for
            ``("a", "b", "c")``, ``("a", "b")`` and ``"a"`` are all notified.
        secure: bool, optional
            If ``True``, the option will be saved in secure storage
            using the :mod:`!keyring` Python package. Otherwise, will be
            saved in Spyder's normal configuration (the default).

        Returns
        -------
        None

        Raises
        ------
        SpyderAPIError
            If ``section`` is not passed and :attr:`CONF_SECTION` is not
            defined.
        """
        if self._conf is not None:
            section = self.CONF_SECTION if section is None else section
            if section is None:
                raise SpyderAPIError(
                    "A spyder plugin must define a `CONF_SECTION` class "
                    "attribute!"
                )

            self._conf.set(
                section,
                option,
                value,
                recursive_notification=recursive_notification,
                secure=secure,
            )
            self.apply_conf({option}, False)

    def remove_conf(
        self,
        option: spyder.config.types.ConfigurationKey,
        section: str | None = None,
        secure: bool = False,
    ) -> None:
        """
        Remove an option from the Spyder configuration system.

        Parameters
        ----------
        option: spyder.config.types.ConfigurationKey
            Name/tuple path of the configuration option to remove.
        section: str | None, optional
            Name of the configuration section to use, e.g. ``"shortcuts"``.
            If ``None``, the default, then the value of :attr:`CONF_SECTION`
            is used.
        secure: bool, optional
            If ``True``, the option will be removed from secure storage
            using the :mod:`!keyring` Python package. Otherwise, will be
            removed from Spyder's normal configuration (the default).

        Returns
        -------
        None

        Raises
        ------
        SpyderAPIError
            If ``section`` is not passed and :attr:`CONF_SECTION` is not
            defined.
        """
        if self._conf is not None:
            section = self.CONF_SECTION if section is None else section
            if section is None:
                raise SpyderAPIError(
                    "A spyder plugin must define a `CONF_SECTION` class "
                    "attribute!"
                )

            self._conf.remove_option(section, option, secure=secure)
            self.apply_conf({option}, False)

    def apply_conf(
        self,
        options_set: set[spyder.config.types.ConfigurationKey],
        notify: bool = True,
    ) -> None:
        """
        Handle applying a set of options to this plugin's widget.

        Parameters
        ----------
        options_set: set[spyder.config.types.ConfigurationKey]
            The set of option names that were changed.
        notify: bool, optional
            If ``True``, the default, call :meth:`after_configuration_update`
            to perform plugin-specific additional operations after applying
            the configuration changes. If ``False``, don't call the method.

        Returns
        -------
        None
        """
        if self._conf is not None and options_set:
            if notify:
                self.after_configuration_update(list(options_set))

    def disable_conf(
        self,
        option: spyder.config.types.ConfigurationKey,
        section: str | None = None,
    ) -> None:
        """
        Disable notifications for an option in the Spyder configuration system.

        Parameters
        ----------
        option: spyder.config.types.ConfigurationKey
            Name of the option, either a string or a tuple of strings.
        section: str | None, optional
            Name of the configuration section to use, e.g. ``"shortcuts"``.
            If ``None``, the default, then the value of :attr:`CONF_SECTION`
            is used.

        Returns
        -------
        None

        Raises
        ------
        SpyderAPIError
            If ``section`` is not passed and :attr:`CONF_SECTION` is not
            defined.
        """
        if self._conf is not None:
            section = self.CONF_SECTION if section is None else section
            if section is None:
                raise SpyderAPIError(
                    "A spyder plugin must define a `CONF_SECTION` class "
                    "attribute!"
                )
            self._conf.disable_notifications(section, option)

    def restore_conf(
        self,
        option: spyder.config.types.ConfigurationKey,
        section: str | None = None,
    ) -> None:
        """
        Restore notifications for an option in the Spyder configuration system.

        Parameters
        ----------
        option: spyder.config.types.ConfigurationKey
            Name of the option, either a string or a tuple of strings.
        section: str | None, optional
            Name of the configuration section to use, e.g. ``"shortcuts"``.
            If ``None``, the default, then the value of :attr:`CONF_SECTION`
            is used.

        Returns
        -------
        None

        Raises
        ------
        SpyderAPIError
            If ``section`` is not passed and :attr:`CONF_SECTION` is not
            defined.
        """
        if self._conf is not None:
            section = self.CONF_SECTION if section is None else section
            if section is None:
                raise SpyderAPIError(
                    "A spyder plugin must define a `CONF_SECTION` class "
                    "attribute!"
                )
            self._conf.restore_notifications(section, option)

    @Slot(str)
    @Slot(str, int)
    def show_status_message(self, message: str, timeout: int = 0) -> None:
        """
        Show a message in the Spyder status bar.

        Parameters
        ----------
        message: str
            The message to display in the status bar.
        timeout: int
            The amount of time, in milliseconds, to display the message.
            If ``0``, the default, the message will be shown until a plugin
            calls :meth:`!show_status_message` again.

        Returns
        -------
        None
        """
        self.sig_status_message_requested.emit(message, timeout)

    def before_long_process(self, message: str) -> None:
        """
        Perform actions required before starting a long-running process.

        Shows a message in the main window's status bar,
        and changes the mouse pointer to a wait cursor.

        Parameters
        ----------
        message: str
            Message to show in the status bar when the long process starts.

        Returns
        -------
        None
        """
        if message:
            self.show_status_message(message)

        QApplication.setOverrideCursor(QCursor(Qt.WaitCursor))
        QApplication.processEvents()

    def after_long_process(self, message: str = "") -> None:
        """
        Perform actions required after starting a long-running process.

        Clears the message in the Spyder main window's status bar
        and restores the mouse pointer to the OS default.

        Parameters
        ----------
        message: str, optional
            Message to show in the status bar when the long process finishes.
            An empty message by default, clearing the previous message.

        Returns
        -------
        None
        """
        QApplication.restoreOverrideCursor()
        self.show_status_message(message, timeout=2000)
        QApplication.processEvents()

    def get_color_scheme(
        self,
    ) -> dict[str, str | tuple[str, bool, bool]] | None:
        """
        Get the Editor's current color scheme.

        This is useful to set the color scheme of all instances of
        CodeEditor used by the plugin.

        Returns
        -------
        dict[str, str | tuple[str, bool, bool]] | None
            Dictionary with properties and colors of the color scheme
            used in the Editor, or ``None`` if the Spyder configuration
            object is not available (usually only ever the case in tests).
        """
        if self._conf is None:
            return None

        return get_color_scheme(self._conf.get("appearance", "selected"))

    def initialize(self) -> None:
        """
        Initialize a plugin instance.

        .. caution::

            This method should be called to initialize the plugin, but it
            should not be overridden, since it calls :meth:`on_initialize`
            and emits the :attr:`sig_plugin_ready` signal.

        Returns
        -------
        None
        """
        self.on_initialize()
        self.sig_plugin_ready.emit()

    @staticmethod
    def create_icon(name) -> QIcon:
        """
        Retrieve an icon from the theme and icon manager.

        Parameters
        ----------
        name: str
            The name of the icon to retrieve.

        Returns
        -------
        QIcon
            The specified icon, as a :class:`QIcon` instance.
        """
        return ima.icon(name)

    @classmethod
    def get_font(cls, font_type: str) -> QFont:
        """
        Return the font object for one of the font types used in Spyder.

        All plugins in Spyder use the same, global fonts. In case a plugin
        wants to use a different font size than on the default, it can set
        the :attr:`MONOSPACE_FONT_SIZE_DELTA` or
        :attr:`INTERFACE_FONT_SIZE_DELTA` class constants.

        Parameters
        ----------
        font_type: str
            The kind of font to return the object for, as listed under the
            :class:`~spyder.api.fonts.SpyderFontType` pseudo-enum class.
            See that class' documentation for more details.

        Returns
        -------
        QFont
            :class:`QFont` object for the specified ``font_type``, to be
            passed to other Qt widgets.
        """
        if font_type == SpyderFontType.Monospace:
            font_size_delta = cls.MONOSPACE_FONT_SIZE_DELTA
        elif font_type in [
            SpyderFontType.Interface,
            SpyderFontType.MonospaceInterface,
        ]:
            font_size_delta = cls.INTERFACE_FONT_SIZE_DELTA
        else:
            raise SpyderAPIError("Unrecognized font type")

        return get_font(option=font_type, font_size_delta=font_size_delta)

    def get_command_line_options(self) -> argparse.Namespace:
        """
        Get the command line options passed by the user when starting Spyder.

        See :mod:`spyder.app.cli_options` for the option names.

        Returns
        -------
        argparse.Namespace
            Namespace of the passed option keys and values.
        """
        if self._main is not None:
            return self._main._cli_options
        else:
            # This is necessary when the plugin has no parent.
            sys_argv = [sys.argv[0]]  # Avoid options passed to pytest
            return get_options(sys_argv)[0]

    # ---- API: Mandatory methods to define
    # -------------------------------------------------------------------------
    @staticmethod
    def get_name() -> str:
        """
        Return the plugin's localized name.

        .. note::

            This method needs to be decorated with :func:`staticmethod`.

        Returns
        -------
        str
            Localized name of the plugin.
        """
        raise NotImplementedError("A plugin name must be defined!")

    @staticmethod
    def get_description() -> str:
        """
        Return the plugin's localized description.

        .. note::

            This method needs to be decorated with :func:`staticmethod`.

        Returns
        -------
        str
            Localized description of the plugin.
        """
        raise NotImplementedError("A plugin description must be defined!")

    @classmethod
    def get_icon(cls) -> QIcon:
        """
        Return the plugin's associated icon.

        .. note::

            This method needs to be decorated with :func:`classmethod` or
            :func:`staticmethod`.

        Returns
        -------
        QIcon
            The plugin's icon, as a :class:`QIcon` instance.
        """
        raise NotImplementedError("A plugin icon must be defined!")

    def on_initialize(self) -> None:
        """
        Set up the plugin.

        .. caution::

            Any calls performed in this method should not call other plugins.

        Returns
        -------
        None
        """
        raise NotImplementedError(
            f"The plugin {type(self)} is missing an implementation of "
            "on_initialize"
        )

    # ---- API: Optional methods to override
    # -------------------------------------------------------------------------
    @staticmethod
    def check_compatibility() -> tuple[bool, str]:
        """
        Check compatibility of a plugin with the user's current environment.

        Intended for plugin-specific checks, so needs to be reimplemented by
        the plugin subclass to do anything meaningful.

        Returns
        -------
        valid, message: tuple[bool, str]
            The first value, ``valid``, tells Spyder if the plugin has passed
            the compatibility test defined in this method.

            The second value, ``message``, must (if ``valid`` is ``False``)
            explain to users why the plugin was found to be incompatible
            (e.g. ``"This plugin does not work with PyQt4"``).
            It will be shown at startup in a :class:`QMessageBox`.
        """
        valid = True
        message = ""  # Note: Remember to use _('') to localize the string
        return valid, message

    def on_first_registration(self) -> None:
        """
        Actions to be performed the first time the plugin is started.

        It can also be used to perform actions that are needed only the
        first time this is loaded after installation.

        This method is called after the main window is visible.

        Returns
        -------
        None
        """
        pass

    def before_mainwindow_visible(self) -> None:
        """
        Actions to be performed after setup but before showing the main window.

        Returns
        -------
        None
        """
        pass

    def on_mainwindow_visible(self) -> None:
        """
        Actions to be performed after the main window has been shown.

        Returns
        -------
        None
        """
        pass

    def on_close(self, cancelable: bool = False) -> None:
        """
        Perform actions before the plugin is closed.

        .. caution::

            This method **must** only operate on local attributes and not
            call other plugins.

        Parameters
        ----------
        cancelable: bool, optional
            ``True`` if the close operation can potentially be canceled;
            ``False`` by default.

        Returns
        -------
        None
        """
        pass

    def can_close(self) -> bool:
        """
        Determine if the plugin can be closed.

        Returns
        -------
        close: bool
            ``True`` if the plugin can be closed, ``False`` otherwise.
        """
        return True

    def update_font(self) -> None:
        """
        Modify the font used in the plugin's interface.
        
        This must be reimplemented by plugins that need to adjust their fonts.

        The following plugins illustrate the usage of this method:
          * :mod:`spyder.plugins.help.plugin`
          * :mod:`spyder.plugins.onlinehelp.plugin`

        Returns
        -------
        None
        """
        pass

    def update_style(self) -> None:
        """
        Modify the interface styling used by the plugin.
        
        This must be reimplemented by plugins that need to adjust their style.

        Changing from the dark to the light interface theme might
        require specific styles or stylesheets to be applied. When
        the theme is changed by the user through our :guilabel:`Preferences`,
        this method will be called for all plugins.

        Returns
        -------
        None
        """
        pass

    def after_container_creation(self) -> None:
        """
        Perform necessary operations before setting up the container.

        This must be reimplemented by plugins whose containers emit signals
        that need to be connected before applying options to Spyder's config
        system.

        Returns
        -------
        None
        """
        pass

    def after_configuration_update(
        self, options: list[spyder.config.types.ConfigurationKey]
    ) -> None:
        """
        Perform additional operations after updating the plugin config options.

        This can be implemented by plugins that do not have a container and
        need to act on configuration updates.

        Parameters
        ----------
        options: list[spyder.config.types.ConfigurationKey]
            A list that contains the option names that were updated.

        Returns
        -------
        None
        """
        pass


class SpyderDockablePlugin(SpyderPluginV2):
    """
    Subclass for plugins with a dockable widget (pane) in the interface.
    """

    # ---- API: Mandatory attributes
    # -------------------------------------------------------------------------

    WIDGET_CLASS: type[PluginMainWidget] = None
    """
    This is the main widget of the dockable plugin.

    It must be a subclass of
    :class:`spyder.api.widgets.main_widget.PluginMainWidget`.
    """

    # ---- API: Optional attributes
    # -------------------------------------------------------------------------

    TABIFY: list[str] = []
    """
    Define a list of plugins next to which we want to tabify this plugin.

    Examples
    --------

    .. code-block:: python

        TABIFY = [Plugins.Editor]
    """

    DISABLE_ACTIONS_WHEN_HIDDEN: bool = True
    """
    Disable the plugin's actions in the main menu when the plugin is hidden.

    If ``True``, disable the plugin's actions when it is not shown (default);
    if ``False``, keep them enabled.
    """

    RAISE_AND_FOCUS: bool = False
    """
    Give the plugin focus on switch to plugin calls.

    If ``True``, the plugin will be given focus when switched to.
    If ``False``, the default, the plugin's widget will still be raised to
    the foreground, but it will not be given focus until the switch action
    is called a second time.
    """

    CAN_HANDLE_FILE_ACTIONS: bool = False
    """
    Whether the plugin declares it can handle file actions.

    If set to ``True``, then the :meth:`create_new_file`,
    :meth:`open_last_closed_file`, :meth:`save_file`, :meth:`save_file_as`,
    :meth:`save_copy_as`, :meth:`save_all`, :meth:`revert_file`,
    :meth:`close_file` and :meth:`close_all` methods will be called
    to handle the corresponding actions.

    If set to ``False``, the default, the corresponding actions fall back
    to calling these methods on the :guilabel:`Editor`.

    Individual actions can be disabled with the
    :meth:`spyder.plugins.application.plugin.enable_file_action` method
    in the :guilabel:`Application` plugin.
    """

    FILE_EXTENSIONS: list[str] = []
    """
    List of file extensions which the plugin can open.

    If the user opens a file with one of these extensions, then the file
    will open in this plugin using its :meth:`open_file` method.

    Examples
    --------

    For example, in the Spyder-Notebook plugin to open Jupyter notebooks:

    .. code-block:: python

        FILE_EXTENSIONS = [".ipynb"]
    """

    CAN_HANDLE_EDIT_ACTIONS: bool = False
    """
    Whether the plugin can handle editing actions.

    If set to ``True``, then the :meth:`undo`, :meth:`redo`, :meth:`cut`,
    :meth:`copy`, :meth:`paste` and :meth:`select_all` methods will be called
    to handle the corresponding actions.

    If set to ``False``, the default, the corresponding actions fall back
    to calling these methods on the :guilabel:`Editor`.

    Individual actions can be disabled with the
    :meth:`spyder.plugins.application.plugin.enable_edit_action` method
    in the :guilabel:`Application` plugin.
    """

    CAN_HANDLE_SEARCH_ACTIONS = False
    """
    Whether the plugin can handle search actions.

    If set to ``True``, then the :meth:`find`, :meth:`find_next`,
    :meth:`find_previous` and :meth:`replace` methods will be called
    to handle the corresponding actions.

    If set to ``False``, the default, the corresponding actions fall back
    to calling these methods on the :guilabel:`Editor`.

    Individual actions can be disabled with the
    :meth:`spyder.plugins.application.plugin.enable_search_action` method
    in the :guilabel:`Application` plugin.
    """

    # ---- API: Available signals
    # -------------------------------------------------------------------------
    sig_focus_changed: Signal = Signal()
    """
    Report the focus state of this plugin has changed.
    """

    sig_toggle_view_changed: Signal = Signal(bool)
    """
    Report that visibility of a dockable plugin has changed.

    This is triggered by checking/unchecking the entry for a pane in the
    :menuselection:`Window --> Panes` menu.

    Parameters
    ----------
    visible: bool
        Whether the dockwidget has been shown (``True``) or hidden (``False``).
    """

    sig_switch_to_plugin_requested: Signal = Signal(object, bool)
    """
    Request the main window show this plugin's widget.

    Parameters
    ----------
    plugin: SpyderDockablePlugin
        The plugin object to show.
    force_focus: bool
        If ``True``, always give the plugin's widget focus when showing
        or hiding it with this method. If ``False``, the default,
        don't give it focus.
    """

    sig_update_ancestor_requested: Signal = Signal()
    """
    Notify the main window that a child widget needs its ancestor updated.
    """

    # ---- Private methods
    # -------------------------------------------------------------------------
    def __init__(
        self,
        parent: spyder.app.mainwindow.MainWindow,
        configuration: spyder.config.manager.ConfigurationManager,
    ):
        """
        Initialize the plugin object (called automatically by Spyder).

        .. important::

            Plugins are initialized automatically by Spyder, so they shouldn't
            call or override this method directly.

        Parameters
        ----------
        parent : spyder.app.mainwindow.MainWindow
            Parent Spyder window of this plugin.
        configuration : spyder.config.manager.ConfigurationManager
            The Spyder configuration manager object for the plugin to access.

        Raises
        ------
        SpyderAPIError
            If :attr:`WIDGET_CLASS` is not set to a subclass of
            :class:`spyder.api.widgets.main_widget.PluginMainWidget`.

        Returns
        -------
        None
        """
        if not issubclass(self.WIDGET_CLASS, PluginMainWidget):
            raise SpyderAPIError(
                "A SpyderDockablePlugin must define a valid WIDGET_CLASS "
                "attribute!"
            )

        self.CONTAINER_CLASS = self.WIDGET_CLASS
        super().__init__(parent, configuration=configuration)

        self._switch_to_shortcut = None
        """Shortcut to switch to the plugin, defined on the main window."""

        # Widget setup
        # --------------------------------------------------------------------
        self._widget = self._container
        widget = self._widget
        if widget is None:
            raise SpyderAPIError(
                "A dockable plugin must define a WIDGET_CLASS!"
            )

        if not isinstance(widget, PluginMainWidget):
            raise SpyderAPIError(
                "The WIDGET_CLASS of a dockable plugin must be a subclass of "
                "PluginMainWidget!"
            )

        widget.DISABLE_ACTIONS_WHEN_HIDDEN = self.DISABLE_ACTIONS_WHEN_HIDDEN
        widget.RAISE_AND_FOCUS = self.RAISE_AND_FOCUS
        widget.set_icon(self.get_icon())
        widget.set_name(self.NAME)

        # Render all toolbars as a final separate step on the main window
        # in case some plugins want to extend a toolbar. Since the rendering
        # can only be done once!
        widget.render_toolbars()

        # Default Signals
        # --------------------------------------------------------------------
        widget.sig_toggle_view_changed.connect(self.sig_toggle_view_changed)
        widget.sig_update_ancestor_requested.connect(
            self.sig_update_ancestor_requested
        )

    # ---- API: Optional methods to override
    # -------------------------------------------------------------------------
    def create_new_file(self) -> None:
        """
        Create a new file inside the plugin.

        This method will be called if the user creates a new file using
        the :menuselection:`File --> New` menu item or the :guilabel:`New file`
        button in the main toolbar, and :attr:`CAN_HANDLE_FILE_ACTIONS` is
        set to ``True``.

        Returns
        -------
        None
        """
        raise NotImplementedError

    def open_file(self, filename: str) -> None:
        """
        Open a file inside the plugin.

        This method will be called if the user wants to open a file with one
        of the file name extensions listed in :attr:`FILE_EXTENSIONS`,
        so that attribute needs to be set too in order to use this method.

        Parameters
        ----------
        filename: str
            The name of the file to be opened.

        Returns
        -------
        None
        """
        raise NotImplementedError

    def get_current_filename(self) -> str | None:
        """
        Return the name of the file that is currently displayed.

        This is meant for plugins like the :guilabel:`Editor` or
        Spyder-Notebook which can display or edit files. Return ``None``
        if no file is displayed or if this plugin does not display files.

        This method is used in the :guilabel:`Open file` action to
        initialize the :guilabel:`Open file` dialog.

        Returns
        -------
        str | None
            The filename currently displayed in the plugin as a string,
            or ``None`` if no file is opened.
        """
        return None

    def current_file_is_temporary(self) -> bool:
        """
        Return whether the currently displayed file is a temporary file.

        This method should only be called if a file is displayed; that is,
        if :meth:`get_current_filename` does not return `None`.

        Returns
        -------
        bool
            ``True`` if the plugin's currently displayed file is a temporary
            one, ``False`` otherwise.
        """
        return False

    def open_last_closed_file(self) -> None:
        """
        Reopen the last closed file.

        This method will be called if the
        :menuselection:`File --> Open last closed` menu item is selected
        while the plugin has focus and :attr:`CAN_HANDLE_FILE_ACTIONS`
        is set to ``True``.

        Returns
        -------
        None
        """
        raise NotImplementedError

    def save_file(self) -> None:
        """
        Save the current file.

        This method will be called if the user saves the current file using
        the :menuselection:`File --> Save` menu item or the
        :guilabel:`Save file` button in the main toolbar, the plugin has focus,
        and :attr:`CAN_HANDLE_FILE_ACTIONS` is set to ``True``.

        Returns
        -------
        None
        """
        raise NotImplementedError

    def save_file_as(self) -> None:
        """
        Save the current file under a different name.

        This method will be called if the user saves the current file using
        the :menuselection:`File --> Save as` menu item, the plugin has focus,
        and :attr:`CAN_HANDLE_FILE_ACTIONS` is set to ``True``.

        Returns
        -------
        None
        """
        raise NotImplementedError

    def save_copy_as(self) -> None:
        """
        Save a copy of the current file under a different name.

        This method will be called if the user saves the current file using
        the :menuselection:`File --> Save copy as` menu item,
        the plugin has focus, and :attr:`CAN_HANDLE_FILE_ACTIONS` is set to
        ``True``.

        Returns
        -------
        None
        """
        raise NotImplementedError

    def save_all(self) -> None:
        """
        Save all files that are opened in the plugin.

        This method will be called if the user saves all open file using
        the :menuselection:`File --> Save all` menu item or the
        :guilabel:`Save all` button in the main toolbar, the plugin has focus,
        and :attr:`CAN_HANDLE_FILE_ACTIONS` is set to ``True``.

        Returns
        -------
        None
        """
        raise NotImplementedError

    def revert_file(self) -> None:
        """
        Revert the current file to the version stored on disk.

        This method will be called if the :menuselection:`File --> Revert`
        menu item is selected, the plugin has focus, and
        :attr:`CAN_HANDLE_FILE_ACTIONS` is set to ``True``.

        Returns
        -------
        None
        """
        raise NotImplementedError

    def close_file(self) -> None:
        """
        Close the current file.

        This method will be called if the :menuselection:`File --> Close`
        menu item is selected, the plugin has focus, and
        :attr:`CAN_HANDLE_FILE_ACTIONS` is set to ``True``.

        Returns
        -------
        None
        """
        raise NotImplementedError

    def close_all(self) -> None:
        """
        Close all opened files.

        This method will be called if the :menuselection:`File --> Close all`
        menu item is selected, the plugin has focus, and
        :attr:`CAN_HANDLE_FILE_ACTIONS` is set to ``True``.

        Returns
        -------
        None
        """
        raise NotImplementedError

    def undo(self) -> None:
        """
        Undo the most recent change.

        This method will be called if the :menuselection:`Edit --> Undo`
        menu item is selected, the plugin has focus, and
        :attr:`CAN_HANDLE_EDIT_ACTIONS` is set to ``True``.

        Returns
        -------
        None
        """
        raise NotImplementedError

    def redo(self) -> None:
        """
        Redo the most recently undone change.

        This method will be called if the :menuselection:`Edit --> Redo`
        menu item is selected, the plugin has focus, and
        :attr:`CAN_HANDLE_EDIT_ACTIONS` is set to ``True``.

        Returns
        -------
        None
        """
        raise NotImplementedError

    def cut(self) -> None:
        """
        Copy and remove the current selection.

        This method will be called if the :menuselection:`Edit --> Cut`
        menu item is selected, the plugin has focus, and
        :attr:`CAN_HANDLE_EDIT_ACTIONS` is set to ``True``.

        Returns
        -------
        None
        """
        raise NotImplementedError

    def copy(self) -> None:
        """
        Copy the current selection.

        This method will be called if the :menuselection:`Edit --> Copy`
        menu item is selected, the plugin has focus, and
        :attr:`CAN_HANDLE_EDIT_ACTIONS` is set to ``True``.

        Returns
        -------
        None
        """
        raise NotImplementedError

    def paste(self) -> None:
        """
        Paste the current clipboard contents.

        This method will be called if the :menuselection:`Edit --> Paste`
        menu item is selected, the plugin has focus, and
        :attr:`CAN_HANDLE_EDIT_ACTIONS` is set to ``True``.

        Returns
        -------
        None
        """
        raise NotImplementedError

    def select_all(self) -> None:
        """
        Select all content in the plugin.

        This method will be called if the :menuselection:`Edit --> Select all`
        menu item is selected, the plugin has focus, and
        :attr:`CAN_HANDLE_EDIT_ACTIONS` is set to ``True``.

        Returns
        -------
        None
        """
        raise NotImplementedError

    def find(self) -> None:
        """
        Search for text in the plugin.

        This method will be called if the :menuselection:`Search --> Find text`
        menu item is selected, the plugin has focus, and
        :attr:`CAN_HANDLE_SEARCH_ACTIONS` is set to ``True``.

        Returns
        -------
        None
        """
        raise NotImplementedError

    def find_next(self) -> None:
        """
        Move to the next occurrence of found text in the plugin.

        This method will be called if the :menuselection:`Search --> Find next`
        menu item is selected, the plugin has focus, and
        :attr:`CAN_HANDLE_SEARCH_ACTIONS` is set to ``True``.

        Returns
        -------
        None
        """
        raise NotImplementedError

    def find_previous(self) -> None:
        """
        Move to the previous occurrence of found text in the plugin.

        This method will be called if the
        :menuselection:`Search --> Find previous` menu item is selected,
        the plugin has focus, and :attr:`CAN_HANDLE_SEARCH_ACTIONS` is set
        to ``True``.

        Returns
        -------
        None
        """
        raise NotImplementedError

    def replace(self) -> None:
        """
        Replace occurrence of text in the plugin.

        This method will be called if the
        :menuselection:`Search --> Replace text` menu item is selected,
        the plugin has focus, and :attr:`CAN_HANDLE_SEARCH_ACTIONS` is set
        to ``True``.

        Returns
        -------
        None
        """
        raise NotImplementedError

    # ---- API: available methods
    # -------------------------------------------------------------------------
    def before_long_process(self, message: str) -> None:
        """
        Perform actions required before starting a long-running process.

        Shows a message in the main window's status bar,
        changes the mouse pointer to a wait cursor, and starts a spinner.

        Parameters
        ----------
        message: str
            Message to show in the status bar when the long process starts.

        Returns
        -------
        None
        """
        self.get_widget().start_spinner()
        super().before_long_process(message)

    def after_long_process(self, message: str = "") -> None:
        """
        Perform actions required after starting a long-running process.

        Clears the message in the Spyder main window's status bar,
        restores the mouse pointer to the OS default, and stops spinner.

        Parameters
        ----------
        message: str, optional
            Message to show in the status bar when the long process finishes.
            An empty message by default, clearing the previous message.

        Returns
        -------
        None
        """
        super().after_long_process(message)
        self.get_widget().stop_spinner()

    def get_widget(self) -> PluginMainWidget:
        """
        Return the plugin's main widget.

        Returns
        -------
        spyder.api.widgets.main_widget.PluginMainWidget
            The plugin's main widget, an instance of :attr:`WIDGET_CLASS`.
        """
        if self._widget is None:
            raise SpyderAPIError("Dockable plugin must have a WIDGET_CLASS!")

        return self._widget

    def update_title(self) -> None:
        """
        Update the plugin widget's title, i.e. its dockwidget or window title.

        Returns
        -------
        None
        """
        self.get_widget().update_title()

    def update_margins(self, margin: int | None) -> None:
        """
        Update the margins of the main widget inside this dockable plugin.

        Parameters
        ----------
        margin: int | None
            The margins to use for the main widget, or ``None`` for the
            default margins.

        Returns
        -------
        None
        """
        self.get_widget().update_margins(margin)

    @Slot()
    def switch_to_plugin(self, force_focus: bool = False) -> None:
        """
        Switch to this plugin and define if focus should be given or not.

        Parameters
        ----------
        force_focus : bool | None, optional
            If ``True``, always give the plugin's widget focus when showing
            or hiding it with this method. If ``False``, the default,
            don't give it focus.

        Returns
        -------
        None
        """
        if self.get_widget().windowwidget is None:
            self.sig_switch_to_plugin_requested.emit(self, force_focus)

    def set_ancestor(self, ancestor_widget: QWidget) -> None:
        """
        Update the ancestor/parent of child widgets when undocking.

        Parameters
        ----------
        ancestor_widget: QWidget
            The window widget to set as a parent of this one.

        Returns
        -------
        None
        """
        self.get_widget().set_ancestor(ancestor_widget)

    # ---- Convenience methods from the widget exposed on the plugin
    # -------------------------------------------------------------------------
    @property
    def dockwidget(self) -> spyder.widgets.dock.SpyderDockWidget:
        """The dockable widget (pane) for this plugin."""
        return self.get_widget().dockwidget

    @property
    def options_menu(self) -> PluginMainWidgetOptionsMenu:
        """The options ("hamburger") menu widget for this plugin."""
        return self.get_widget().get_options_menu()

    @property
    def toggle_view_action(self) -> spyder.utils.qthelpers.SpyderAction:
        """The :class:`QAction` for showing/hiding this plugin's pane."""
        return self.get_widget().toggle_view_action

    def create_dockwidget(
        self,
        mainwindow: spyder.app.mainwindow.MainWindow,
    ) -> spyder.widgets.dock.SpyderDockWidget:
        """
        Create a new dock widget for this plugin.

        Parameters
        ----------
        mainwindow : spyder.app.mainwindow.MainWindow
            The main window to set as the dockwidget's parent.

        Returns
        -------
        spyder.widgets.dock.SpyderDockWidget
            The new dock widget created for the plugin.
        """
        return self.get_widget().create_dockwidget(mainwindow)

    def create_window(self) -> None:
        """
        Create an undocked window for the plugin.

        Returns
        -------
        None
        """
        self.get_widget().create_window()

    def close_window(self, save_undocked: bool = False) -> None:
        """
        Close the plugin's undocked window, optionally saving its state.
        
        This is a convenience wrapper to close an undocked plugin.

        Parameters
        ----------
        save_undocked : bool, optional
            ``True`` if the window state (size and position) should be saved.
            If ``False``, the default, don't persist the window state.

        Returns
        -------
        None
        """
        self.get_widget()._close_window(save_undocked=save_undocked)

    def change_visibility(
        self, state: bool, force_focus: bool = False
    ) -> None:
        """
        Raise the plugin's dockwidget to the foreground, and/or grab its focus.

        Parameters
        ----------
        state : bool
            Whether the plugin's widget is being raised to the foreground
            (``True``) or set as not in the foreground (``False``).
            The latter does not actually send it to the background, but
            does configure it for not being actively shown (e.g. it disables
            its empty pane graphics).
        force_focus : bool | None, optional
            If ``True``, always give the plugin's widget keyboard focus when
            raising or un-raising it with this method. If ``None``, only give
            it focus when showing, not hiding (setting ``state`` to ``True``),
            and only if :attr:`RAISE_AND_FOCUS` is ``True``. If ``False``,
            the default, don't give it focus regardless.

        Returns
        -------
        None
        """
        self.get_widget().change_visibility(state, force_focus)

    def toggle_view(self, value: bool) -> None:
        """
        Show or hide the plugin's dockwidget in the Spyder interface.

        Used to show or hide it from the from the
        :menuselection:`Window --> Panes` menu.

        Parameters
        ----------
        value : bool
            Whether to show (``True``) or hide (``False``) the dockwidget.

        Returns
        -------
        None
        """
        self.get_widget().toggle_view(value)
