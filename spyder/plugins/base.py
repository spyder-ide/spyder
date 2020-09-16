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
import sys

# Third party imports
import qdarkstyle
from qtpy.QtCore import Qt, Slot
from qtpy.QtGui import QCursor, QKeySequence
from qtpy.QtWidgets import (QAction, QApplication, QDockWidget, QMainWindow,
                            QMenu, QMessageBox, QShortcut, QToolButton)

# Local imports
from spyder.config.base import _
from spyder.config.gui import get_color_scheme, get_font, is_dark_interface
from spyder.config.manager import CONF
from spyder.config.user import NoDefault
from spyder.py3compat import configparser, is_text_string
from spyder.utils import icon_manager as ima
from spyder.utils.qthelpers import (
    add_actions, create_action, create_toolbutton, MENU_SEPARATOR,
    toggle_actions, set_menu_icons)
from spyder.widgets.dock import SpyderDockWidget


class BasePluginMixin(object):
    """Implementation of the basic functionality for Spyder plugins."""

    # Define configuration name map for plugin to split configuration
    # among several files. See spyder/config/main.py
    # Status: Hidden
    _CONF_NAME_MAP = None

    def __init__(self, parent=None):
        super(BasePluginMixin, self).__init__()

        # Check compatibility
        check_compatibility, message = self.check_compatibility()

        self._register_plugin()

        self._is_compatible = True
        if not check_compatibility:
            self._is_compatible = False
            self._show_compatibility_message(message)

    def _register_plugin(self):
        """Register plugin configuration."""
        CONF.register_plugin(self)

    def _set_option(self, option, value, section=None):
        """Set option in spyder.ini"""
        section = self.CONF_SECTION if section is None else section
        CONF.set(section, str(option), value)

    def _get_option(self, option, default=NoDefault, section=None):
        """Get option from spyder.ini."""
        section = self.CONF_SECTION if section is None else section
        return CONF.get(section, option, default)

    def _show_status_message(self, message, timeout=0):
        """Show message in main window's status bar."""
        self.main.statusBar().showMessage(message, timeout)

    def _show_compatibility_message(self, message):
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

    def _create_configwidget(self, dlg, main_window):
        """Create configuration dialog box page widget"""
        if self.CONFIGWIDGET_CLASS is not None:
            parent = self
            main = dlg
            if not hasattr(self, 'dockwidget'):
                # Prevent QWidget assignment to a plugin that does not have
                # a graphical widget.
                parent = dlg
                main = main_window
            configwidget = self.CONFIGWIDGET_CLASS(parent, main)
            configwidget.initialize()
            return configwidget


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
        self.plugin.set_ancestor(self.plugin.main)
        self.plugin.dockwidget.setWidget(self.plugin)
        self.plugin.dockwidget.setVisible(True)
        self.plugin.switch_to_plugin()
        QMainWindow.closeEvent(self, event)
        # Qt might want to do something with this soon,
        # So it should not be deleted by python yet.
        # Fixes spyder-ide/spyder#10704
        self.plugin.__unsafe__window = self
        self.plugin._undocked_window = None


