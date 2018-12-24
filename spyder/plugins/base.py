# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""
Base plugin class
"""

# Third party imports
import qdarkstyle
from qtpy.QtCore import Qt, Slot
from qtpy.QtGui import QKeySequence
from qtpy.QtWidgets import QDockWidget, QMainWindow, QShortcut

# Local imports
from spyder.config.base import _
from spyder.config.gui import is_dark_interface, get_font
from spyder.config.main import CONF
from spyder.py3compat import is_text_string
from spyder.utils import icon_manager as ima
from spyder.utils.qthelpers import create_action
from spyder.widgets.dock import SpyderDockWidget


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


class BasePluginMixin(object):
    """Basic functionality for Spyder plugin widgets."""

    ALLOWED_AREAS = Qt.AllDockWidgetAreas
    LOCATION = Qt.LeftDockWidgetArea
    FEATURES = QDockWidget.DockWidgetClosable | QDockWidget.DockWidgetMovable

    def __init__(self, parent=None):
        super(BasePluginMixin, self).__init__()

        # Additional actions
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

    def show_message(self, message, timeout=0):
        """Show message in main window's status bar"""
        self.main.statusBar().showMessage(message, timeout)

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
