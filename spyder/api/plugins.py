# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""
spyder.api.plugins
==================

Here, 'plugins' are dock widgets designed specifically for Spyder
These plugins inherit the following classes
(SpyderPluginMixin & SpyderPluginWidget)
"""

# pylint: disable=C0103
# pylint: disable=R0903
# pylint: disable=R0911
# pylint: disable=R0201

# Standard library imports
import inspect
import os

# Third party imports
from qtpy.QtCore import Qt, Signal
from qtpy.QtGui import QCursor, QKeySequence
from qtpy.QtWidgets import (QApplication, QDockWidget, QMainWindow, QShortcut,
                            QWidget)

# Local imports
from spyder.config.base import _
from spyder.config.gui import get_color_scheme, get_font
from spyder.config.main import CONF
from spyder.config.user import NoDefault
from spyder.py3compat import configparser, is_text_string
from spyder.utils import icon_manager as ima
from spyder.utils.qthelpers import create_action, toggle_actions
from spyder.widgets.dock import SpyderDockWidget


class BasePluginWidget(QWidget):
    """
    Useful methods to bind widgets to the main window
    See SpyderPluginWidget class for required widget interface

    Signals:
        * sig_option_changed
             Example:
             plugin.sig_option_changed.emit('show_all', checked)
        * show_message
        * update_plugin_title
    """
    ALLOWED_AREAS = Qt.AllDockWidgetAreas
    LOCATION = Qt.LeftDockWidgetArea
    FEATURES = QDockWidget.DockWidgetClosable | QDockWidget.DockWidgetFloatable

    # Signals
    sig_option_changed = Signal(str, object)
    show_message = Signal(str, int)
    update_plugin_title = Signal()

    def __init__(self, main=None):
        """Bind widget to a QMainWindow instance"""
        QWidget.__init__(self, main)
        assert self.CONF_SECTION is not None

        self.PLUGIN_PATH = os.path.dirname(inspect.getfile(self.__class__))
        self.main = main
        self.default_margins = None
        self.plugin_actions = None
        self.dockwidget = None
        self.mainwindow = None
        self.ismaximized = False
        self.isvisible = False

        # NOTE: Don't use the default option of CONF.get to assign a
        # None shortcut to plugins that don't have one. That will mess
        # the creation of our Keyboard Shortcuts prefs page
        try:
            self.shortcut = CONF.get('shortcuts', '_/switch to %s' % \
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
        self.plugin_actions = self.get_plugin_actions()
        self.show_message.connect(self.__show_message)
        self.update_plugin_title.connect(self.__update_plugin_title)
        self.sig_option_changed.connect(self.set_option)
        self.setWindowTitle(self.get_plugin_title())

    def initialize_plugin_in_mainwindow_layout(self):
        """
        If this is the first time the plugin is shown, perform actions to
        initialize plugin position in Spyder's window layout.

        Use on_first_registration to define the actions to be run
        by your plugin
        """
        if self.get_option('first_time', True):
            try:
                self.on_first_registration()
            except NotImplementedError:
                return
            self.set_option('first_time', False)

    def update_margins(self):
        """Update plugin margins"""
        layout = self.layout()
        if self.default_margins is None:
            self.default_margins = layout.getContentsMargins()
        if CONF.get('main', 'use_custom_margin'):
            margin = CONF.get('main', 'custom_margin')
            layout.setContentsMargins(*[margin]*4)
        else:
            layout.setContentsMargins(*self.default_margins)

    def __update_plugin_title(self):
        """Update plugin title, i.e. dockwidget or mainwindow title"""
        if self.dockwidget is not None:
            win = self.dockwidget
        elif self.mainwindow is not None:
            win = self.mainwindow
        else:
            return
        win.setWindowTitle(self.get_plugin_title())

    def create_dockwidget(self):
        """Add to parent QMainWindow as a dock widget"""

        # This is not clear yet why the following do not work...
        # (see Issue #880)
##         # Using Qt.Window window flags solves Issue #880 (detached dockwidgets
##         # are not painted after restarting Spyder and restoring their hexstate)
##         # but it does not work with PyQt <=v4.7 (dockwidgets can't be docked)
##         # or non-Windows platforms (lot of warnings are printed out)
##         # (so in those cases, we use the default window flags: Qt.Widget):
##         flags = Qt.Widget if is_old_pyqt or os.name != 'nt' else Qt.Window
        dock = SpyderDockWidget(self.get_plugin_title(), self.main)#, flags)

        dock.setObjectName(self.__class__.__name__+"_dw")
        dock.setAllowedAreas(self.ALLOWED_AREAS)
        dock.setFeatures(self.FEATURES)
        dock.setWidget(self)
        self.update_margins()
        dock.visibilityChanged.connect(self.visibility_changed)
        dock.plugin_closed.connect(self.plugin_closed)
        self.dockwidget = dock
        if self.shortcut is not None:
            sc = QShortcut(QKeySequence(self.shortcut), self.main,
                            self.switch_to_plugin)
            self.register_shortcut(sc, "_", "Switch to %s" % self.CONF_SECTION)
        return (dock, self.LOCATION)

    def create_mainwindow(self):
        """
        Create a QMainWindow instance containing this plugin
        Note: this method is currently not used in Spyder core plugins
        """
        self.mainwindow = mainwindow = QMainWindow()
        mainwindow.setAttribute(Qt.WA_DeleteOnClose)
        icon = self.get_plugin_icon()
        if is_text_string(icon):
            icon = self.get_icon(icon)
        mainwindow.setWindowIcon(icon)
        mainwindow.setWindowTitle(self.get_plugin_title())
        mainwindow.setCentralWidget(self)
        self.refresh_plugin()
        return mainwindow

    def create_configwidget(self, parent):
        """Create configuration dialog box page widget"""
        if self.CONFIGWIDGET_CLASS is not None:
            configwidget = self.CONFIGWIDGET_CLASS(self, parent)
            configwidget.initialize()
            return configwidget

    def register_shortcut(self, qaction_or_qshortcut, context, name,
                          add_sc_to_tip=False):
        """
        Register QAction or QShortcut to Spyder main application

        if add_sc_to_tip is True, the shortcut is added to the
        action's tooltip
        """
        self.main.register_shortcut(qaction_or_qshortcut, context,
                                    name, add_sc_to_tip)

    def register_widget_shortcuts(self, widget):
        """
        Register widget shortcuts
        widget interface must have a method called 'get_shortcut_data'
        """
        for qshortcut, context, name in widget.get_shortcut_data():
            self.register_shortcut(qshortcut, context, name)

    def switch_to_plugin(self):
        """Switch to plugin
        This method is called when pressing plugin's shortcut key"""
        if not self.ismaximized:
            self.dockwidget.show()
        if not self.toggle_view_action.isChecked():
            self.toggle_view_action.setChecked(True)
        self.visibility_changed(True)

    def visibility_changed(self, enable):
        """DockWidget visibility has changed"""
        if enable:
            self.dockwidget.raise_()
            widget = self.get_focus_widget()
            if widget is not None:
                widget.setFocus()
        visible = self.dockwidget.isVisible() or self.ismaximized
        if self.DISABLE_ACTIONS_WHEN_HIDDEN:
            toggle_actions(self.plugin_actions, visible)
        self.isvisible = enable and visible
        if self.isvisible:
            self.refresh_plugin()   # To give focus to the plugin's widget

    def plugin_closed(self):
        """DockWidget was closed"""
        self.toggle_view_action.setChecked(False)

    def set_option(self, option, value):
        """
        Set a plugin option in configuration file
        Use a SIGNAL to call it, e.g.:
        plugin.sig_option_changed.emit('show_all', checked)
        """
        CONF.set(self.CONF_SECTION, str(option), value)

    def get_option(self, option, default=NoDefault):
        """Get a plugin option from configuration file"""
        return CONF.get(self.CONF_SECTION, option, default)

    def get_plugin_font(self, rich_text=False):
        """
        Return plugin font option.

        All plugins in Spyder use a global font. This is a convenience method
        in case some plugins will have a delta size based on the default size.
        """

        if rich_text:
            option = 'rich_font'
            font_size_delta = self.RICH_FONT_SIZE_DELTA
        else:
            option = 'font'
            font_size_delta = self.FONT_SIZE_DELTA

        return get_font(option=option, font_size_delta=font_size_delta)

    def set_plugin_font(self):
        """
        Set plugin font option.

        Note: All plugins in Spyder use a global font. To define a different
        size, the plugin must define a 'FONT_SIZE_DELTA' class variable.
        """
        raise Exception("Plugins font is based on the general settings, "
                        "and cannot be set directly on the plugin."
                        "This method is deprecated.")

    def __show_message(self, message, timeout=0):
        """Show message in main window's status bar"""
        self.main.statusBar().showMessage(message, timeout)

    def starting_long_process(self, message):
        """
        Showing message in main window's status bar
        and changing mouse cursor to Qt.WaitCursor
        """
        self.__show_message(message)
        QApplication.setOverrideCursor(QCursor(Qt.WaitCursor))
        QApplication.processEvents()

    def ending_long_process(self, message=""):
        """
        Clearing main window's status bar
        and restoring mouse cursor
        """
        QApplication.restoreOverrideCursor()
        self.__show_message(message, timeout=2000)
        QApplication.processEvents()

    def get_color_scheme(self):
        """Get current color scheme"""
        return get_color_scheme(CONF.get('color_schemes', 'selected'))

    def create_toggle_view_action(self):
        """Associate a toggle view action with each plugin"""
        title = self.get_plugin_title()
        if self.CONF_SECTION == 'editor':
            title = _('Editor')
        if self.shortcut is not None:
            action = create_action(self, title,
                             toggled=lambda checked: self.toggle_view(checked),
                             shortcut=QKeySequence(self.shortcut),
                             context=Qt.WidgetShortcut)
        else:
            action = create_action(self, title, toggled=lambda checked:
                                                self.toggle_view(checked))
        self.toggle_view_action = action

    def toggle_view(self, checked):
        """Toggle view"""
        if not self.dockwidget:
            return
        if checked:
            self.dockwidget.show()
            self.dockwidget.raise_()
        else:
            self.dockwidget.hide()


