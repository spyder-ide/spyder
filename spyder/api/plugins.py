# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""
spyder.api.plugins
==================

Here, 'plugins' are Qt widgets designed specifically for Spyder
"""

# Standard library imports
import inspect
import os

# Third party imports
from qtpy.QtCore import Signal, Slot
from qtpy.QtWidgets import QMenu, QToolButton, QWidget

# Local imports
from spyder.config.base import _
from spyder.config.gui import get_color_scheme, is_dark_interface
from spyder.config.main import CONF
from spyder.config.user import NoDefault
from spyder.plugins.base import BasePluginMixin, BasePluginWidgetMixin
from spyder.py3compat import configparser
from spyder.utils import icon_manager as ima
from spyder.utils.qthelpers import (add_actions, create_toolbutton,
                                    MENU_SEPARATOR)


class BasePlugin(BasePluginMixin):
    """
    Basic functionality for Spyder plugins.

    WARNING: Don't override any methods present here!
    """

    # Use this signal to display a message in the status bar
    sig_show_message = Signal(str, int)

    # Use this signal to inform another plugin that a configuration
    # value has changed.
    sig_option_changed = Signal(str, object)

    def __init__(self, parent=None):
        super(BasePlugin, self).__init__(parent)

        # This is the plugin parent, which corresponds to the main
        # window.
        self.main = parent

        # Filesystem path to this plugin
        self.PLUGIN_PATH = os.path.dirname(inspect.getfile(self.__class__))

        # Connect signals to slots.
        self.sig_show_message.connect(self.show_message)
        self.sig_option_changed.connect(self.set_option)

    @Slot(str)
    @Slot(str, int)
    def show_message(self, message, timeout=0):
        """Show message in main window's status bar."""
        super(BasePlugin, self).show_message(message, timeout)

    @Slot(str, object)
    def set_option(self, option, value):
        """
        Set an option in CONF_SECTION of Spyder configuration file.

        Note: Use sig_option_changed to call it from widgets of the
              same or another plugin.
        """
        super(BasePlugin, self).set_option(option, value)

    def get_option(self, option, default=NoDefault):
        """Get an option from our configuration system."""
        return super(BasePlugin, self).get_option(option, default)

    def starting_long_process(self, message):
        """
        Showing message in main window's status bar when starting a
        long process.

        This also changes mouse cursor to Qt.WaitCursor
        """
        super(BasePlugin, self).starting_long_process(message)

    def ending_long_process(self, message=""):
        """
        Clear main window's status bar after a long process and restore
        mouse cursor.
        """
        super(BasePlugin, self).ending_long_process(message)


class SpyderPlugin(BasePlugin):
    """
    Spyder plugin class.

    All plugins *must* inherit this class and reimplement its interface.
    """
    # ---------------------------- ATTRIBUTES ---------------------------------

    # Name of the configuration section that's going to be
    # used to record the plugin's permanent data in Spyder
    # config system (i.e. in spyder.ini)
    # Status: Required
    CONF_SECTION = None

    def check_compatibility(self):
        """
        This method can be implemented to check compatibility of a plugin
        for a given condition.

        `message` should give information in case of non compatibility:
        For example: 'This plugin does not work with Qt4'
        """
        message = ''
        valid = True
        return valid, message


