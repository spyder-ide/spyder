# -*- coding: utf-8 -*-
#
# Copyright © 2009-2010 Pierre Raybaut
# Licensed under the terms of the MIT License
# (see spyderlib/__init__.py for details)

"""
spyderlib.plugins
=================

Here, 'plugins' are widgets designed specifically for Spyder
These plugins inherit the following classes
(SpyderPluginMixin & SpyderPluginWidget)
"""

# pylint: disable=C0103
# pylint: disable=R0903
# pylint: disable=R0911
# pylint: disable=R0201

from spyderlib.qt.QtGui import (QDockWidget, QWidget, QShortcut, QCursor,
                                QKeySequence, QMainWindow, QApplication)
from spyderlib.qt.QtCore import SIGNAL, Qt, QObject, Signal

import sys

# Local imports
from spyderlib.utils.qthelpers import toggle_actions, get_icon, create_action
from spyderlib.baseconfig import _
from spyderlib.config import CONF
from spyderlib.userconfig import NoDefault
from spyderlib.guiconfig import get_font, set_font
from spyderlib.plugins.configdialog import SpyderConfigPage
from spyderlib.py3compat import configparser, is_text_string


class PluginConfigPage(SpyderConfigPage):
    """Plugin configuration dialog box page widget"""
    def __init__(self, plugin, parent):
        self.plugin = plugin
        self.get_option = plugin.get_option
        self.set_option = plugin.set_option
        self.get_font = plugin.get_plugin_font
        self.set_font = plugin.set_plugin_font
        self.apply_settings = plugin.apply_plugin_settings
        SpyderConfigPage.__init__(self, parent)
    
    def get_name(self):
        return self.plugin.get_plugin_title()

    def get_icon(self):
        return self.plugin.get_plugin_icon()


class SpyderDockWidget(QDockWidget):
    """Subclass to override needed methods"""

    def closeEvent(self, event):
        """
        Reimplement Qt method to send a signal on close so that "Panes" main
        window menu can be updated correctly
        """
        self.emit(SIGNAL('plugin_closed()'))


