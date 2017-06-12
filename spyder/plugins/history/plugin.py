# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""Console History Plugin"""

# Third party imports
from qtpy.QtCore import Signal, Slot
from qtpy.QtWidgets import QInputDialog, QVBoxLayout


# Local imports
from spyder.config.base import _
from spyder.api.plugins import SpyderPluginWidget
from spyder.utils import icon_manager as ima
from spyder.utils.qthelpers import create_action

from spyder.plugins.history.confpage import HistoryConfigPage
from spyder.plugins.history.widgets import History


class HistoryLog(SpyderPluginWidget):
    """
    History log widget
    """
    CONF_SECTION = 'historylog'
    CONFIGWIDGET_CLASS = HistoryConfigPage
    focus_changed = Signal()
    
    def __init__(self, parent):
        SpyderPluginWidget.__init__(self, parent)

        self.menu_actions = None
        self.history = None

        self.dockviewer = None
        self.wrap_action = None

        # Initialize plugin
        self.initialize_plugin()

        self.history = History(self)
        self.history.set_menu_actions(self.menu_actions)
        self.history.focus_changed.connect(self.focus_changed)
        self.register_widget_shortcuts(self.history.find_widget)

        layout = QVBoxLayout()
        layout.addWidget(self.history)
        self.setLayout(layout)

    #------ SpyderPluginWidget API ---------------------------------------------
    def get_plugin_title(self):
        """Return widget title"""
        return _('History log')
    
    def get_plugin_icon(self):
        """Return widget icon"""
        return ima.icon('history')
    
    def get_focus_widget(self):
        """
        Return the widget to give focus to when
        this plugin's dockwidget is raised on top-level
        """
        return self.history.tabwidget.currentWidget()
        
    def closing_plugin(self, cancelable=False):
        """Perform actions before parent main window is closed"""
        return True

    def refresh_plugin(self):
        """Refresh widget."""
        self.history.refresh()

    def get_plugin_actions(self):
        """Return a list of actions related to plugin"""
        history_action = create_action(self, _("History..."),
                                       None, ima.icon('history'),
                                       _("Set history maximum entries"),
                                       triggered=self.change_history_depth)
        self.wrap_action = create_action(self, _("Wrap lines"),
                                    toggled=self.toggle_wrap_mode)
        self.wrap_action.setChecked( self.get_option('wrap') )
        self.menu_actions = [history_action, self.wrap_action]
        return self.menu_actions

    def on_first_registration(self):
        """Action to be performed on first plugin registration"""
        self.main.tabify_plugins(self.main.extconsole, self)
    
    def register_plugin(self):
        """Register plugin in Spyder's main window"""
        self.focus_changed.connect(self.main.plugin_focus_changed)
        self.main.add_dockwidget(self)
#        self.main.console.set_historylog(self)
        self.main.console.shell.refresh.connect(self.history.refresh)

    def update_font(self):
        """Update font from Preferences"""
        color_scheme = self.get_color_scheme()
        font = self.get_plugin_font()
        for editor in self.history.editors:
            editor.set_font(font, color_scheme)

    def apply_plugin_settings(self, options):
        """Apply configuration file's plugin settings"""
        color_scheme_n = 'color_scheme_name'
        color_scheme_o = self.get_color_scheme()
        font_n = 'plugin_font'
        font_o = self.get_plugin_font()
        wrap_n = 'wrap'
        wrap_o = self.get_option(wrap_n)
        self.wrap_action.setChecked(wrap_o)
        for editor in self.history.editors:
            if font_n in options:
                scs = color_scheme_o if color_scheme_n in options else None
                editor.set_font(font_o, scs)
            elif color_scheme_n in options:
                editor.set_color_scheme(color_scheme_o)
            if wrap_n in options:
                editor.toggle_wrap_mode(wrap_o)

    #------ Public API ---------------------------------------------------------
    def add_history(self, filename):
        """
        Add new history tab
        Slot for add_history signal emitted by shell instance
        """
        color_scheme = self.get_color_scheme()
        font = self.get_plugin_font()
        wrap = self.get_option('wrap')
        
        self.history.add_history(filename, color_scheme=color_scheme, font=font,
                               wrap=wrap)

    def append_to_history(self, filename, command):
        """
        Append an entry to history filename
        Slot for append_to_history signal emitted by shell instance
        """
        go_to_eof = self.get_option('go_to_eof')
        self.history.append_to_history(filename, command, go_to_eof)
    
    @Slot()
    def change_history_depth(self):
        "Change history max entries"""
        depth, valid = QInputDialog.getInt(self, _('History'),
                                       _('Maximum entries'),
                                       self.get_option('max_entries'),
                                       10, 10000)
        if valid:
            self.set_option('max_entries', depth)

    @Slot(bool)
    def toggle_wrap_mode(self, checked):
        """Toggle wrap mode"""
        if self.history is None:
            return
        for editor in self.history.editors:
            editor.toggle_wrap_mode(checked)
        self.set_option('wrap', checked)
