# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""
spyder.api.plugins
==================

Here, 'plugins' are Qt widgets that can make changes to Spyder's
main window and call other plugins directly.
"""

# Third party imports
from qtpy.QtCore import Signal, Slot
from qtpy.QtWidgets import QWidget

# Local imports
from spyder.config.user import NoDefault
from spyder.plugins.base import BasePluginMixin, BasePluginWidgetMixin
from spyder.utils import icon_manager as ima


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
            Message to display in the status bar
        timeout: int
            Amound of time to display the message
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
