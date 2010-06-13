# -*- coding: utf-8 -*-
#
# Copyright © 2009 Pierre Raybaut
# Licensed under the terms of the MIT License
# (see spyderlib/__init__.py for details)

"""
spyderlib.plugins
=================

Here, 'plugins' are widgets designed specifically for Spyder
These plugins inherit the following classes
(SpyderPluginMixin & SpyderPluginWidget)
"""

# pylint: disable-msg=C0103
# pylint: disable-msg=R0903
# pylint: disable-msg=R0911
# pylint: disable-msg=R0201

from PyQt4.QtGui import (QDockWidget, QWidget, QFontDialog, QShortcut, QCursor,
                         QKeySequence, QMainWindow, QApplication)
from PyQt4.QtCore import SIGNAL, Qt, QObject

import sys

# For debugging purpose:
STDOUT = sys.stdout

# Local imports
from spyderlib.utils.qthelpers import (toggle_actions, create_action,
                                       add_actions, translate)
from spyderlib.config import CONF, get_font, set_font, get_icon
from spyderlib.widgets.editor import CodeEditor
from spyderlib.widgets.findreplace import FindReplace


class SpyderPluginMixin(object):
    """
    Useful methods to bind widgets to the main window
    See SpyderPluginWidget class for required widget interface
    """
    FLAGS = Qt.Window
    ALLOWED_AREAS = Qt.AllDockWidgetAreas
    LOCATION = Qt.LeftDockWidgetArea
    FEATURES = QDockWidget.DockWidgetClosable | \
               QDockWidget.DockWidgetFloatable | \
               QDockWidget.DockWidgetMovable
    DISABLE_ACTIONS_WHEN_HIDDEN = True
    def __init__(self, main):
        """Bind widget to a QMainWindow instance"""
        super(SpyderPluginMixin, self).__init__()
        self.main = main
        self.menu_actions, self.toolbar_actions = self.get_plugin_actions()
        self.dockwidget = None
        self.ismaximized = False
        QObject.connect(self, SIGNAL('option_changed'), self.option_changed)
        QObject.connect(self, SIGNAL('show_message(QString,int)'),
                        self.show_message)
        
    def create_dockwidget(self):
        """Add to parent QMainWindow as a dock widget"""
        dock = QDockWidget(self.get_plugin_title(), self.main)#, self.FLAGS) -> bug in Qt 4.4
        dock.setObjectName(self.__class__.__name__+"_dw")
        dock.setAllowedAreas(self.ALLOWED_AREAS)
        dock.setFeatures(self.FEATURES)
        dock.setWidget(self)
        self.connect(dock, SIGNAL('visibilityChanged(bool)'),
                     self.visibility_changed)
        self.dockwidget = dock
        self.refresh_plugin()
        short = CONF.get(self.ID, "shortcut", None)
        if short is not None:
            QShortcut(QKeySequence(short), self.main,
                      lambda: self.visibility_changed(True))
        return (dock, self.LOCATION)
    
    def create_mainwindow(self):
        """
        Create a QMainWindow instance containing this plugin
        Note: this method is currently not used
        """
        mainwindow = QMainWindow()
        mainwindow.setAttribute(Qt.WA_DeleteOnClose)
        icon = self.get_widget_icon()
        if isinstance(icon, basestring):
            icon = get_icon(icon)
        mainwindow.setWindowIcon(icon)
        mainwindow.setWindowTitle(self.get_plugin_title())
        mainwindow.setCentralWidget(self)
        self.refresh_plugin()
        return mainwindow

    def visibility_changed(self, enable):
        """DockWidget visibility has changed"""
        if enable:
            self.dockwidget.raise_()
            widget = self.get_focus_widget()
            if widget is not None:
                widget.setFocus()
        visible = self.dockwidget.isVisible() or self.ismaximized
        if self.DISABLE_ACTIONS_WHEN_HIDDEN:
            toggle_actions(self.menu_actions, visible)
            toggle_actions(self.toolbar_actions, visible)
        if visible:
            self.refresh_plugin() #XXX Is it a good idea?

    def option_changed(self, option, value):
        """
        Change a plugin option in configuration file
        Use a SIGNAL to call it, e.g.:
        self.emit(SIGNAL('option_changed'), 'show_all', checked)
        """
        CONF.set(self.ID, option, value)
        
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


class SpyderPluginWidget(QWidget, SpyderPluginMixin):
    """
    Spyder base widget class
    Spyder's widgets either inherit this class or reimplement its interface
    """
    ID = None
    def __init__(self, parent):
        QWidget.__init__(self, parent)
        SpyderPluginMixin.__init__(self, parent)
        assert self.ID is not None
        self.setWindowTitle(self.get_plugin_title())
        
    def get_plugin_title(self):
        """
        Return plugin title
        Note: after some thinking, it appears that using a method
        is more flexible here than using a class attribute
        """
        raise NotImplementedError
    
    def get_plugin_icon(self):
        """
        Return plugin icon name (e.g.: qt.png) or QIcon instance
        Note: this is required only for plugins creating a main window
              (see SpyderPluginMixin.create_mainwindow)
        """
        return 'qt.png'
    
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
        Setup actions and return a tuple (menu_actions, toolbar_actions)
        (each tuple element contains a list of QAction objects or None)
        """
        raise NotImplementedError


class ReadOnlyEditor(SpyderPluginWidget):
    """
    Read-only editor plugin widget
    (see example of child class in inspector.py)
    """
    def __init__(self, parent):
        self.editor = None
        
        SpyderPluginWidget.__init__(self, parent)

        # Read-only editor
        self.editor = CodeEditor(self)
        self.editor.setup_editor(linenumbers=False, language='py',
                                 code_folding=True, scrollflagarea=False)
        self.connect(self.editor, SIGNAL("focus_changed()"),
                     lambda: self.emit(SIGNAL("focus_changed()")))
        self.editor.setReadOnly(True)
        self.editor.set_font( get_font(self.ID) )
        self.editor.toggle_wrap_mode( CONF.get(self.ID, 'wrap') )
        
        # Add entries to read-only editor context-menu
        font_action = create_action(self, translate("Editor", "&Font..."), None,
                                    'font.png',
                                    translate("Editor", "Set font style"),
                                    triggered=self.change_font)
        wrap_action = create_action(self, translate("Editor", "Wrap lines"),
                                    toggled=self.toggle_wrap_mode)
        wrap_action.setChecked( CONF.get(self.ID, 'wrap') )
        self.editor.readonly_menu.addSeparator()
        add_actions(self.editor.readonly_menu, (font_action, wrap_action))
        
        # Find/replace widget
        self.find_widget = FindReplace(self)
        self.find_widget.set_editor(self.editor)
        self.find_widget.hide()
        
        # <!> Layout will have to be implemented in child class!
    
    def get_focus_widget(self):
        """
        Return the widget to give focus to when
        this plugin's dockwidget is raised on top-level
        """
        return self.editor
            
    def get_plugin_actions(self):
        """Setup and return actions"""
        return (None, None)
        
    def closing_plugin(self, cancelable=False):
        """Perform actions before parent main window is closed"""
        return True
        
    def change_font(self):
        """Change console font"""
        font, valid = QFontDialog.getFont(get_font(self.ID), self,
                                      translate("Editor", "Select a new font"))
        if valid:
            self.editor.set_font(font)
            set_font(font, self.ID)
            
    def toggle_wrap_mode(self, checked):
        """Toggle wrap mode"""
        self.editor.toggle_wrap_mode(checked)
        CONF.set(self.ID, 'wrap', checked)
