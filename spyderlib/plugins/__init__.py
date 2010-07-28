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
                         QKeySequence, QMainWindow, QApplication, QCheckBox,
                         QMessageBox, QLabel, QLineEdit, QSpinBox, QVBoxLayout,
                         QHBoxLayout, QPushButton)
from PyQt4.QtCore import SIGNAL, Qt, QObject

import sys

# For debugging purpose:
STDOUT = sys.stdout

# Local imports
from spyderlib.utils.qthelpers import (toggle_actions, create_action,
                                       add_actions, translate)
from spyderlib.config import CONF, get_font, set_font, get_icon
from spyderlib.userconfig import NoDefault
from spyderlib.plugins.configdialog import ConfigPage
from spyderlib.widgets.editor import CodeEditor
from spyderlib.widgets.findreplace import FindReplace


class PluginConfigPage(ConfigPage):
    """Plugin configuration dialog box page widget"""
    def __init__(self, plugin, parent):
        self.is_modified = False
        self.plugin = plugin
        self.get_option = self.plugin.get_option
        self.set_option = self.plugin.set_option
        ConfigPage.__init__(self, parent,
                            apply_callback=plugin.apply_plugin_settings)
        self.checkboxes = {}
        self.lineedits = {}
        self.spinboxes = {}
        
    def get_name(self):
        """Return page name"""
        return self.plugin.get_plugin_title()
    
    def get_icon(self):
        """Return page icon"""
        return self.plugin.get_plugin_icon()
    
    def apply_changes(self):
        """Apply changes callback"""
        if self.is_modified:
            ConfigPage.apply_changes(self)
        
    def load_from_conf(self):
        """Load settings from configuration file"""
        for checkbox, (option, default) in self.checkboxes.items():
            checkbox.setChecked(self.get_option(option, default))
            self.connect(checkbox, SIGNAL("clicked(bool)"),
                         lambda checked: self.has_been_modified())
        for lineedit, (option, default) in self.lineedits.items():
            lineedit.setText(self.get_option(option, default))
            self.connect(lineedit, SIGNAL("textChanged(QString)"),
                         lambda text: self.has_been_modified())
        for spinbox, (option, default) in self.spinboxes.items():
            spinbox.setValue(self.get_option(option, default))
            self.connect(spinbox, SIGNAL('valueChanged(int)'),
                         lambda value: self.has_been_modified())
    
    def save_to_conf(self):
        """Save settings to configuration file"""
        for checkbox, (option, _default) in self.checkboxes.items():
            self.set_option(option, checkbox.isChecked())
        for lineedit, (option, _default) in self.lineedits.items():
            self.set_option(option, unicode(lineedit.text()))
        for spinbox, (option, _default) in self.spinboxes.items():
            self.set_option(option, spinbox.value())
    
    def has_been_modified(self):
        self.is_modified = True
    
    def create_checkbox(self, text, option, default=NoDefault,
                        tip=None, msg_warning=None, msg_info=None,
                        msg_if_enabled=False):
        checkbox = QCheckBox(text)
        if tip is not None:
            checkbox.setToolTip(tip)
        self.checkboxes[checkbox] = (option, default)
        if msg_warning is not None or msg_info is not None:
            def show_message(is_checked):
                if is_checked or not msg_if_enabled:
                    if msg_warning is not None:
                        QMessageBox.warning(self, self.get_name(),
                                            msg_warning, QMessageBox.Ok)
                    if msg_info is not None:
                        QMessageBox.information(self, self.get_name(),
                                                msg_info, QMessageBox.Ok)
            self.connect(checkbox, SIGNAL("clicked(bool)"), show_message)
        return checkbox
    
    def create_lineedit(self, text, option, default=NoDefault,
                        tip=None, alignment=Qt.Vertical):
        label = QLabel(text)
        label.setWordWrap(True)
        edit = QLineEdit()
        layout = QVBoxLayout() if alignment == Qt.Vertical else QHBoxLayout()
        layout.addWidget(label)
        layout.addWidget(edit)
        layout.setContentsMargins(0, 0, 0, 0)
        if tip:
            edit.setToolTip(tip)
        self.lineedits[edit] = (option, default)
        lineedit = QWidget(self)
        lineedit.setLayout(layout)
        return lineedit
    
    def create_spinbox(self, prefix, suffix, option, default=NoDefault,
                       min_=None, max_=None, step=None, tip=None):
        plabel = QLabel(prefix)
        slabel = QLabel(suffix)
        spinbox = QSpinBox()
        if min_ is not None:
            spinbox.setMinimum(min_)
        if max_ is not None:
            spinbox.setMaximum(max_)
        if step is not None:
            spinbox.setSingleStep(step)
        if tip is not None:
            spinbox.setToolTip(tip)
        self.spinboxes[spinbox] = (option, default)
        layout = QHBoxLayout()
        for subwidget in (plabel, spinbox, slabel):
            layout.addWidget(subwidget)
        layout.addStretch(1)
        layout.setContentsMargins(0, 0, 0, 0)
        widget = QWidget(self)
        widget.setLayout(layout)
        return widget
    
    def create_button(self, text, callback):
        btn = QPushButton(text)
        self.connect(btn, SIGNAL('clicked()'), callback)
        self.connect(btn, SIGNAL('clicked()'), self.has_been_modified)
        return btn
    
    def create_tab(self, *widgets):
        """Create simple tab widget page: widgets added in a vertical layout"""
        widget = QWidget()
        layout = QVBoxLayout()
        for widg in widgets:
            layout.addWidget(widg)
        layout.addStretch(1)
        widget.setLayout(layout)
        return widget


