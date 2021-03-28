# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""
spyder.api.plugins
==================

Here, 'plugins' are Qt objects that can make changes to Spyder's
main window and call other plugins directly.

There are two types of plugins available:

1. SpyderPluginV2 is a plugin that does not create a new dock/pane on Spyder's
   main window. Note: SpyderPluginV2 will be renamed to SpyderPlugin once the
   migration to the new API is finished

2. SpyderDockablePlugin is a plugin that does create a new dock/pane on
   Spyder's main window.
"""

# Standard library imports
from collections import OrderedDict
import inspect
import logging
import os
import os.path as osp
from typing import List, Union

# Third party imports
from qtpy.QtCore import QObject, Qt, Signal, Slot
from qtpy.QtGui import QCursor
from qtpy.QtWidgets import QApplication, QWidget

# Local imports
from spyder.api.config.mixins import SpyderConfigurationObserver
from spyder.api.exceptions import SpyderAPIError
from spyder.api.translations import get_translation
from spyder.api.widgets.main_container import PluginMainContainer
from spyder.api.widgets.main_widget import PluginMainWidget
from spyder.api.widgets.mixins import SpyderActionMixin
from spyder.api.widgets.mixins import SpyderWidgetMixin
from spyder.config.gui import get_color_scheme, get_font
from spyder.config.user import NoDefault
from spyder.plugins.base import BasePluginMixin, BasePluginWidgetMixin
from spyder.utils.icon_manager import ima
from spyder.utils.image_path_manager import IMAGE_PATH_MANAGER

# Localization
_ = get_translation('spyder')
logger = logging.getLogger(__name__)


# =============================================================================
# SpyderPlugin
# =============================================================================
class BasePlugin(BasePluginMixin):
    """
    Basic functionality for Spyder plugins.

    WARNING: Don't override any methods or attributes present here!
    """
    # Use this signal to display a message in the status bar.
    # str: The message you want to display
    # int: Amount of time to display the message
    sig_show_status_message = Signal(str, int)

    # Use this signal to inform another plugin that a configuration
    # value has changed.
    sig_option_changed = Signal(str, object)

    def __init__(self, parent=None):
        super(BasePlugin, self).__init__(parent)

        # This is the plugin parent, which corresponds to the main
        # window.
        self.main = parent

        # Filesystem path to the root directory that contains the
        # plugin
        self.PLUGIN_PATH = self._get_plugin_path()

        # Connect signals to slots.
        self.sig_show_status_message.connect(self.show_status_message)
        self.sig_option_changed.connect(self.set_option)

    @Slot(str)
    @Slot(str, int)
    def show_status_message(self, message, timeout=0):
        """
        Show message in main window's status bar.

        Parameters
        ----------
        message: str
            Message to display in the status bar.
        timeout: int
            Amount of time to display the message.
        """
        super(BasePlugin, self)._show_status_message(message, timeout)

    @Slot(str, object)
    def set_option(self, option, value, section=None,
                   recursive_notification=True):
        """
        Set an option in Spyder configuration file.

        Parameters
        ----------
        option: str
            Name of the option (e.g. 'case_sensitive')
        value: bool, int, str, tuple, list, dict
            Value to save in configuration file, passed as a Python
            object.

        Notes
        -----
        * Use sig_option_changed to call this method from widgets of the
          same or another plugin.
        * CONF_SECTION needs to be defined for this to work.
        """
        super(BasePlugin, self)._set_option(
            option, value, section=section,
            recursive_notification=recursive_notification)

    def get_option(self, option, default=NoDefault, section=None):
        """
        Get an option from Spyder configuration file.

        Parameters
        ----------
        option: str
            Name of the option to get its value from.

        Returns
        -------
        bool, int, str, tuple, list, dict
            Value associated with `option`.
        """
        return super(BasePlugin, self)._get_option(option, default,
                                                   section=section)

    def remove_option(self, option, section=None):
        """
        Remove an option from the Spyder configuration file.

        Parameters
        ----------
        option: Union[str, Tuple[str, ...]]
            A string or a Tuple of strings containing an option name to remove.
        section: Optional[str]
            Name of the section where the option belongs to.
        """
        return super(BasePlugin, self)._remove_option(option, section=section)

    def starting_long_process(self, message):
        """
        Show a message in main window's status bar and changes the
        mouse to Qt.WaitCursor when starting a long process.

        Parameters
        ----------
        message: str
            Message to show in the status bar when the long
            process starts.
        """
        super(BasePlugin, self)._starting_long_process(message)

    def ending_long_process(self, message=""):
        """
        Clear main window's status bar after a long process and restore
        mouse to the OS deault.

        Parameters
        ----------
        message: str
            Message to show in the status bar when the long process
            finishes.
        """
        super(BasePlugin, self)._ending_long_process(message)


class SpyderPlugin(BasePlugin):
    """
    Spyder plugin class.

    All plugins *must* inherit this class and reimplement its interface.
    """
    # ---------------------------- ATTRIBUTES ---------------------------------

    # Name of the configuration section that's going to be
    # used to record the plugin's permanent data in Spyder
    # config system (i.e. in spyder.ini)
    # Status: Optional
    CONF_SECTION = None

    # One line localized description of the features this plugin implements
    # Status: Optional
    DESCRIPTION = None

    # Widget to be used as entry in Spyder Preferences dialog
    # Status: Optional
    CONFIGWIDGET_CLASS = None

    # Use separate configuration file for plugin
    # Status: Optional
    CONF_FILE = True

    # Define configuration defaults if using a separate file.
    # List of tuples, with the first item in the tuple being the section
    # name and the second item being the default options dictionary.
    # Status: Optional
    #
    # CONF_DEFAULTS_EXAMPLE = [
    #     ('section-name', {'option-1': 'some-value',
    #                       'option-2': True,}),
    #     ('another-section-name', {'option-3': 'some-other-value',
    #                               'option-4': [1, 2, 3],}),
    # ]
    CONF_DEFAULTS = None

    # Define configuration version if using a separate file
    # Status: Optional
    #
    # IMPORTANT NOTES:
    # 1. If you want to *change* the default value of a current option, you
    #    need to do a MINOR update in config version, e.g. from 3.0.0 to 3.1.0
    # 2. If you want to *remove* options that are no longer needed or if you
    #    want to *rename* options, then you need to do a MAJOR update in
    #    version, e.g. from 3.0.0 to 4.0.0
    # 3. You don't need to touch this value if you're just adding a new option
    CONF_VERSION = None

    # ------------------------------ METHODS ----------------------------------

    def check_compatibility(self):
        """
        This method can be reimplemented to check compatibility of a
        plugin for a given condition.

        Returns
        -------
        (bool, str)
            The first value tells Spyder if the plugin has passed the
            compatibility test defined in this method. The second value
            is a message that must explain users why the plugin was
            found to be incompatible (e.g. 'This plugin does not work
            with PyQt4'). It will be shown at startup in a QMessageBox.
        """
        message = ''
        valid = True
        return valid, message


# =============================================================================
# SpyderPluginWidget
# =============================================================================
class BasePluginWidget(QWidget, BasePluginWidgetMixin):
    """
    Basic functionality for Spyder plugin widgets.

    WARNING: Don't override any methods or attributes present here!
    """

    # Signal used to update the plugin title when it's undocked
    sig_update_plugin_title = Signal()

    def __init__(self, main=None):
        super(BasePluginWidget, self).__init__(main)

        # Dockwidget for the plugin, i.e. the pane that's going to be
        # displayed in Spyder for this plugin.
        # Note: This is created when you call the `add_dockwidget`
        # method, which must be done in the `register_plugin` one.
        self.dockwidget = None

    def add_dockwidget(self):
        """Add the plugin's QDockWidget to the main window."""
        super(BasePluginWidget, self)._add_dockwidget()

    def tabify(self, core_plugin):
        """
        Tabify plugin next to one of the core plugins.

        Parameters
        ----------
        core_plugin: SpyderPluginWidget
            Core Spyder plugin this one will be tabified next to.

        Examples
        --------
        >>> self.tabify(self.main.variableexplorer)
        >>> self.tabify(self.main.ipyconsole)

        Notes
        -----
        The names of variables associated with each of the core plugins
        can be found in the `setup` method of `MainWindow`, present in
        `spyder/app/mainwindow.py`.
        """
        super(BasePluginWidget, self)._tabify(core_plugin)

    def get_font(self, rich_text=False):
        """
        Return plain or rich text font used in Spyder.

        Parameters
        ----------
        rich_text: bool
            Return rich text font (i.e. the one used in the Help pane)
            or plain text one (i.e. the one used in the Editor).

        Returns
        -------
        QFont:
            QFont object to be passed to other Qt widgets.

        Notes
        -----
        All plugins in Spyder use the same, global font. This is a
        convenience method in case some plugins want to use a delta
        size based on the default one. That can be controlled by using
        FONT_SIZE_DELTA or RICH_FONT_SIZE_DELTA (declared below in
        `SpyderPluginWidget`).
        """
        return super(BasePluginWidget, self)._get_font(rich_text)

    def register_shortcut(self, qaction_or_qshortcut, context, name,
                          add_shortcut_to_tip=False):
        """
        Register a shortcut associated to a QAction or a QShortcut to
        Spyder main application.

        Parameters
        ----------
        qaction_or_qshortcut: QAction or QShortcut
            QAction to register the shortcut for or QShortcut.
        context: str
            Name of the plugin this shortcut applies to. For instance,
            if you pass 'Editor' as context, the shortcut will only
            work when the editor is focused.
            Note: You can use '_' if you want the shortcut to be work
            for the entire application.
        name: str
            Name of the action the shortcut refers to (e.g. 'Debug
            exit').
        add_shortcut_to_tip: bool
            If True, the shortcut is added to the action's tooltip.
            This is useful if the action is added to a toolbar and
            users hover it to see what it does.
        """
        super(BasePluginWidget, self)._register_shortcut(
            qaction_or_qshortcut,
            context,
            name,
            add_shortcut_to_tip)

    def register_widget_shortcuts(self, widget):
        """
        Register shortcuts defined by a plugin's widget so they take
        effect when the plugin is focused.

        Parameters
        ----------
        widget: QWidget
            Widget to register shortcuts for.

        Notes
        -----
        The widget interface must have a method called
        `get_shortcut_data` for this to work. Please see
        `spyder/widgets/findreplace.py` for an example.
        """
        for qshortcut, context, name in widget.get_shortcut_data():
            self.register_shortcut(qshortcut, context, name)

    def get_color_scheme(self):
        """
        Get the current color scheme.

        Returns
        -------
        dict
            Dictionary with properties and colors of the color scheme
            used in the Editor.

        Notes
        -----
        This is useful to set the color scheme of all instances of
        CodeEditor used by the plugin.
        """
        return super(BasePluginWidget, self)._get_color_scheme()

    def switch_to_plugin(self):
        """
        Switch to this plugin.

        Notes
        -----
        This operation unmaximizes the current plugin (if any), raises
        this plugin to view (if it's hidden) and gives it focus (if
        possible).
        """
        super(BasePluginWidget, self)._switch_to_plugin()


class SpyderPluginWidget(SpyderPlugin, BasePluginWidget):
    """
    Spyder plugin widget class.

    All plugin widgets *must* inherit this class and reimplement its interface.
    """

    # ---------------------------- ATTRIBUTES ---------------------------------

    # Path for images relative to the plugin path
    # Status: Optional
    IMG_PATH = 'images'

    # Control the size of the fonts used in the plugin
    # relative to the fonts defined in Spyder
    # Status: Optional
    FONT_SIZE_DELTA = 0
    RICH_FONT_SIZE_DELTA = 0

    # Disable actions in Spyder main menus when the plugin
    # is not visible
    # Status: Optional
    DISABLE_ACTIONS_WHEN_HIDDEN = True

    # Shortcut to give focus to the plugin. In Spyder we try
    # to reserve shortcuts that start with Ctrl+Shift+... for
    # these actions
    # Status: Optional
    shortcut = None

    # ------------------------------ METHODS ----------------------------------

    def get_plugin_title(self):
        """
        Get plugin's title.

        Returns
        -------
        str
            Name of the plugin.
        """
        raise NotImplementedError

    def get_plugin_icon(self):
        """
        Get plugin's associated icon.

        Returns
        -------
        QIcon
            QIcon instance
        """
        return ima.icon('outline_explorer')

    def get_focus_widget(self):
        """
        Get the plugin widget to give focus to.

        Returns
        -------
        QWidget
            QWidget to give focus to.

        Notes
        -----
        This is applied when plugin's dockwidget is raised on top-level.
        """
        pass

    def closing_plugin(self, cancelable=False):
        """
        Perform actions before the main window is closed.

        Returns
        -------
        bool
            Whether the plugin may be closed immediately or not.

        Notes
        -----
        The returned value is ignored if *cancelable* is False.
        """
        return True

    def refresh_plugin(self):
        """
        Refresh plugin after it receives focus.

        Notes
        -----
        For instance, this is used to maintain in sync the Variable
        Explorer with the currently focused IPython console.
        """
        pass

    def get_plugin_actions(self):
        """
        Return a list of QAction's related to plugin.

        Notes
        -----
        These actions will be shown in the plugins Options menu (i.e.
        the hambuger menu on the right of each plugin).
        """
        return []

    def register_plugin(self):
        """
        Register plugin in Spyder's main window and connect it to other
        plugins.

        Notes
        -----
        Below is the minimal call necessary to register the plugin. If
        you override this method, please don't forget to make that call
        here too.
        """
        self.add_dockwidget()

    def on_first_registration(self):
        """
        Action to be performed on first plugin registration.

        Notes
        -----
        This is mostly used to tabify the plugin next to one of the
        core plugins, like this:

        self.tabify(self.main.variableexplorer)
        """
        raise NotImplementedError

    def apply_plugin_settings(self, options):
        """
        Determine what to do to apply configuration plugin settings.
        """
        pass

    def update_font(self):
        """
        This must be reimplemented by plugins that need to adjust
        their fonts.
        """
        pass

    def toggle_view(self, checked):
        """
        Toggle dockwidget's visibility when its entry is selected in
        the menu `View > Panes`.

        Parameters
        ----------
        checked: bool
            Is the entry in `View > Panes` checked or not?

        Notes
        -----
        Redefining this method can be useful to execute certain actions
        when the plugin is made visible. For an example, please see
        `spyder/plugins/ipythonconsole/plugin.py`
        """
        if not self.dockwidget:
            return
        if checked:
            self.dockwidget.show()
            self.dockwidget.raise_()
        else:
            self.dockwidget.hide()

    def set_ancestor(self, ancestor):
        """
        Needed to update the ancestor/parent of child widgets when undocking.
        """
        pass


##############################################################################
#
# New API: Migrate plugins one by one and test changes on the way.
#
##############################################################################
class Plugins:
    """
    Convenience class for accessing Spyder internal plugins.
    """
    All = "all"   # Wildcard to populate REQUIRES with all available plugins
    Appearance = 'appearance'
    Application = 'application'
    Breakpoints = 'breakpoints'
    Completions = 'completions'
    Console = 'internal_console'
    Editor = 'editor'
    Explorer = 'explorer'
    Find = 'find_in_files'
    Help = 'help'
    History = 'historylog'
    IPythonConsole = 'ipython_console'
    Layout = 'layout'
    MainInterpreter = 'main_interpreter'
    MainMenu = 'mainmenu'
    OnlineHelp = 'onlinehelp'
    OutlineExplorer = 'outline_explorer'
    Plots = 'plots'
    Preferences = 'preferences'
    Profiler = 'profiler'
    Projects = 'project_explorer'
    Pylint = 'pylint'
    Run = 'run'
    Shortcuts = 'shortcuts'
    StatusBar = 'statusbar'
    Toolbar = "toolbar"
    VariableExplorer = 'variable_explorer'
    WorkingDirectory = 'workingdir'


# --- Base API plugins
# ----------------------------------------------------------------------------
class SpyderPluginV2(QObject, SpyderActionMixin, SpyderConfigurationObserver):
    """
    A Spyder plugin to extend functionality without a dockable widget.

    If you want to create a plugin that adds a new pane, please use
    SpyderDockablePlugin.
    """

    # --- API: Mandatory attributes ------------------------------------------
    # ------------------------------------------------------------------------
    # Name of the plugin that will be used to refer to it.
    # This name must be unique and will only be loaded once.
    NAME = None

    # --- API: Optional attributes ------------------------------------------
    # ------------------------------------------------------------------------
    # List of required plugin dependencies.
    # Example: [Plugins.Plots, Plugins.IPythonConsole, ...].
    # These values are defined in the `Plugins` class present in this file.
    # If a plugin is using a widget from another plugin, that other
    # must be declared as a required dependency.
    REQUIRES = None

    # List of optional plugin dependencies.
    # Example: [Plugins.Plots, Plugins.IPythonConsole, ...].
    # These values are defined in the `Plugins` class present in this file.
    # A plugin might be performing actions when connectiong to other plugins,
    # but the main functionality of the plugin does not depend on other
    # plugins. For example, the Help plugin might render information from
    # the Editor or from the Console or from another source, but it does not
    # depend on either of those plugins.
    # Methods in the plugin that make use of optional plugins must check
    # existence before using those methods or applying signal connections.
    OPTIONAL = None

    # This must subclass a `PluginMainContainer` for non dockable plugins that
    # create a widget, like a status bar widget, a toolbar, a menu, etc.
    # For non dockable plugins that do not define widgets of any kind this can
    # be `None`, for example a plugin that only exposes a configuration page.
    CONTAINER_CLASS = None

    # Name of the configuration section that's going to be
    # used to record the plugin's permanent data in Spyder
    # config system (i.e. in spyder.ini)
    CONF_SECTION = None

    # Use a separate configuration file for the plugin.
    CONF_FILE = True

    # Define configuration defaults if using a separate file.
    # List of tuples, with the first item in the tuple being the section
    # name and the second item being the default options dictionary.
    #
    # CONF_DEFAULTS_EXAMPLE = [
    #     ('section-name', {'option-1': 'some-value',
    #                       'option-2': True,}),
    #     ('another-section-name', {'option-3': 'some-other-value',
    #                               'option-4': [1, 2, 3],}),
    # ]
    CONF_DEFAULTS = None

    # Define configuration version if using a separate file
    #
    # IMPORTANT NOTES:
    # 1. If you want to *change* the default value of a current option, you
    #    need to do a MINOR update in config version, e.g. from 3.0.0 to 3.1.0
    # 2. If you want to *remove* options that are no longer needed or if you
    #    want to *rename* options, then you need to do a MAJOR update in
    #    version, e.g. from 3.0.0 to 4.0.0
    # 3. You don't need to touch this value if you're just adding a new option
    CONF_VERSION = None

    # Widget to be used as entry in Spyder Preferences dialog.
    CONF_WIDGET_CLASS = None

    # Some plugins may add configuration options for other plugins.
    # Example:
    # ADDITIONAL_CONF_OPTIONS = {'section': <new value to add>}
    ADDITIONAL_CONF_OPTIONS = None

    # Define additional configurable options (via a tab) to
    # another's plugin configuration page. All configuration tabs should
    # inherit from `SpyderPreferencesTab`.
    # Example:
    # ADDITIONAL_CONF_TABS = {'plugin_name': [<SpyderPreferencesTab classes>]}
    ADDITIONAL_CONF_TABS = None

    # Path for images relative to the plugin path
    # A Python package can include one or several Spyder plugins. In this case
    # the package may be using images from a global folder outside the plugin
    # folder
    IMG_PATH = None

    # Control the font size relative to the global fonts defined in Spyder
    FONT_SIZE_DELTA = 0
    RICH_FONT_SIZE_DELTA = 0

    # Define context to store actions, toolbars, toolbuttons and menus.
    CONTEXT_NAME = None

    # --- API: Signals -------------------------------------------------------
    # ------------------------------------------------------------------------
    # Signals here are automatically connected by the Spyder main window and
    # connected to the the respective global actions defined on it.
    sig_free_memory_requested = Signal()
    """
    This signal can be emitted to request the main application to garbage
    collect deleted objects.
    """

    sig_quit_requested = Signal()
    """
    This signal can be emitted to request the main application to quit.
    """

    sig_restart_requested = Signal()
    """
    This signal can be emitted to request the main application to restart.
    """

    sig_status_message_requested = Signal(str, int)
    """
    This signal can be emitted to request the main application to display a
    message in the status bar.

    Parameters
    ----------
    message: str
        The actual message to display.
    timeout: int
        The timeout before the message disappears.
    """

    sig_redirect_stdio_requested = Signal(bool)
    """
    This signal can be emitted to request the main application to redirect
    standard output/error when using Open/Save/Browse dialogs within widgets.

    Parameters
    ----------
    enable: bool
        Enable/Disable standard input/output redirection.
    """

    sig_exception_occurred = Signal(dict)
    """
    This signal can be emitted to report an exception from any plugin.

    Parameters
    ----------
    error_data: dict
        The dictionary containing error data. The expected keys are:
        >>> error_data= {
            "text": str,
            "is_traceback": bool,
            "repo": str,
            "title": str,
            "label": str,
            "steps": str,
        }

    Notes
    -----
    The `is_traceback` key indicates if `text` contains plain text or a
    Python error traceback.

    The `title` and `repo` keys indicate how the error data should
    customize the report dialog and Github error submission.

    The `label` and `steps` keys allow customizing the content of the
    error dialog.

    This signal is automatically connected to the main container/widget.
    """

    # --- Private attributes -------------------------------------------------
    # ------------------------------------------------------------------------
    # Define configuration name map for plugin to split configuration
    # among several files. See spyder/config/main.py
    _CONF_NAME_MAP = None

    def __init__(self, parent, configuration=None):
        super().__init__(parent)

        self._main = parent
        self._widget = None
        self._conf = configuration
        self._plugin_path = os.path.dirname(inspect.getfile(self.__class__))
        self._container = None
        self._added_toolbars = OrderedDict()
        self._actions = {}
        self.is_compatible = None
        self.is_registered = None
        self.main = parent

        # Attribute used to access the action, toolbar, toolbutton and menu
        # registries
        self.PLUGIN_NAME = self.NAME

        if self.CONTAINER_CLASS is not None:
            self._container = container = self.CONTAINER_CLASS(
                name=self.NAME,
                plugin=self,
                parent=parent
            )

            if isinstance(container, SpyderWidgetMixin):
                container.setup()
                container.update_actions()

            if isinstance(container, PluginMainContainer):
                # Default signals to connect in main container or main widget.
                container.sig_exception_occurred.connect(
                    self.sig_exception_occurred)
                container.sig_free_memory_requested.connect(
                    self.sig_free_memory_requested)
                container.sig_quit_requested.connect(
                    self.sig_quit_requested)
                container.sig_redirect_stdio_requested.connect(
                    self.sig_redirect_stdio_requested)
                container.sig_restart_requested.connect(
                    self.sig_restart_requested)

            self.after_container_creation()

            if hasattr(container, '_setup'):
                container._setup()

        # Load the custom images of the plugin
        if self.IMG_PATH:
            plugin_path = osp.join(self.get_path(), self.IMG_PATH)
            IMAGE_PATH_MANAGER.add_image_path(plugin_path)

    # --- Private methods ----------------------------------------------------
    # ------------------------------------------------------------------------
    def _register(self):
        """
        Setup and register plugin in Spyder's main window and connect it to
        other plugins.
        """
        # Checks
        # --------------------------------------------------------------------
        if self.NAME is None:
            raise SpyderAPIError('A Spyder Plugin must define a `NAME`!')

        if self.NAME in self._main._PLUGINS:
            raise SpyderAPIError(
                'A Spyder Plugin with NAME="{}" already exists!'.format(
                    self.NAME))

        # Setup configuration
        # --------------------------------------------------------------------
        if self._conf is not None:
            self._conf.register_plugin(self)

        # Signals
        # --------------------------------------------------------------------
        self.is_registered = True

        self.update_font()

    def _unregister(self):
        """
        Disconnect signals and clean up the plugin to be able to stop it while
        Spyder is running.
        """

        if self._conf is not None:
            self._conf.unregister_plugin()

        self._container = None
        self.is_compatible = None
        self.is_registered = False

    # --- API: available methods ---------------------------------------------
    # ------------------------------------------------------------------------
    def get_path(self):
        """
        Return the plugin's system path.
        """
        return self._plugin_path

    def get_container(self):
        """
        Return the plugin main container.
        """
        return self._container

    def get_configuration(self):
        """
        Return the Spyder configuration object.
        """
        return self._conf

    def get_main(self):
        """
        Return the Spyder main window..
        """
        return self._main

    def get_plugin(self, plugin_name):
        """
        Return a plugin instance by providing the plugin's NAME.
        """
        # Ensure that this plugin has the plugin corresponding to
        # `plugin_name` listed as required or optional.
        requires = self.REQUIRES or []
        optional = self.OPTIONAL or []
        deps = []

        for dependency in requires + optional:
            deps.append(dependency)

        PLUGINS = self._main._PLUGINS
        if plugin_name in deps:
            for name, plugin_instance in PLUGINS.items():
                if name == plugin_name and name in deps:
                    return plugin_instance
            else:
                if plugin_name in requires:
                    raise SpyderAPIError(
                        'Required Plugin "{}" not found!'.format(plugin_name))
                else:
                    return None
        else:
            raise SpyderAPIError(
                'Plugin "{}" not part of REQUIRES or '
                'OPTIONAL requirements!'.format(plugin_name)
            )

    def get_dockable_plugins(self):
        """
        Return a list of the required plugin instances.

        Only required plugins that extend SpyderDockablePlugin are returned.
        """
        requires = self.REQUIRES or []
        dockable_plugins_required = []
        PLUGINS = self._main._PLUGINS
        for name, plugin_instance in PLUGINS.items():
            if name in requires and isinstance(
                    plugin_instance,
                    (SpyderDockablePlugin, SpyderPluginWidget)):
                dockable_plugins_required.append(plugin_instance)
        return dockable_plugins_required

    def get_conf(self, option, default=NoDefault, section=None):
        """
        Get an option from Spyder configuration system.

        Parameters
        ----------
        option: str
            Name of the option to get its value from.
        default: bool, int, str, tuple, list, dict, NoDefault
            Value to get from the configuration system, passed as a
            Python object.
        section: str
            Section in the configuration system, e.g. `shortcuts`.

        Returns
        -------
        bool, int, str, tuple, list, dict
            Value associated with `option`.
        """
        if self._conf is not None:
            section = self.CONF_SECTION if section is None else section
            if section is None:
                raise SpyderAPIError(
                    'A spyder plugin must define a `CONF_SECTION` class '
                    'attribute!'
                )

            return self._conf.get(section, option, default)

    @Slot(str, object)
    @Slot(str, object, str)
    def set_conf(self, option, value, section=None,
                 recursive_notification=True):
        """
        Set an option in Spyder configuration system.

        Parameters
        ----------
        option: str
            Name of the option (e.g. 'case_sensitive')
        value: bool, int, str, tuple, list, dict
            Value to save in the configuration system, passed as a
            Python object.
        section: str
            Section in the configuration system, e.g. `shortcuts`.
        recursive_notification: bool
            If True, all objects that observe all changes on the
            configuration section and objects that observe partial tuple paths
            are notified. For example if the option `opt` of section `sec`
            changes, then the observers for section `sec` are notified.
            Likewise, if the option `(a, b, c)` changes, then observers for
            `(a, b, c)`, `(a, b)` and a are notified as well.
        """
        if self._conf is not None:
            section = self.CONF_SECTION if section is None else section
            if section is None:
                raise SpyderAPIError(
                    'A spyder plugin must define a `CONF_SECTION` class '
                    'attribute!'
                )

            self._conf.set(section, option, value,
                           recursive_notification=recursive_notification)
            self.apply_conf({option}, False)

    def remove_conf(self, option, section=None):
        """
        Delete an option in the Spyder configuration system.

        Parameters
        ----------
        option: Union[str, Tuple[str, ...]]
            Name of the option, either a string or a tuple of strings.
        section: str
            Section in the configuration system.
        """
        if self._conf is not None:
            section = self.CONF_SECTION if section is None else section
            if section is None:
                raise SpyderAPIError(
                    'A spyder plugin must define a `CONF_SECTION` class '
                    'attribute!'
                )

            self._conf.remove_option(section, option)
            self.apply_conf({option}, False)

    def apply_conf(self, options_set, notify=True):
        """
        Apply `options_set` to this plugin's widget.
        """
        if self._conf is not None and options_set:
            container = self.get_container()
            if notify:
                self.after_configuration_update(list(options_set))

    @Slot(str)
    @Slot(str, int)
    def show_status_message(self, message, timeout=0):
        """
        Show message in status bar.

        Parameters
        ----------
        message: str
            Message to display in the status bar.
        timeout: int
            Amount of time to display the message.
        """
        self.sig_status_message_requested.emit(message, timeout)

    def before_long_process(self, message):
        """
        Show a message in main window's status bar and change the mouse
        pointer to Qt.WaitCursor when starting a long process.

        Parameters
        ----------
        message: str
            Message to show in the status bar when the long process starts.
        """
        if message:
            self.show_status_message(message)

        QApplication.setOverrideCursor(QCursor(Qt.WaitCursor))
        QApplication.processEvents()

    def after_long_process(self, message=""):
        """
        Clear main window's status bar after a long process and restore
        mouse pointer to the OS deault.

        Parameters
        ----------
        message: str
            Message to show in the status bar when the long process finishes.
        """
        QApplication.restoreOverrideCursor()
        self.show_status_message(message, timeout=2000)
        QApplication.processEvents()

    def get_color_scheme(self):
        """
        Get the current color scheme.

        Returns
        -------
        dict
            Dictionary with properties and colors of the color scheme
            used in the Editor.

        Notes
        -----
        This is useful to set the color scheme of all instances of
        CodeEditor used by the plugin.
        """
        if self._conf is not None:
            return get_color_scheme(self._conf.get('appearance', 'selected'))

    @staticmethod
    def create_icon(name):
        """
        Provide icons from the theme and icon manager.
        """
        return ima.icon(name)

    @classmethod
    def get_font(cls, rich_text=False):
        """
        Return plain or rich text font used in Spyder.

        Parameters
        ----------
        rich_text: bool
            Return rich text font (i.e. the one used in the Help pane)
            or plain text one (i.e. the one used in the Editor).

        Returns
        -------
        QFont
            QFont object to be passed to other Qt widgets.

        Notes
        -----
        All plugins in Spyder use the same, global font. This is a convenience
        method in case some plugins want to use a delta size based on the
        default one. That can be controlled by using FONT_SIZE_DELTA or
        RICH_FONT_SIZE_DELTA (declared in `SpyderPlugin`).
        """
        if rich_text:
            option = 'rich_font'
            font_size_delta = cls.RICH_FONT_SIZE_DELTA
        else:
            option = 'font'
            font_size_delta = cls.FONT_SIZE_DELTA

        return get_font(option=option, font_size_delta=font_size_delta)

    # --- API: Mandatory methods to define -----------------------------------
    # ------------------------------------------------------------------------
    def get_name(self):
        """
        Return the plugin localized name.

        Returns
        -------
        str
            Localized name of the plugin.

        Notes
        -----
        This is a method to be able to update localization without a restart.
        """
        raise NotImplementedError('A plugin name must be defined!')

    def get_description(self):
        """
        Return the plugin localized description.

        Returns
        -------
        str
            Localized description of the plugin.

        Notes
        -----
        This is a method to be able to update localization without a restart.
        """
        raise NotImplementedError('A plugin description must be defined!')

    def get_icon(self):
        """
        Return the plugin associated icon.

        Returns
        -------
        QIcon
            QIcon instance
        """
        raise NotImplementedError('A plugin icon must be defined!')

    def register(self):
        """
        Setup and register plugin in Spyder's main window and connect it to
        other plugins.
        """
        raise NotImplementedError('Must define a register method!')

    # --- API: Optional methods to override ----------------------------------
    # ------------------------------------------------------------------------
    def unregister(self):
        """
        Disconnect signals and clean up the plugin to be able to stop it while
        Spyder is running.
        """
        pass

    @staticmethod
    def check_compatibility():
        """
        This method can be reimplemented to check compatibility of a plugin
        with the user's current environment.

        Returns
        -------
        (bool, str)
            The first value tells Spyder if the plugin has passed the
            compatibility test defined in this method. The second value
            is a message that must explain users why the plugin was
            found to be incompatible (e.g. 'This plugin does not work
            with PyQt4'). It will be shown at startup in a QMessageBox.
        """
        valid = True
        message = ''  # Note: Remember to use _('') to localize the string
        return valid, message

    def on_first_registration(self):
        """
        Actions to be performed the first time the plugin is started.

        It can also be used to perform actions that are needed only the
        first time this is loaded after installation.

        This method is called after the main window is visible.
        """
        pass

    def before_mainwindow_visible(self):
        """
        Actions to be performed after setup but before the main window's has
        been shown.
        """
        pass

    def on_mainwindow_visible(self):
        """
        Actions to be performed after the main window's has been shown.
        """
        pass

    def on_close(self, cancelable=False):
        """
        Perform actions before the main window is closed.

        Returns
        -------
        bool
            Whether the plugin may be closed immediately or not.

        Notes
        -----
        The returned value is ignored if *cancelable* is False.
        """
        return True

    def update_font(self):
        """
        This must be reimplemented by plugins that need to adjust their fonts.

        The following plugins illustrate the usage of this method:
          * spyder/plugins/help/plugin.py
          * spyder/plugins/onlinehelp/plugin.py
        """
        pass

    def update_style(self):
        """
        This must be reimplemented by plugins that need to adjust their style.

        Changing from the dark to the light interface theme might
        require specific styles or stylesheets to be applied. When
        the theme is changed by the user through our Preferences,
        this method will be called for all plugins.
        """
        pass

    def after_container_creation(self):
        """
        Perform necessary operations before setting up the container.

        This must be reimplemented by plugins whose containers emit signals in
        on_option_update that need to be connected before applying those
        options to our config system.
        """
        pass

    def after_configuration_update(self, options: List[Union[str, tuple]]):
        """
        Perform additional operations after updating the plugin configuration
        values.

        This can be implemented by plugins that do not have a container and
        need to act on configuration updates.

        Parameters
        ----------
        options: List[Union[str, tuple]]
            A list that contains the options that were updated.
        """
        pass


class SpyderDockablePlugin(SpyderPluginV2):
    """
    A Spyder plugin to enhance functionality with a dockable widget.
    """
    # --- API: Mandatory attributes ------------------------------------------
    # ------------------------------------------------------------------------
    # This is the main widget of the dockable plugin.
    # It needs to be a subclass of PluginMainWidget.
    WIDGET_CLASS = None

    # --- API: Optional attributes -------------------------------------------
    # ------------------------------------------------------------------------
    # Define a list of plugins next to which we want to to tabify this plugin.
    # Example: ['Plugins.Editor']
    TABIFY = []

    # Disable actions in Spyder main menus when the plugin is not visible
    DISABLE_ACTIONS_WHEN_HIDDEN = True

    # Raise and focus on switch to plugin calls.
    # If False, the widget will be raised but focus will not be given until
    # the action to switch is called a second time.
    RAISE_AND_FOCUS = False

    # --- API: Available signals ---------------------------------------------
    # ------------------------------------------------------------------------
    sig_focus_changed = Signal()
    """
    This signal is emitted to inform the focus of this plugin has changed.
    """

    sig_toggle_view_changed = Signal(bool)
    """
    This action is emitted to inform the visibility of a dockable plugin
    has changed.

    This is triggered by checking/unchecking the entry for a pane in the
    `View > Panes` menu.

    Parameters
    ----------
    visible: bool
        New visibility of the dockwidget.
    """

    sig_switch_to_plugin_requested = Signal(object, bool)
    """
    This signal can be emitted to inform the main window that this plugin
    requested to be displayed.

    Notes
    -----
    This is automatically connected to main container/widget at plugin's
    registration.
    """

    sig_update_ancestor_requested = Signal()
    """
    This signal is emitted to inform the main window that a child widget
    needs its ancestor to be updated.
    """

    # --- Private methods ----------------------------------------------------
    # ------------------------------------------------------------------------
    def __init__(self, parent, configuration):
        if not issubclass(self.WIDGET_CLASS, PluginMainWidget):
            raise SpyderAPIError(
                'A SpyderDockablePlugin must define a valid WIDGET_CLASS '
                'attribute!')

        self.CONTAINER_CLASS = self.WIDGET_CLASS
        super().__init__(parent, configuration=configuration)

        # Defined on mainwindow.py
        self._shortcut = None

        # Widget setup
        # --------------------------------------------------------------------
        self._widget = self._container
        widget = self._widget
        if widget is None:
            raise SpyderAPIError(
                'A dockable plugin must define a WIDGET_CLASS!')

        if not isinstance(widget, PluginMainWidget):
            raise SpyderAPIError(
                'The WIDGET_CLASS of a dockable plugin must be a subclass of '
                'PluginMainWidget!')

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
            self.sig_update_ancestor_requested)

    # --- API: available methods ---------------------------------------------
    # ------------------------------------------------------------------------
    def before_long_process(self, message):
        """
        Show a message in main window's status bar, change the mouse pointer
        to Qt.WaitCursor and start spinner when starting a long process.

        Parameters
        ----------
        message: str
            Message to show in the status bar when the long process starts.
        """
        self.get_widget().start_spinner()
        super().before_long_process(message)

    def after_long_process(self, message=""):
        """
        Clear main window's status bar after a long process, restore mouse
        pointer to the OS deault and stop spinner.

        Parameters
        ----------
        message: str
            Message to show in the status bar when the long process finishes.
        """
        super().after_long_process(message)
        self.get_widget().stop_spinner()

    def get_widget(self):
        """
        Return the plugin main widget.
        """
        if self._widget is None:
            raise SpyderAPIError('Dockable Plugin must have a WIDGET_CLASS!')

        return self._widget

    def update_title(self):
        """
        Update plugin title, i.e. dockwidget or window title.
        """
        self.get_widget().update_title()

    def update_margins(self, margin):
        """
        Update margins of main widget inside dockable plugin.
        """
        self.get_widget().update_margins(margin)

    def switch_to_plugin(self, force_focus=False):
        """
        Switch to plugin and define if focus should be given or not.
        """
        self.sig_switch_to_plugin_requested.emit(self, force_focus)

    def set_ancestor(self, ancestor_widget):
        """
        Update the ancestor/parent of child widgets when undocking.
        """
        self.get_widget().set_ancestor(ancestor_widget)

    # --- Convenience methods from the widget exposed on the plugin
    # ------------------------------------------------------------------------
    @property
    def dockwidget(self):
        return self.get_widget().dockwidget

    @property
    def options_menu(self):
        return self.get_widget().get_options_menu()

    @property
    def toggle_view_action(self):
        return self.get_widget().toggle_view_action

    def create_dockwidget(self, mainwindow):
        return self.get_widget().create_dockwidget(mainwindow)

    def close_window(self):
        self.get_widget().close_window()

    def change_visibility(self, state, force_focus=False):
        self.get_widget().change_visibility(state, force_focus)

    def toggle_view(self, value):
        self.get_widget().toggle_view(value)