class BasePluginWidgetMixin(object):
    """
    Implementation of the basic functionality for Spyder plugin widgets.
    """

    def __init__(self, parent=None):
        super(BasePluginWidgetMixin, self).__init__()

        # Actions to add to the Options menu
        self._plugin_actions = None

        # Attribute to keep track if the plugin is undocked in a
        # separate window
        self._undocked_window = None

        self._ismaximized = False
        self._default_margins = None
        self._isvisible = False

        self.shortcut = None

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
        self._options_menu = QMenu(self)

        # We decided to create our own toggle action instead of using
        # the one that comes with dockwidget because it's not possible
        # to raise and focus the plugin with it.
        self._toggle_view_action = None

        # Default actions for Options menu
        self._dock_action = create_action(
            self,
            _("Dock"),
            icon=ima.icon('dock'),
            tip=_("Dock the pane"),
            triggered=self._close_window)

        self._undock_action = create_action(
            self,
            _("Undock"),
            icon=ima.icon('undock'),
            tip=_("Undock the pane"),
            triggered=self._create_window)

        self._close_plugin_action = create_action(
            self,
            _("Close"),
            icon=ima.icon('close_pane'),
            tip=_("Close the pane"),
            triggered=self._plugin_closed)

    def _initialize_plugin_in_mainwindow_layout(self):
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

    def _update_margins(self):
        """Update plugin margins"""
        layout = self.layout()
        if self._default_margins is None:
            self._default_margins = layout.getContentsMargins()
        if CONF.get('main', 'use_custom_margin'):
            margin = CONF.get('main', 'custom_margin')
            layout.setContentsMargins(*[margin]*4)
        else:
            layout.setContentsMargins(*self._default_margins)

    def _update_plugin_title(self):
        """Update plugin title, i.e. dockwidget or window title"""
        if self.dockwidget is not None:
            win = self.dockwidget
        elif self._undocked_window is not None:
            win = self._undocked_window
        else:
            return
        win.setWindowTitle(self.get_plugin_title())

    def _create_dockwidget(self):
        """Add to parent QMainWindow as a dock widget"""
        # Creating dock widget
        dock = SpyderDockWidget(self.get_plugin_title(), self.main)

        # Set properties
        dock.setObjectName(self.__class__.__name__+"_dw")
        dock.setAllowedAreas(dock.ALLOWED_AREAS)
        dock.setFeatures(dock.FEATURES)
        dock.setWidget(self)
        self._update_margins()
        dock.visibilityChanged.connect(self._visibility_changed)
        dock.topLevelChanged.connect(self._on_top_level_changed)
        dock.sig_plugin_closed.connect(self._plugin_closed)
        self.dockwidget = dock

        # NOTE: Don't use the default option of CONF.get to assign a
        # None shortcut to plugins that don't have one. That will mess
        # the creation of our Keyboard Shortcuts prefs page
        try:
            context = '_'
            name = 'switch to {}'.format(self.CONF_SECTION)
            self.shortcut = CONF.get_shortcut(context, name,
                                              plugin_name=self.CONF_SECTION)
        except (configparser.NoSectionError, configparser.NoOptionError):
            pass

        if self.shortcut is not None and self.main is not None:
            sc = QShortcut(QKeySequence(self.shortcut), self.main,
                           self.switch_to_plugin)
            self.register_shortcut(sc, "_", "Switch to {}".format(
                self.CONF_SECTION))

        return (dock, dock.LOCATION)

    def _switch_to_plugin(self):
        """Switch to plugin."""
        if (self.main.last_plugin is not None and
                self.main.last_plugin._ismaximized and
                self.main.last_plugin is not self):
            self.main.maximize_dockwidget()
        if not self._toggle_view_action.isChecked():
            self._toggle_view_action.setChecked(True)
        self._visibility_changed(True)

    @Slot()
    def _plugin_closed(self):
        """DockWidget was closed."""
        if self._toggle_view_action:
            self._toggle_view_action.setChecked(False)

    def _get_font(self, rich_text=False):
        """Return plugin font."""
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

    def _create_toggle_view_action(self):
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
        self._toggle_view_action = action

    @Slot()
    def _close_window(self):
        """Close QMainWindow instance that contains this plugin."""
        if self._undocked_window is not None:
            self._undocked_window.close()
            self._undocked_window = None

            # Oddly, these actions can appear disabled after the Dock
            # action is pressed
            self._undock_action.setDisabled(False)
            self._close_plugin_action.setDisabled(False)

    @Slot()
    def _create_window(self):
        """Create a QMainWindow instance containing this plugin."""
        self._undocked_window = window = PluginWindow(self)
        window.setAttribute(Qt.WA_DeleteOnClose)
        icon = self.get_plugin_icon()
        if is_text_string(icon):
            icon = self.get_icon(icon)
        window.setWindowIcon(icon)
        window.setWindowTitle(self.get_plugin_title())
        window.setCentralWidget(self)
        window.resize(self.size())
        self.refresh_plugin()
        self.set_ancestor(window)
        self.dockwidget.setFloating(False)
        self.dockwidget.setVisible(False)

        window.show()

    @Slot(bool)
    def _on_top_level_changed(self, top_level):
        """Actions to perform when a plugin is undocked to be moved."""
        if top_level:
            self._undock_action.setDisabled(True)
        else:
            self._undock_action.setDisabled(False)

    def _visibility_changed(self, enable):
        """Dock widget visibility has changed."""
        if self.dockwidget is None:
            return
        if enable:
            self.dockwidget.raise_()
            widget = self.get_focus_widget()
            if widget is not None and self._undocked_window is not None:
                widget.setFocus()
        visible = self.dockwidget.isVisible() or self._ismaximized
        if self.DISABLE_ACTIONS_WHEN_HIDDEN:
            toggle_actions(self._plugin_actions, visible)
        self._isvisible = enable and visible
        if self._isvisible:
            self.refresh_plugin()

    def _refresh_actions(self):
        """Refresh Options menu."""
        self._options_menu.clear()

        # Decide what additional actions to show
        if self._undocked_window is None:
            additional_actions = [MENU_SEPARATOR,
                                  self._undock_action,
                                  self._close_plugin_action]
        else:
            additional_actions = [MENU_SEPARATOR,
                                  self._dock_action]

        # Create actions list
        self._plugin_actions = self.get_plugin_actions() + additional_actions
        add_actions(self._options_menu, self._plugin_actions)

        if sys.platform == 'darwin':
            set_menu_icons(self._options_menu, True)

    def _setup(self):
        """
        Setup Options menu, create toggle action and connect signals.
        """
        # Creat toggle view action
        self._create_toggle_view_action()

        # Create Options menu
        self._plugin_actions = self.get_plugin_actions() + [MENU_SEPARATOR,
                                                            self._undock_action]
        add_actions(self._options_menu, self._plugin_actions)
        self.options_button.setMenu(self._options_menu)
        self._options_menu.aboutToShow.connect(self._refresh_actions)

        # Show icons in Mac plugin menus
        if sys.platform == 'darwin':
            self._options_menu.aboutToHide.connect(
                lambda menu=self._options_menu:
                set_menu_icons(menu, False))

        # Update title
        self.sig_update_plugin_title.connect(self._update_plugin_title)
        self.setWindowTitle(self.get_plugin_title())

    def _register_shortcut(self, qaction_or_qshortcut, context, name,
                           add_shortcut_to_tip=False):
        """Register a shortcut associated to a QAction or QShortcut."""
        self.main.register_shortcut(
            qaction_or_qshortcut,
            context,
            name,
            add_shortcut_to_tip,
            self.CONF_SECTION)

    def _get_color_scheme(self):
        """Get the current color scheme."""
        return get_color_scheme(CONF.get('appearance', 'selected'))

    def _add_dockwidget(self):
        """Add dockwidget to the main window and set it up."""
        self.main.add_dockwidget(self)

        # This is not necessary for the Editor because it calls
        # _setup directly on init.
        if self.CONF_SECTION != 'editor':
            self._setup()

    def _tabify(self, core_plugin):
        """Tabify plugin next to a core plugin."""
        self.main.tabify_plugins(core_plugin, self)
