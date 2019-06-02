# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""
Base plugin class
"""

# Standard library imports
import inspect
import os

# Third party imports
import qdarkstyle
from qtpy.QtCore import Qt, Slot
from qtpy.QtGui import QCursor, QKeySequence
from qtpy.QtWidgets import (QApplication, QDockWidget, QMainWindow, QMenu,
                            QMessageBox, QShortcut, QToolButton)

# Local imports
from spyder.config.base import _
from spyder.config.gui import get_color_scheme, get_font, is_dark_interface
from spyder.config.main import CONF
from spyder.config.user import NoDefault
from spyder.py3compat import configparser, is_text_string
from spyder.utils import icon_manager as ima
from spyder.utils.qthelpers import (
    add_actions, create_action, create_toolbutton, MENU_SEPARATOR,
    toggle_actions)
from spyder.widgets.dock import SpyderDockWidget


class BasePluginMixin(object):
    """Implementation of the basic functionality for Spyder plugins."""

    def __init__(self, parent=None):
        super(BasePluginMixin, self).__init__()

        # Check compatibility
        check_compatibility, message = self.check_compatibility()

        self.is_compatible = True
        if not check_compatibility:
            self.is_compatible = False
            self.show_compatibility_message(message)

    def set_option(self, option, value):
        """Set option in spyder.ini"""
        CONF.set(self.CONF_SECTION, str(option), value)

    def get_option(self, option, default=NoDefault):
        """Get option from spyder.ini."""
        return CONF.get(self.CONF_SECTION, option, default)

    def _show_status_message(self, message, timeout=0):
        """Show message in main window's status bar."""
        self.main.statusBar().showMessage(message, timeout)

    def show_compatibility_message(self, message):
        """Show a compatibility message."""
        messageBox = QMessageBox(self)
        messageBox.setWindowModality(Qt.NonModal)
        messageBox.setAttribute(Qt.WA_DeleteOnClose)
        messageBox.setWindowTitle('Compatibility Check')
        messageBox.setText(message)
        messageBox.setStandardButtons(QMessageBox.Ok)
        messageBox.show()

    def _starting_long_process(self, message):
        """
        Show message in main window's status bar and change cursor to
        Qt.WaitCursor
        """
        self._show_status_message(message)
        QApplication.setOverrideCursor(QCursor(Qt.WaitCursor))
        QApplication.processEvents()

    def _ending_long_process(self, message=""):
        """
        Clear main window's status bar and restore mouse cursor.
        """
        QApplication.restoreOverrideCursor()
        self._show_status_message(message, timeout=2000)
        QApplication.processEvents()

    def _get_plugin_path(self):
        """Return filesystem path to the root directory of the plugin."""
        return os.path.dirname(inspect.getfile(self.__class__))


class PluginWindow(QMainWindow):
    """MainWindow subclass that contains a Spyder Plugin."""

    def __init__(self, plugin):
        QMainWindow.__init__(self)
        self.plugin = plugin

        # Setting interface theme
        if is_dark_interface():
            self.setStyleSheet(qdarkstyle.load_stylesheet_from_environment())

    def closeEvent(self, event):
        """Reimplement Qt method."""
        self.plugin.dockwidget.setWidget(self.plugin)
        self.plugin.dockwidget.setVisible(True)
        self.plugin.switch_to_plugin()
        QMainWindow.closeEvent(self, event)
        self.plugin.undocked_window = None


