# -*- coding: utf-8 -*-
#
# Copyright © 2009 Pierre Raybaut
# Licensed under the terms of the MIT License
# (see spyderlib/__init__.py for details)

"""Console History Plugin"""

from PyQt4.QtGui import QVBoxLayout, QFontDialog, QInputDialog

import sys
# For debugging purpose:
STDOUT = sys.stdout

# Local imports
from spyderlib.utils import encoding
from spyderlib.config import CONF, get_font, set_font
from spyderlib.utils.qthelpers import create_action
from spyderlib.plugins import ReadOnlyEditor


class HistoryLog(ReadOnlyEditor):
    """
    History log widget
    """
    ID = 'historylog'
    def __init__(self, parent):
        self.filename = None
        ReadOnlyEditor.__init__(self, parent)
        layout = QVBoxLayout()
        layout.addWidget(self.editor)
        layout.addWidget(self.find_widget)
        self.setLayout(layout)
            
    #------ SpyderPluginWidget API ---------------------------------------------    
    def get_plugin_title(self):
        """Return widget title"""
        return self.tr('History log')
    
    def get_focus_widget(self):
        """
        Return the widget to give focus to when
        this plugin's dockwidget is raised on top-level
        """
        return self.editor
        
    def closing_plugin(self, cancelable=False):
        """Perform actions before parent main window is closed"""
        return True
    
    def refresh_plugin(self):
        """Refresh tabwidget"""
        self.find_widget.set_editor(self.editor)
        
    def get_plugin_actions(self):
        """Setup actions"""
        history_action = create_action(self, self.tr("History..."),
                                       None, 'history.png',
                                       self.tr("Set history maximum entries"),
                                       triggered=self.change_history_depth)
        font_action = create_action(self, self.tr("&Font..."), None,
                                    'font.png', self.tr("Set shell font style"),
                                    triggered=self.change_font)
        wrap_action = create_action(self, self.tr("Wrap lines"),
                                    toggled=self.toggle_wrap_mode)
        wrap_action.setChecked( CONF.get(self.ID, 'wrap') )
        self.menu_actions = [history_action, font_action, wrap_action]
        return (self.menu_actions, None)
        
    #------ Public API ---------------------------------------------------------
    def add_history(self, filename):
        """
        Add new history tab
        Slot for SIGNAL('add_history(QString)') emitted by shell instance
        """
        filename = encoding.to_unicode(filename)
        if filename == self.filename:
            return
        self.filename = filename
        text, _ = encoding.read(filename)
        self.editor.set_text(text)
        self.editor.set_cursor_position('eof')
        self.find_widget.set_editor(self.editor)
        
    def append_to_history(self, filename, command):
        """
        Append an entry to history filename
        Slot for SIGNAL('append_to_history(QString,QString)')
        emitted by shell instance
        """
        filename, command = encoding.to_unicode(filename), unicode(command)
        self.editor.append(command)
        self.editor.set_cursor_position('eof')
        
    def change_history_depth(self):
        "Change history max entries"""
        depth, valid = QInputDialog.getInteger(self, self.tr('History'),
                                       self.tr('Maximum entries'),
                                       CONF.get(self.ID, 'max_entries'),
                                       10, 10000)
        if valid:
            CONF.set(self.ID, 'max_entries', depth)
        
    def change_font(self):
        """Change console font"""
        font, valid = QFontDialog.getFont(get_font(self.ID),
                       self, self.tr("Select a new font"))
        if valid:
            self.editor.set_font(font)
            set_font(font, self.ID)
            
    def toggle_wrap_mode(self, checked):
        """Toggle wrap mode"""
        if self.editor is not None:
            self.editor.toggle_wrap_mode(checked)
            CONF.set(self.ID, 'wrap', checked)
