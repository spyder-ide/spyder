# -*- coding: utf-8 -*-
#
# Copyright © 2009 Pierre Raybaut
# Licensed under the terms of the MIT License
# (see spyderlib/__init__.py for details)

"""Console History Plugin"""

from PyQt4.QtGui import (QVBoxLayout, QFontDialog, QInputDialog, QToolButton,
                         QMenu)
from PyQt4.QtCore import SIGNAL

import os.path as osp

import sys
# For debugging purpose:
STDOUT = sys.stdout

# Local imports
from spyderlib.utils import encoding
from spyderlib.config import CONF, get_font, get_icon, set_font
from spyderlib.utils.qthelpers import (create_action, create_toolbutton,
                                       add_actions)
from spyderlib.widgets.tabs import Tabs
from spyderlib.widgets.editor import CodeEditor
from spyderlib.widgets.findreplace import FindReplace
from spyderlib.plugins import SpyderPluginWidget


class HistoryLog(SpyderPluginWidget):
    """
    History log widget
    """
    ID = 'historylog'
    def __init__(self, parent):
        self.tabwidget = None
        self.menu_actions = None
        self.dockviewer = None
        
        self.editors = []
        self.filenames = []
        self.icons = []
        
        SpyderPluginWidget.__init__(self, parent)
        
        layout = QVBoxLayout()
        self.tabwidget = Tabs(self, self.menu_actions)
        self.connect(self.tabwidget, SIGNAL('currentChanged(int)'),
                     self.refresh_plugin)
        self.connect(self.tabwidget, SIGNAL('move_data(int,int)'),
                     self.move_tab)
        layout.addWidget(self.tabwidget)

        # Menu as corner widget
        options_button = create_toolbutton(self, text=self.tr("Options"),
                                           icon=get_icon('tooloptions.png'))
        options_button.setPopupMode(QToolButton.InstantPopup)
        menu = QMenu(self)
        add_actions(menu, self.menu_actions)
        options_button.setMenu(menu)
        self.tabwidget.setCornerWidget(options_button)
        
        # Find/replace widget
        self.find_widget = FindReplace(self)
        self.find_widget.hide()
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
        return self.tabwidget.currentWidget()
        
    def closing_plugin(self, cancelable=False):
        """Perform actions before parent main window is closed"""
        return True
    
    def refresh_plugin(self):
        """Refresh tabwidget"""
        if self.tabwidget.count():
            editor = self.tabwidget.currentWidget()
        else:
            editor = None
        self.find_widget.set_editor(editor)
        
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
        
    #------ Private API --------------------------------------------------------
    def move_tab(self, index_from, index_to):
        """
        Move tab (tabs themselves have already been moved by the tabwidget)
        """
        filename = self.filenames.pop(index_from)
        editor = self.editors.pop(index_from)
        icon = self.icons.pop(index_from)
        
        self.filenames.insert(index_to, filename)
        self.editors.insert(index_to, editor)
        self.icons.insert(index_to, icon)
        
    #------ Public API ---------------------------------------------------------
    def add_history(self, filename):
        """
        Add new history tab
        Slot for SIGNAL('add_history(QString)') emitted by shell instance
        """
        filename = encoding.to_unicode(filename)
        if filename in self.filenames:
            return
        editor = CodeEditor(self)
        if osp.splitext(filename)[1] == '.py':
            language = 'py'
            icon = get_icon('python.png')
        else:
            language = 'bat'
            icon = get_icon('cmdprompt.png')
        editor.setup_editor(linenumbers=False, language=language,
                            code_folding=True, scrollflagarea=False)
        self.connect(editor, SIGNAL("focus_changed()"),
                     lambda: self.emit(SIGNAL("focus_changed()")))
        editor.setReadOnly(True)
        editor.set_font( get_font(self.ID) )
        editor.toggle_wrap_mode( CONF.get(self.ID, 'wrap') )

        text, _ = encoding.read(filename)
        editor.set_text(text)
        editor.set_cursor_position('eof')
        
        self.editors.append(editor)
        self.filenames.append(filename)
        self.icons.append(icon)
        index = self.tabwidget.addTab(editor, osp.basename(filename))
        self.find_widget.set_editor(editor)
        self.tabwidget.setTabToolTip(index, filename)
        self.tabwidget.setTabIcon(index, icon)
        self.tabwidget.setCurrentIndex(index)
        
    def append_to_history(self, filename, command):
        """
        Append an entry to history filename
        Slot for SIGNAL('append_to_history(QString,QString)')
        emitted by shell instance
        """
        filename, command = encoding.to_unicode(filename), unicode(command)
        index = self.filenames.index(filename)
        self.editors[index].append(command)
        self.editors[index].set_cursor_position('eof')
        self.tabwidget.setCurrentIndex(index)
        
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
            for editor in self.editors:
                editor.set_font(font)
            set_font(font, self.ID)
            
    def toggle_wrap_mode(self, checked):
        """Toggle wrap mode"""
        if self.tabwidget is None:
            return
        for editor in self.editors:
            editor.toggle_wrap_mode(checked)
        CONF.set(self.ID, 'wrap', checked)
