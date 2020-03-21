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

1. SpyderPluginV2 is a plugin that does not create a new dock/pane on Spyder
   main window. Note: SpyderPluginV2 will be renamed to SpyderPlugin once the
   migration to the new API is finished

2. SpyderDockablePlugin is a plugin that does create a new dock/pane on Spyder
   main window.
"""

# Standard library imports
from collections import OrderedDict
import inspect
import os

# Third party imports
from qtpy.QtCore import QObject, Qt, Signal, Slot, QSize
from qtpy.QtGui import QCursor
from qtpy.QtWidgets import QApplication, QWidget

# Local imports
from spyder.api.menus import ApplicationMenus
from spyder.api.mixins import SpyderActionMixin, SpyderOptionMixin
from spyder.api.toolbars import ApplicationToolBars
from spyder.api.translations import get_translation
from spyder.api.widgets import (ApplicationMenu, ApplicationToolBar,
                                PluginMainWidget)
from spyder.config.gui import get_color_scheme, get_font
from spyder.config.manager import CONF  # TODO: Remove after migration
from spyder.config.user import NoDefault
from spyder.plugins.base import BasePluginMixin, BasePluginWidgetMixin
from spyder.py3compat import configparser as cp
from spyder.utils import icon_manager as ima
from spyder.utils.qthelpers import create_action

# Localization
_ = get_translation('spyder')


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
    def set_option(self, option, value, section=None):
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
        super(BasePlugin, self)._set_option(option, value, section=section)

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
# New API, to migrate plugins one by one and make it easier to test changes
#
##############################################################################
class Plugins:
    """
    Convenience for accessing Spyder internal plugins.
    """
    Breakpoints = 'breakpoints'
    CodeAnalysis = 'code_analysis'
    CodeCompletion = 'code_completion'
    KiteCompletion = 'kite'
    FallBackCompletion = 'fallback'
    LanguageServerCompletion = 'lsp'
    Console = 'internal_console'
    Editor = 'editor'
    Explorer = 'explorer'
    Find = 'find_in_files'
    Help = 'help'
    History = 'history'
    IPythonConsole = 'ipython_console'
    OnlineHelp = 'online_help'
    OutlineExplorer = 'outline_explorer'
    Plots = 'plots'
    Profiler = 'profiler'
    Projects = 'project_explorer'
    Pylint = 'pylint'
    VariableExplorer = 'variable_explorer'
    WorkingDirectory = 'workingdir'


class SpyderAPIError(Exception):
    pass


# --- Base API plugins
# ----------------------------------------------------------------------------
class SpyderPluginV2(QObject, SpyderActionMixin, SpyderOptionMixin):
    """
    A Spyder plugin to enhance functionality without a dockable widget.

    If you want to create a plugin that adds a new panel, use
    SpyderDockableWidget.
    """

    # --- API: Mandatory attributes ------------------------------------------
    # ------------------------------------------------------------------------
    # Name of the plugin that will be used to refer plugins.
    # This name must be unique and will only be loaded once.
    NAME = None

    # --- API: Optional attributes ------------------------------------------
    # ------------------------------------------------------------------------
    # List of required plugin dependencies names
    # Example: [Plugin.Plots, Plugin.IPythonConsole, ...].
    # These values are from the Plugins enumeration
    # A plugin might be using a widget from another plugin, in that case that
    # other plugin is a required dependency.
    REQUIRES = None

    # List of optional plugin dependencies names
    # Example: [Plugin.Plots, Plugin.IPythonConsole, ...].
    # These values are from the Plugins enumeration
    # A plugin might be performing actions when connectiong to other plugins,
    # but the main functionality of the plugin does not depend on other
    # plugins. For example, the Help plugin might render information from
    # the Editor or from the Console or from another source, but it does not
    # depend on either of those plugins.
    # Methods in the plugin that make use of optional plugins must check
    # existence before ussing methods or applying signal connections
    OPTIONAL = None

    # This is a qobject class to store behavior and actions. Subclass
    # SpyderWigdetMixin
    # For example: The Working Directory plugin creates a New widget:
    # a Toolbar. In those cases it makes sense to put that widget here.
    # If a Plugin is creating "several" non dockable widgets: status bar
    # widgets, menus, a new toolbar; those widgets could (or should be
    # grouped) within some "parent" qobject class.
    WIDGET_CLASS = None

    # Name of the configuration section that's going to be
    # used to record the plugin's permanent data in Spyder
    # config system (i.e. in spyder.ini)
    CONF_SECTION = None

    # Use separate configuration file for the plugin
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

    # Widget to be used as entry in Spyder Preferences dialog
    CONF_WIDGET_CLASS = None

    # Some widgets may use configuration options from other plguins.
    # This variable helps translate CONF to options when the option comes
    # from another plugin.
    # Example:
    # CONF_FROM_OPTIONS = {'widget_option': ('section', 'option'), ...}
    CONF_FROM_OPTIONS = None

    # Path for images relative to the plugin path
    # A Python package can include one or several Spyder plugins. In this case
    # the package may be using images from a global folder outside the plugin
    # folder
    IMG_PATH = 'images'

    # Control the font size relative to the global fonts defined in Spyder
    FONT_SIZE_DELTA = 0
    RICH_FONT_SIZE_DELTA = 0

    # --- API: Signals -------------------------------------------------------
    # ------------------------------------------------------------------------

    # Use this signal to inform another plugin that configuration changed.
    sig_free_memory_requested = Signal()
    sig_option_changed = Signal(str, object)
    sig_quit_requested = Signal()
    sig_restart_requested = Signal()
    sig_status_message_requested = Signal(str, int)
    sig_redirect_stdio_requested = Signal(bool)
    sig_focus_changed = Signal()

    # --- Private attributes -------------------------------------------------
    # ------------------------------------------------------------------------
    # Define configuration name map for plugin to split configuration
    # among several files. See spyder/config/main.py
    _CONF_NAME_MAP = None

    def __init__(self, parent, configuration=None):
        super().__init__(parent)

        self._main = parent
        self._conf = configuration
        self._plugin_path = os.path.dirname(inspect.getfile(self.__class__))
        self.is_compatible = None
        self.is_registered = None
        self.main = parent
        self._actions = {}

        if self.WIDGET_CLASS is not None:
            options = self.options_from_conf(self.WIDGET_CLASS.DEFAULT_OPTIONS)
            self._widget = widget = self.WIDGET_CLASS(
                name=self.NAME,
                plugin=self,
                parent=parent,
                options=options,
            )

            # Widget setup
            # ----------------------------------------------------------------
            try:
                widget._setup(options=options)
            except AttributeError:
                pass

            widget.setup(options=options)
            widget.update_actions()

            # Set options without emitting a signal
            widget.change_options(options=options)

            # Default Signals
            # --------------------------------------------------------------------
            widget.sig_option_changed.connect(self.sig_option_changed)
            widget.sig_redirect_stdio_requested.connect(
                self.sig_redirect_stdio_requested)

    # --- Private methods ---------------------------------------------
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
        self.sig_option_changed.connect(self.set_conf_option)
        self.is_registered = True

    def _unregister(self):
        """
        Disconnect signals and clean up the plugin to be able to stop it while
        Spyder is running.
        """
        try:
            self.sig_option_changed.disconnect()
        except TypeError:
            pass

        if self._conf is not None:
            self._conf.unregister_plugin()

        self._widget = None
        self.is_compatible = None
        self.is_registered = False

    # --- API: available methods ---------------------------------------------
    # ------------------------------------------------------------------------
    def get_path(self):
        """
        Return the plugin's system path.
        """
        return self._plugin_path

    # Could be a property, but this mixes the C++/Python ideas, so maybe
    # getters are cleaner, even if more verbose.
    def get_widget(self):
        """
        Return the plugin widget.
        """
        return self._widget

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
        # Ensure that the plugin class had the plugin listed as REQUIRES
        # or OPTIONAL
        requires = self.REQUIRES or []
        optional = self.OPTIONAL or []
        deps = []

        for dependency in requires + optional:
            deps.append(dependency)

        PLUGINS = self._main._PLUGINS
        if plugin_name in PLUGINS:
            for name, plugin_instance in PLUGINS.items():
                if name == plugin_name and name in deps:
                    return plugin_instance
            else:
                raise SpyderAPIError(
                    'Plugin "{}" not found!'.format(plugin_name))
        else:
            raise SpyderAPIError(
                'Plugin "{}" not part of REQUIRES or '
                'OPTIONAL requirements!'.format(plugin_name)
            )

    def options_from_conf(self, options):
        """
        Get the options from the configurations files.

        Returns
        -------
        Dictionary of {str: object}
        """
        conf_from_options = self.CONF_FROM_OPTIONS or {}
        config_options = {}
        if self._conf is not None:
            # options could be a list, or a dictionary
            for option in options:
                if option in conf_from_options:
                    section, new_option = conf_from_options[option]
                else:
                    section, new_option = (self.CONF_SECTION, option)

                try:
                    config_options[option] = self.get_conf_option(
                        new_option,
                        section=section,
                    )
                except (cp.NoSectionError, cp.NoOptionError):
                    # TODO: Remove when migration is done, move to logger.
                    #       Needed to check how the options API needs to cover
                    #       options from all plugins
                    print('\nspyder.api.plugins.options_from_conf\n'
                          'Warning: option "{}" not found in section "{}" '
                          'of configuration!'.format(option, self.NAME))

                    # Try to use the default if it was a dictionary as some
                    # options might not have a default value in the CONF
                    if isinstance(options, (dict, OrderedDict)):
                        try:
                            config_options[option] = options[option]
                        except Exception:
                            pass

        return config_options

    def get_conf_option(self, option, default=NoDefault, section=None):
        """
        Get an option from Spyder configuration files.

        Parameters
        ----------
        option: str
            Name of the option to get its value from.
        default: bool, int, str, tuple, list, dict, NoDefault
            Value to save in configuration file, passed as a Python
            object.
        section: str
            TODO:

        Returns
        -------
        bool, int, str, tuple, list, dict
            Value associated with `option`.
        """
        if self._conf is not None:
            section = self.CONF_SECTION if section is None else section
            return self._conf.get(section, option, default)

    @Slot(str, object)
    @Slot(str, object, str)
    def set_conf_option(self, option, value, section=None):
        """
        Set an option in Spyder configuration files.

        Parameters
        ----------
        option: str
            Name of the option (e.g. 'case_sensitive')
        value: bool, int, str, tuple, list, dict
            Value to save in configuration file, passed as a Python
            object.
        section: str
            TODO

        Notes
        -----
        * Use sig_option_changed to call this method from widgets of the
          same or another plugin.
        * CONF_SECTION needs to be defined for this to work.
        """
        if self._conf is not None:
            section = self.CONF_SECTION if section is None else section
            self._conf.set(section, str(option), value)

    def apply_conf(self, options_set):
        """
        Determine what to do to apply configuration of plugin settings.
        """
        if self._conf is not None:
            widget = self.get_widget()
            options = self.options_from_conf(options_set)
            new_options = self.options_from_keys(
                options,
                widget.DEFAULT_OPTIONS,
            )
            # By using change_options we will not emit sig_option_changed
            # when setting the options
            # This will also cascade on all children
            widget.change_options(new_options)

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

    def before_long_process(self, message):  # Old name: starting_long_process
        """
        Show a message in main window's status bar and changes the
        mouse to Qt.WaitCursor when starting a long process.

        Parameters
        ----------
        message: str
            Message to show in the status bar when the long
            process starts.
        """
        if self.get_widget() is not None:
            self.get_widget().start_spinner()

        if message:
            self.show_status_message(message)

        QApplication.setOverrideCursor(QCursor(Qt.WaitCursor))
        QApplication.processEvents()

    def after_long_process(self, message=""):  # Old name: ending_long_process
        """
        Clear main window's status bar after a long process and restore
        mouse to the OS deault.

        Parameters
        ----------
        message: str
            Message to show in the status bar when the long process
            finishes.
        """
        QApplication.restoreOverrideCursor()
        self.show_status_message(message, timeout=2000)
        QApplication.processEvents()

        if self.get_widget() is not None:
            self.get_widget().stop_spinner()

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
    def create_icon(name, path=None):
        """
        Provide icons from the theme and icon manager.
        """
        return ima.icon(name, icon_path=path)

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
        QFont:
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

    def get_actions(self):  # Old name: get_plugin_actions
        """
        Return a dictionary of actions exposed by the plugin and child widgets.
        Return all actions defined by the Spyder plugin widget.

        Notes
        -----
        1. Actions should be created once. Creating new actions on menu popup
           is *highly* discouraged.
        2. To create an action the user must user this method on
           SpyderWidgetMixin.
        3. The PluginMainWidget will collect any actions defined in subwidgets
           (if defined) and expose them in the get_actions method at the plugin
           level.
        4. Any action created this way is now exposed as a possible shortcut
           automatically without manual shortcut registration.
           If an option is found in the config then it is assigned otherwise
           is left with an empty shortcut.
        5. There is no need to override this method.
        """
        actions = self.get_widget().get_actions()
        actions.update(super().get_actions())
        return actions

    def get_action(self, name):
        """
        Return action defined in any of the child widgets by name.
        """
        actions = self.get_widget().get_actions()
        if name in actions:
            return actions[name]
        else:
            raise SpyderAPIError('Action "{0}" not found! Available '
                                 'actions are: {1}'.format(name, actions))

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
        This is a method to be able to update localization without a restart
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
        This is a method to be able to update localization without a restart
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

    def register(self):  # Old name: register_plugin
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
        message = ''  # Note: Remeber to use _('') to localize the string
        return valid, message

    def on_first_registration(self):
        """
        Action to be performed on the first time the plugin is started.

        Or to perform actions that are needed only the first time this is
        installed.

        This method is called after the main window is visible.
        """
        pass

    # FIXME: Better name
    def on_visible(self):
        """
        Actions to be performed after the main window's has been shown.
        """
        pass

    # Old name: closing_plugin
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

        FIXME: Give examples of core plugins that use this.
        """
        pass

    def update_style(self):
        """
        This must be reimplemented by plugins that need to adjust their style.

        Changing from dark to light themes, might require specific styles or
        stylesheets. When the global application theme of Spyder changes
        when using the Preferences, this method will be called for all
        plugins.
        """
        pass

    # --- CoreUI Plugin: This methods need to go in the coreui plugin so that
    #     application menu/toolbar/status bar handling is managed by that
    #     plugin
    # ------------------------------------------------------------------------
    def create_application_menu(self, name):
        """
        Create a Spyder application menu with `name` and return it.
        """
        app_menus = getattr(self, '_application_menus', None)
        if app_menus is None:
            self._application_menus = {}

        menu = ApplicationMenu(self._main)
        self._application_menus[name] = menu

        return menu

    def get_application_menu(self, name):
        """
        Return an application menu by name.
        """
        # TODO: Temporal solution while API for managing app menus is created
        self._main.file_menu.name = ApplicationMenus.File
        self._main.edit_menu.name = ApplicationMenus.Edit
        self._main.search_menu.name = ApplicationMenus.Search
        self._main.source_menu.name = ApplicationMenus.Source
        self._main.run_menu.name = ApplicationMenus.Run
        self._main.debug_menu.name = ApplicationMenus.Debug
        self._main.consoles_menu.name = ApplicationMenus.Consoles
        self._main.projects_menu.name = ApplicationMenus.Projects
        self._main.tools_menu.name = ApplicationMenus.Tools
        self._main.view_menu.name = ApplicationMenus.View
        self._main.help_menu.name = ApplicationMenus.Help

        app_menus = {
            ApplicationMenus.File: self._main.file_menu,
            ApplicationMenus.Edit: self._main.edit_menu,
            ApplicationMenus.Search: self._main.search_menu,
            ApplicationMenus.Source: self._main.source_menu,
            ApplicationMenus.Run: self._main.run_menu,
            ApplicationMenus.Debug: self._main.debug_menu,
            ApplicationMenus.Consoles: self._main.consoles_menu,
            ApplicationMenus.Projects: self._main.projects_menu,
            ApplicationMenus.Tools: self._main.tools_menu,
            ApplicationMenus.View: self._main.view_menu,
            ApplicationMenus.Help: self._main.help_menu,
        }

        if name in app_menus:
            return app_menus[name]
        else:
            raise Exception('Application menu "{0}" not found! Available '
                            'menus are: {1}'.format(name,
                                                    list(app_menus.keys())))

    def get_application_toolbar(self, name):
        """
        Return an application toolbar by name.
        """
        # TODO: Temporal solution while API for managing app menus is created
        app_toolbars = {
            ApplicationToolBars.File: self._main.file_toolbar,
            ApplicationToolBars.Run: self._main.run_toolbar,
            ApplicationToolBars.Debug: self._main.debug_toolbar,
            ApplicationToolBars.Main: self._main.main_toolbar,
            ApplicationToolBars.Search: self._main.search_toolbar,
            ApplicationToolBars.Edit: self._main.edit_toolbar,
            ApplicationToolBars.Source: self._main.source_toolbar,
        }
        if name in app_toolbars:
            return app_toolbars[name]
        else:
            raise SpyderAPIError(
                'Application toolbar "{0}" not found! '
                'Available toolbars are: {1}'.format(
                    name,
                    list(app_toolbars.keys())
                )
            )

    def add_item_to_application_menu(self, item, menu, section=None,
                                     before=None):
        """
        TODO: Menu could be a name or an instance? this could avoid calling
        get application menu.
        """
        # Enable when new API is activated
        # Check that menu is an ApplicationMenu
        # if not isinstance(menu, ApplicationMenu):
        #     raise SpyderAPIError('Not an ApplicationMenu!')

        # TODO: For now just add to the bottom
        #       Temporal solution while API for managing app menus is created
        app_menu_actions = {
            ApplicationMenus.File: self._main.file_menu_actions,
            ApplicationMenus.Edit: self._main.edit_menu_actions,
            ApplicationMenus.Search: self._main.search_menu_actions,
            ApplicationMenus.Source: self._main.source_menu_actions,
            ApplicationMenus.Run: self._main.run_menu_actions,
            ApplicationMenus.Debug: self._main.debug_menu_actions,
            ApplicationMenus.Consoles: self._main.consoles_menu_actions,
            ApplicationMenus.Projects: self._main.projects_menu_actions,
            ApplicationMenus.Tools: self._main.tools_menu_actions,
            # ApplicationMenus.View: self._main.view_menu_actions,
            ApplicationMenus.Help: self._main.help_menu_actions,
        }
        actions = app_menu_actions[menu.name]
        actions.append(None)
        actions.append(item)

    def add_item_to_application_toolbar(self, item, toolbar, section=None,
                                        before=None):
        """
        Add item to given application toolbar.

        section:
            TODO:
        before: SpyderAction or SpyderMenu
            TODO:
        """
        if not isinstance(toolbar, ApplicationToolBar):
            raise SpyderAPIError('Not an ApplicationMenu!')

        toolbar.addAction(item)

    def add_application_status_widget(self, name, widget):
        """
        Add status widget to main application status bar.
        """
        # TODO: Check widget class
        # TODO: Check existence
        status_bar = self._main.statusBar()
        status_bar.addWidget(widget)
        self._main._STATUS_WIDGETS[name] = widget

    def add_application_toolbar(self, name, toolbar):
        """
        Add toolbar to application toolbars.
        """
        if name in self._main._APPLICATION_TOOLBARS:
            raise SpyderAPIError(
                'Toolbar with name "{}" already added!'.format(name))

        iconsize = 24
        toolbar.setIconSize(QSize(iconsize, iconsize))
        self._main._APPLICATION_TOOLBARS[name] = toolbar
        self.main.addToolBar(toolbar)

    def get_status_widget(self, name):
        """
        Return status widget by name.
        """
        if name in self._main._STATUS_WIDGETS:
            return self._main._STATUS_WIDGETS[name]
        else:
            raise SpyderAPIError('Status widget "{}" not found!'.format(name))

    def get_application_toolbars(self):
        """Return all application toolbars created."""
        return self._main._APPLICATION_TOOLBARS

    def get_status_widgets(self):
        """Return all application status widgets created."""
        return self._main._STATUS_WIDGETS