class SpyderPluginMixin(object):
    """
    Useful methods to bind widgets to the main window
    See SpyderPluginWidget class for required widget interface
    
    Signals:
        'option_changed'
            Example:
            self.emit(SIGNAL('option_changed'), 'show_all', checked)
        'show_message(QString,int)'
    """
    ID = None
    CONFIGWIDGET_CLASS = None
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
        assert self.ID is not None
        self.main = main
        self.plugin_actions = self.get_plugin_actions()
        self.dockwidget = None
        self.ismaximized = False
        QObject.connect(self, SIGNAL('option_changed'), self.set_option)
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
        short = self.get_option("shortcut", None)
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
    
    def create_configwidget(self, parent):
        """Create configuration dialog box page widget"""
        if self.CONFIGWIDGET_CLASS is not None:
            configwidget = self.CONFIGWIDGET_CLASS(self, parent)
            configwidget.initialize()
            return configwidget

    def apply_plugin_settings(self):
        """Apply configuration file's plugin settings"""
        raise NotImplementedError

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
        if visible:
            self.refresh_plugin() #XXX Is it a good idea?

    def set_option(self, option, value):
        """
        Set a plugin option in configuration file
        Use a SIGNAL to call it, e.g.:
        self.emit(SIGNAL('option_changed'), 'show_all', checked)
        """
        CONF.set(self.ID, option, value)

    def get_option(self, option, default=NoDefault):
        """Get a plugin option from configuration file"""
        return CONF.get(self.ID, option, default)
    
    def get_plugin_font(self, option=None):
        """Return plugin font option"""
        return get_font(self.ID, option)
    
    def set_plugin_font(self, font, option=None):
        """Set plugin font option"""
        set_font(font, self.ID, option)
        
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
    def __init__(self, parent):
        QWidget.__init__(self, parent)
        SpyderPluginMixin.__init__(self, parent)
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
                                 scrollflagarea=False)
        self.connect(self.editor, SIGNAL("focus_changed()"),
                     lambda: self.emit(SIGNAL("focus_changed()")))
        self.editor.setReadOnly(True)
        self.editor.set_font(self.get_plugin_font())
        self.editor.toggle_wrap_mode(self.get_option('wrap'))
        
        # Add entries to read-only editor context-menu
        font_action = create_action(self, translate("Editor", "&Font..."), None,
                                    'font.png',
                                    translate("Editor", "Set font style"),
                                    triggered=self.change_font)
        wrap_action = create_action(self, translate("Editor", "Wrap lines"),
                                    toggled=self.toggle_wrap_mode)
        wrap_action.setChecked(self.get_option('wrap'))
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
        self.set_option('wrap', checked)