class SpyderPluginMixin(object):
    """
    Useful methods to bind widgets to the main window
    See SpyderPluginWidget class for required widget interface
    
    Signals:
        sig_option_changed
            Example:
            plugin.sig_option_changed.emit('show_all', checked)
        'show_message(QString,int)'
    """
    CONF_SECTION = None
    CONFIGWIDGET_CLASS = None
    ALLOWED_AREAS = Qt.AllDockWidgetAreas
    LOCATION = Qt.LeftDockWidgetArea
    FEATURES = QDockWidget.DockWidgetClosable | \
               QDockWidget.DockWidgetFloatable | \
               QDockWidget.DockWidgetMovable
    DISABLE_ACTIONS_WHEN_HIDDEN = True
    sig_option_changed = None
    def __init__(self, main):
        """Bind widget to a QMainWindow instance"""
        super(SpyderPluginMixin, self).__init__()
        assert self.CONF_SECTION is not None
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
            self.shortcut = None

        # We decided to create our own toggle action instead of using
        # the one that comes with dockwidget because it's not possible
        # to raise and focus the plugin with it.
        self.toggle_view_action = None
        
    def initialize_plugin(self):
        """Initialize plugin: connect signals, setup actions, ..."""
        self.plugin_actions = self.get_plugin_actions()
        QObject.connect(self, SIGNAL('show_message(QString,int)'),
                        self.show_message)
        QObject.connect(self, SIGNAL('update_plugin_title()'),
                        self.__update_plugin_title)
        if self.sig_option_changed is not None:
            self.sig_option_changed.connect(self.set_option)
        self.setWindowTitle(self.get_plugin_title())
        self.create_toggle_view_action()

    def on_first_registration(self):
        """Action to be performed on first plugin registration"""
        # Was written to handle the very first plugin position in Spyder's
        # main window layout, but this could also be used for other things
        # (see for example the IPython console plugin for which this method 
        #  had to be written to handle the fact that this plugin was 
        #  introduced between v2.1 and v2.2)
        raise NotImplementedError

    def initialize_plugin_in_mainwindow_layout(self):
        """If this is the first time the plugin is shown, perform actions to
        initialize plugin position in Spyder's window layout"""
        if self.get_option('first_time', True):
            try:
                self.on_first_registration()
            except NotImplementedError:
                return
            self.set_option('first_time', False)
        
    def update_margins(self):
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
        self.connect(dock, SIGNAL('visibilityChanged(bool)'),
                     self.visibility_changed)
        self.connect(dock, SIGNAL('plugin_closed()'),
                     self.plugin_closed)
        self.dockwidget = dock
        if self.shortcut is not None:
            sc = QShortcut(QKeySequence(self.shortcut), self.main,
                            self.switch_to_plugin)
            self.register_shortcut(sc, "_", "Switch to %s" % self.CONF_SECTION)
        return (dock, self.LOCATION)
    
    def create_mainwindow(self):
        """
        Create a QMainWindow instance containing this plugin
        Note: this method is currently not used
        """
        self.mainwindow = mainwindow = QMainWindow()
        mainwindow.setAttribute(Qt.WA_DeleteOnClose)
        icon = self.get_widget_icon()
        if is_text_string(icon):
            icon = get_icon(icon)
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

    def apply_plugin_settings(self, options):
        """Apply configuration file's plugin settings"""
        raise NotImplementedError
    
    def register_shortcut(self, qaction_or_qshortcut, context, name,
                          default=NoDefault):
        """
        Register QAction or QShortcut to Spyder main application,
        with shortcut (context, name, default)
        """
        self.main.register_shortcut(qaction_or_qshortcut,
                                    context, name, default)
        
    def register_widget_shortcuts(self, context, widget):
        """
        Register widget shortcuts
        widget interface must have a method called 'get_shortcut_data'
        """
        for qshortcut, name, default in widget.get_shortcut_data():
            self.register_shortcut(qshortcut, context, name, default)
    
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
    
    def get_plugin_font(self, option=None):
        """Return plugin font option"""
        return get_font(self.CONF_SECTION, option)
    
    def set_plugin_font(self, font, option=None):
        """Set plugin font option"""
        set_font(font, self.CONF_SECTION, option)
        
    def show_message(self, message, timeout=0):
        """Show message in main window's status bar"""
        self.main.statusBar().showMessage(message, timeout)

    def starting_long_process(self, message):
        """
        Showing message in main window's status bar
        and changing mouse cursor to Qt.WaitCursor
        """
        self.show_message(message)
        QApplication.setOverrideCursor(QCursor(Qt.WaitCursor))
        QApplication.processEvents()
        
    def ending_long_process(self, message=""):
        """
        Clearing main window's status bar
        and restoring mouse cursor
        """
        QApplication.restoreOverrideCursor()
        self.show_message(message, timeout=2000)
        QApplication.processEvents()
        
    def set_default_color_scheme(self, name='Spyder'):
        """Set default color scheme (only once)"""
        color_scheme_name = self.get_option('color_scheme_name', None)
        if color_scheme_name is None:
            names = CONF.get("color_schemes", "names")
            if name not in names:
                name = names[0]
            self.set_option('color_scheme_name', name)
    
    def create_toggle_view_action(self):
        """Associate a toggle view action with each plugin"""
        title = self.get_plugin_title()
        if self.CONF_SECTION == 'editor':
            title = _('Editor')
        if self.shortcut is not None:
            action = create_action(self, title, toggled=self.toggle_view,
                                   shortcut=QKeySequence(self.shortcut))
            action.setShortcutContext(Qt.WidgetWithChildrenShortcut)
        else:
            action = create_action(self, title, toggled=self.toggle_view)
        self.toggle_view_action = action
    
    def toggle_view(self, checked):
        """Toggle view"""
        if checked:
            self.dockwidget.show()
            self.dockwidget.raise_()
        else:
            self.dockwidget.hide()


class SpyderPluginWidget(QWidget, SpyderPluginMixin):
    """
    Spyder base widget class
    Spyder's widgets either inherit this class or reimplement its interface
    """
    sig_option_changed = Signal(str, object)
    
    def __init__(self, parent):
        QWidget.__init__(self, parent)
        SpyderPluginMixin.__init__(self, parent)
        
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
        return get_icon('qt.png')
    
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
        raise NotImplementedError
        
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