class BasePluginWidget(SpyderPlugin, QWidget, BasePluginWidgetMixin):
    """
    Basic functionality for Spyder plugin widgets.

    WARNING: Don't override any methods present here!
    """

    sig_update_plugin_title = Signal()

    def __init__(self, main=None):
        """Bind widget to a QMainWindow instance."""
        super(BasePluginWidget, self).__init__(main)

        # Dockwidget for the plugin, i.e. the pane that's going to be
        # visible in Spyder
        self.dockwidget = None

        # Attribute to keep track if the plugin is undocked in a
        # separate window
        self.undocked_window = None

        self.default_margins = None
        self.plugin_actions = None
        self.ismaximized = False
        self.isvisible = False

        # Options button and menu
        self.options_button = create_toolbutton(self, text=_('Options'),
                                                icon=ima.icon('tooloptions'))
        self.options_button.setPopupMode(QToolButton.InstantPopup)

        # Don't show menu arrow and remove padding
        if is_dark_interface():
            self.options_button.setStyleSheet(
                ("QToolButton::menu-indicator{image: none;}\n"
                 "QToolButton{padding: 3px;}"))
        else:
            self.options_button.setStyleSheet(
                "QToolButton::menu-indicator{image: none;}")
        self.options_menu = QMenu(self)

        # NOTE: Don't use the default option of CONF.get to assign a
        # None shortcut to plugins that don't have one. That will mess
        # the creation of our Keyboard Shortcuts prefs page
        try:
            self.shortcut = CONF.get('shortcuts', '_/switch to %s' %
                                     self.CONF_SECTION)
        except configparser.NoOptionError:
            pass

        # We decided to create our own toggle action instead of using
        # the one that comes with dockwidget because it's not possible
        # to raise and focus the plugin with it.
        self.toggle_view_action = None

    def initialize_plugin(self):
        """
        Initialize plugin: connect signals, setup actions, etc.

        It must be called at the end of the plugin's __init__
        """
        super(BasePluginWidget, self).initialize_plugin()

    def register_shortcut(self, qaction_or_qshortcut, context, name,
                          add_sc_to_tip=False):
        """
        Register QAction or QShortcut to Spyder main application.

        if add_sc_to_tip is True, the shortcut is added to the
        action's tooltip
        """
        self.main.register_shortcut(qaction_or_qshortcut, context,
                                    name, add_sc_to_tip)

    def register_widget_shortcuts(self, widget):
        """
        Register widget shortcuts.

        Widget interface must have a method called 'get_shortcut_data'
        """
        for qshortcut, context, name in widget.get_shortcut_data():
            self.register_shortcut(qshortcut, context, name)

    def visibility_changed(self, enable):
        """Dock widget visibility has changed."""
        super(BasePluginWidget, self).visibility_changed(enable)

    def get_color_scheme(self):
        """Get current color scheme."""
        return get_color_scheme(CONF.get('appearance', 'selected'))

    def refresh_actions(self):
        """Refresh options menu."""
        super(BasePluginWidget, self).refresh_actions()


class SpyderPluginWidget(BasePluginWidget):
    """
    Spyder plugin widget class.

    All plugin widgets *must* inherit this class and reimplement its interface.
    """

    # ---------------------------- ATTRIBUTES ---------------------------------

    # Widget to be used as entry in Spyder Preferences
    # dialog
    # Status: Optional
    CONFIGWIDGET_CLASS = None

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
        Return plugin title.
        """
        raise NotImplementedError

    def get_plugin_icon(self):
        """
        Return plugin icon (QIcon instance).
        """
        return ima.icon('outline_explorer')

    def get_focus_widget(self):
        """
        Return the widget to give focus to.

        This is applied when plugin's dockwidget is raised on top-level.
        """
        pass

    def closing_plugin(self, cancelable=False):
        """
        Perform actions before parent main window is closed.

        Return True or False whether the plugin may be closed immediately or
        not.
        Note: returned value is ignored if *cancelable* is False
        """
        return True

    def refresh_plugin(self):
        """Refresh widget."""
        raise NotImplementedError

    def get_plugin_actions(self):
        """
        Return a list of QAction's related to plugin.

        Note: These actions will be shown in the plugins Options menu.
        """
        raise NotImplementedError

    def register_plugin(self):
        """
        Register plugin in Spyder's main window.
        """
        raise NotImplementedError

    def on_first_registration(self):
        """
        Action to be performed on first plugin registration.

        Note: This is most usually used to tabify the plugin next to one
              of the core plugins, like this:

              self.main.tabify_plugins(self.main.variableexplorer, self)
        """
        raise NotImplementedError

    def apply_plugin_settings(self, options):
        """
        What to do to apply configuration plugin settings.
        """
        raise NotImplementedError

    def update_font(self):
        """
        This must be reimplemented by plugins that need to adjust their fonts.
        """
        pass