class SpyderDockablePlugin(SpyderPluginV2):
    """
    A Spyder plugin to enhance functionality with a dockable widget.
    """
    # --- API: Mandatory attributes ------------------------------------------
    # ------------------------------------------------------------------------
    # This is the main widget of the dockable plugin.
    # Subclass PluginMainWidget
    WIDGET_CLASS = None

    # --- API: Optional attributes -------------------------------------------
    # ------------------------------------------------------------------------
    # Define a list of plugins next to which we want to to tabify this plugin.
    # The order of plugins defines the priority in case some plugin is not
    # found. These values are from the Plugins enumeration
    # Example: ['Plugins.Console', Plugin.Console]
    # TODO: Implement with list of sections
    TABIFY = None

    # Disable actions in Spyder main menus when the plugin is not visible
    DISABLE_ACTIONS_WHEN_HIDDEN = True

    # Raise and focus on switch to plugin calls.
    # If False, the widget will be raised but focus will not be given until
    # the action to switch is called a second time.
    RAISE_AND_FOCUS = False

    # --- API: Available signals ---------------------------------------------
    # ------------------------------------------------------------------------
    # The action that toggles the visibility of a dockable plugin fires
    # this signal. By checking/unchecking the option for a pane inside
    # the view menu in the application this is triggered.
    sig_toggle_view_changed = Signal(bool)
    sig_switch_to_plugin_requested = Signal(object, bool)

    # --- Private methods ----------------------------------------------------
    # ------------------------------------------------------------------------
    def __init__(self, parent, configuration):
        super().__init__(parent, configuration=configuration)

        # Defined on mainwindow.py
        self._shortcut = None

        # Widget setup
        # --------------------------------------------------------------------
        widget = self._widget
        widget.DISABLE_ACTIONS_WHEN_HIDDEN = self.DISABLE_ACTIONS_WHEN_HIDDEN
        widget.RAISE_AND_FOCUS = self.RAISE_AND_FOCUS
        widget.set_icon(self.get_icon())
        widget.set_name(self.NAME)

        # TODO: Streamline this by moving to postvisible setup
        # Render all toolbars as a final separate step on the main window
        # in case some plugins want to extend a toolbar. Since the rendering
        # can only be done once!
        widget.get_main_toolbar()._render()
        for __, toolbars in widget._aux_toolbars.items():
            for toolbar in toolbars:
                toolbar._render()

        # Default Signals
        # --------------------------------------------------------------------
        widget.sig_toggle_view_changed.connect(self.sig_toggle_view_changed)

    # --- API: available methods ---------------------------------------------
    # ------------------------------------------------------------------------
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