class BasePluginWidgetMixin(object):
    """
    Implementation of the basic functionality for Spyder plugin widgets.
    """

    ALLOWED_AREAS = Qt.AllDockWidgetAreas
    LOCATION = Qt.LeftDockWidgetArea
    FEATURES = QDockWidget.DockWidgetClosable | QDockWidget.DockWidgetMovable

    def __init__(self, parent=None):
        super(BasePluginWidgetMixin, self).__init__()

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

        # Options buttons
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

        # Options menu
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

        # Default actions for Options menu
        self.dock_action = create_action(self,
                                         _("Dock"),
                                         icon=ima.icon('dock'),
                                         tip=_("Dock the pane"),
                                         triggered=self.close_window)

        self.undock_action = create_action(self,
                                           _("Undock"),
                                           icon=ima.icon('undock'),
                                           tip=_("Undock the pane"),
                                           triggered=self.create_window)

        self.close_plugin_action = create_action(self,
                                                 _("Close"),
                                                 icon=ima.icon('close_pane'),
                                                 tip=_("Close the pane"),
                                                 triggered=self.plugin_closed)

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

    def update_plugin_title(self):
        """Update plugin title, i.e. dockwidget or window title"""
        if self.dockwidget is not None:
            win = self.dockwidget
        elif self.undocked_window is not None:
            win = self.undocked_window
        else:
            return
        win.setWindowTitle(self.get_plugin_title())

    def create_dockwidget(self):
        """Add to parent QMainWindow as a dock widget"""
        # Creating dock widget
        dock = SpyderDockWidget(self.get_plugin_title(), self.main)

        # Set properties
        dock.setObjectName(self.__class__.__name__+"_dw")
        dock.setAllowedAreas(self.ALLOWED_AREAS)
        dock.setFeatures(self.FEATURES)
        dock.setWidget(self)
        self.update_margins()
        dock.visibilityChanged.connect(self.visibility_changed)
        dock.topLevelChanged.connect(self.on_top_level_changed)
        dock.sig_plugin_closed.connect(self.plugin_closed)
        self.dockwidget = dock
        if self.shortcut is not None:
            sc = QShortcut(QKeySequence(self.shortcut), self.main,
                            self.switch_to_plugin)
            self.register_shortcut(sc, "_", "Switch to %s" % self.CONF_SECTION)
        return (dock, self.LOCATION)

    def create_configwidget(self, parent):
        """Create configuration dialog box page widget"""
        if self.CONFIGWIDGET_CLASS is not None:
            configwidget = self.CONFIGWIDGET_CLASS(self, parent)
            configwidget.initialize()
            return configwidget

    def switch_to_plugin(self):
        """Switch to plugin."""
        if (self.main.last_plugin is not None and
                self.main.last_plugin.ismaximized and
                self.main.last_plugin is not self):
            self.main.maximize_dockwidget()
        if not self.toggle_view_action.isChecked():
            self.toggle_view_action.setChecked(True)
        self.visibility_changed(True)

    @Slot()
    def plugin_closed(self):
        """DockWidget was closed"""
        self.toggle_view_action.setChecked(False)

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

    @Slot()
    def close_window(self):
        """Close QMainWindow instance that contains this plugin."""
        if self.undocked_window is not None:
            self.undocked_window.close()
            self.undocked_window = None

            # Oddly, these actions can appear disabled after the Dock
            # action is pressed
            self.undock_action.setDisabled(False)
            self.close_plugin_action.setDisabled(False)

    @Slot()
    def create_window(self):
        """Create a QMainWindow instance containing this plugin."""
        self.undocked_window = window = PluginWindow(self)
        window.setAttribute(Qt.WA_DeleteOnClose)
        icon = self.get_plugin_icon()
        if is_text_string(icon):
            icon = self.get_icon(icon)
        window.setWindowIcon(icon)
        window.setWindowTitle(self.get_plugin_title())
        window.setCentralWidget(self)
        window.resize(self.size())
        self.refresh_plugin()

        self.dockwidget.setFloating(False)
        self.dockwidget.setVisible(False)

        window.show()

    @Slot(bool)
    def on_top_level_changed(self, top_level):
        """Actions to perform when a plugin is undocked to be moved."""
        if top_level:
            self.undock_action.setDisabled(True)
        else:
            self.undock_action.setDisabled(False)

    # -- Public API
    # The methods below are exposed in spyder/api/plugins.py
    def visibility_changed(self, enable):
        """Dock widget visibility has changed."""
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

    def refresh_actions(self):
        """Refresh Options menu."""
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

    def initialize_plugin(self):
        """
        Setup Options menu, create toggle action and connect some signals.
        """
        self.create_toggle_view_action()

        self.plugin_actions = self.get_plugin_actions() + [MENU_SEPARATOR,
                                                           self.undock_action]
        add_actions(self.options_menu, self.plugin_actions)
        self.options_button.setMenu(self.options_menu)
        self.options_menu.aboutToShow.connect(self.refresh_actions)

        self.sig_update_plugin_title.connect(self.update_plugin_title)
        self.setWindowTitle(self.get_plugin_title())

    def register_shortcut(self, qaction_or_qshortcut, context, name,
                          add_sc_to_tip=False):
        """Register a shortcut associated to a QAction or QShortcut."""
        self.main.register_shortcut(qaction_or_qshortcut, context,
                                    name, add_sc_to_tip)

    def get_color_scheme(self):
        """Get the current color scheme."""
        return get_color_scheme(CONF.get('appearance', 'selected'))