class SpyderPluginWidget(BasePluginWidget):
    """
    Spyder plugin widget class
    Plugin widgets must inherit this class and reimplement its interface
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
        Return plugin title
        Note: after some thinking, it appears that using a method
        is more flexible here than using a class attribute
        """
        raise NotImplementedError

    def get_plugin_icon(self):
        """
        Return plugin icon (QIcon instance)
        Note: this is required for plugins creating a main window
              (see SpyderPluginMixin.create_mainwindow)
              and for configuration dialog widgets creation
        """
        return ima.icon('outline_explorer')

    def get_focus_widget(self):
        """
        Return the widget to give focus to when
        this plugin's dockwidget is raised on top-level
        """
        pass

    def closing_plugin(self, cancelable=False):
        """
        Perform actions before parent main window is closed
        Return True or False whether the plugin may be closed immediately or not
        Note: returned value is ignored if *cancelable* is False
        """
        return True

    def refresh_plugin(self):
        """Refresh widget"""
        raise NotImplementedError

    def get_plugin_actions(self):
        """
        Return a list of actions related to plugin
        Note: these actions will be enabled when plugin's dockwidget is visible
              and they will be disabled when it's hidden
        """
        raise NotImplementedError

    def register_plugin(self):
        """Register plugin in Spyder's main window"""
        raise NotImplementedError

    def on_first_registration(self):
        """Action to be performed on first plugin registration"""
        raise NotImplementedError

    def apply_plugin_settings(self, options):
        """Apply configuration file's plugin settings"""
        raise NotImplementedError

    def update_font(self):
        """
        This has to be reimplemented by plugins that need to adjust
        their fonts
        """
        pass
