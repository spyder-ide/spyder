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
from qtpy.QtCore import Qt, Signal
from qtpy.QtGui import QCursor
from qtpy.QtWidgets import (QApplication, QMenu, QMessageBox, QToolButton,
                            QWidget)

# Local imports
from spyder.config.base import _
from spyder.config.gui import get_color_scheme, is_dark_interface
from spyder.config.main import CONF
from spyder.config.user import NoDefault
from spyder.plugins.base import BasePluginMixin
from spyder.py3compat import configparser
from spyder.utils import icon_manager as ima
from spyder.utils.qthelpers import (add_actions, create_toolbutton,
                                    MENU_SEPARATOR, toggle_actions)


class PluginWidget(QWidget, BasePluginMixin):
    """
    Public interface for Spyder plugins.

    Warning: Don't override any methods present here!

    Signals:
      * sig_option_changed
          Example:
            plugin.sig_option_changed.emit('show_all', checked)
      * sig_show_message
      * sig_update_plugin_title
    """

    sig_option_changed = Signal(str, object)
    sig_show_message = Signal(str, int)
    sig_update_plugin_title = Signal()

    def __init__(self, main=None):
        """Bind widget to a QMainWindow instance."""
        super(PluginWidget, self).__init__(main)
        assert self.CONF_SECTION is not None

        self.dockwidget = None
        self.undocked_window = None

        # Check compatibility
        check_compatibility, message = self.check_compatibility()
        if not check_compatibility:
            self.show_compatibility_message(message)

        self.PLUGIN_PATH = os.path.dirname(inspect.getfile(self.__class__))
        self.main = main
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

        It must be run at the end of __init__
        """
        self.create_toggle_view_action()

        self.plugin_actions = self.get_plugin_actions() + [MENU_SEPARATOR,
                                                           self.undock_action]
        add_actions(self.options_menu, self.plugin_actions)
        self.options_button.setMenu(self.options_menu)
        self.options_menu.aboutToShow.connect(self.refresh_actions)

        self.sig_show_message.connect(self.show_message)
        self.sig_update_plugin_title.connect(self.update_plugin_title)
        self.sig_option_changed.connect(self.set_option)
        self.setWindowTitle(self.get_plugin_title())

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
        """
        Dock widget visibility has changed.
        """
        if self.dockwidget is None:
            return
        if enable:
            self.dockwidget.raise_()
            widget = self.get_focus_widget()
            if widget is not None and self.undocked_window is not None:
                widget.setFocus()
        visible = self.dockwidget.isVisible() or self.ismaximized
        if self.DISABLE_ACTIONS_WHEN_HIDDEN:
            toggle_actions(self.plugin_actions, visible)
        self.isvisible = enable and visible
        if self.isvisible:
            self.refresh_plugin()   # To give focus to the plugin's widget

    def set_option(self, option, value):
        """
        Set a plugin option in configuration file.

        Note: Use sig_option_changed to call it from widgets of the
              same or another plugin.
        """
        CONF.set(self.CONF_SECTION, str(option), value)

    def get_option(self, option, default=NoDefault):
        """
        Get a plugin's option from configuration file.
        """
        return CONF.get(self.CONF_SECTION, option, default)

    def starting_long_process(self, message):
        """
        Showing message in main window's status bar.

        This also changes mouse cursor to Qt.WaitCursor
        """
        self.show_message(message)
        QApplication.setOverrideCursor(QCursor(Qt.WaitCursor))
        QApplication.processEvents()

    def ending_long_process(self, message=""):
        """
        Clear main window's status bar and restore mouse cursor.
        """
        QApplication.restoreOverrideCursor()
        self.show_message(message, timeout=2000)
        QApplication.processEvents()

    def get_color_scheme(self):
        """
        Get current color scheme.
        """
        return get_color_scheme(CONF.get('appearance', 'selected'))

    def show_compatibility_message(self, message):
        """
        Show compatibility message.
        """
        messageBox = QMessageBox(self)
        messageBox.setWindowModality(Qt.NonModal)
        messageBox.setAttribute(Qt.WA_DeleteOnClose)
        messageBox.setWindowTitle('Compatibility Check')
        messageBox.setText(message)
        messageBox.setStandardButtons(QMessageBox.Ok)
        messageBox.show()

    def refresh_actions(self):
        """
        Create options menu.
        """
        self.options_menu.clear()

        # Decide what additional actions to show
        if self.undocked_window is None:
            additional_actions = [MENU_SEPARATOR,
                                  self.undock_action,
                                  self.close_plugin_action]
        else:
            additional_actions = [MENU_SEPARATOR,
                                  self.dock_action]

        # Create actions list
        self.plugin_actions = self.get_plugin_actions() + additional_actions
        add_actions(self.options_menu, self.plugin_actions)


class SpyderPluginWidget(PluginWidget):
    """
    Spyder plugin widget class.

    All plugin widgets must inherit this class and reimplement its interface.
    """

    # ---------------------------- ATTRIBUTES ---------------------------------

    # Name of the configuration section that's going to be
    # used to record the plugin's permanent data in Spyder
    # config system (i.e. in spyder.ini)
    # Status: Required
    CONF_SECTION = None

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
