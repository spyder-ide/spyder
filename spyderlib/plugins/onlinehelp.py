# -*- coding: utf-8 -*-
#
# Copyright © 2009 Pierre Raybaut
# Licensed under the terms of the MIT License
# (see spyderlib/__init__.py for details)

"""Online Help Plugin"""

import sys, os.path as osp

# For debugging purpose:
STDOUT = sys.stdout

# Local imports
from spyderlib.config import CONF, get_conf_path
from spyderlib.widgets.pydocgui import PydocBrowser
from spyderlib.plugins import SpyderPluginMixin


class OnlineHelp(PydocBrowser, SpyderPluginMixin):
    """
    Online Help Plugin
    """
    ID = 'onlinehelp'
    LOG_PATH = get_conf_path('.onlinehelp')
    def __init__(self, parent):
        PydocBrowser.__init__(self, parent)
        SpyderPluginMixin.__init__(self, parent)
        
        self.set_zoom_factor(CONF.get(self.ID, 'zoom_factor'))
        self.url_combo.setMaxCount(CONF.get(self.ID, 'max_history_entries'))
        self.url_combo.addItems( self.load_history() )
        
    #------ Public API ---------------------------------------------------------
    def load_history(self, obj=None):
        """Load history from a text file in user home directory"""
        if osp.isfile(self.LOG_PATH):
            history = [line.replace('\n','')
                       for line in file(self.LOG_PATH, 'r').readlines()]
        else:
            history = []
        return history
    
    def save_history(self):
        """Save history to a text file in user home directory"""
        file(self.LOG_PATH, 'w').write("\n".join( \
            [ unicode( self.url_combo.itemText(index) )
                for index in range(self.url_combo.count()) ] ))

    #------ SpyderPluginMixin API ---------------------------------------------
    def visibility_changed(self, enable):
        """DockWidget visibility has changed"""
        SpyderPluginMixin.visibility_changed(self, enable)
        if enable and not self.is_server_running():
            self.initialize()
    
    #------ SpyderPluginWidget API ---------------------------------------------
    def get_plugin_title(self):
        """Return widget title"""
        return self.tr('Online help')
    
    def get_focus_widget(self):
        """
        Return the widget to give focus to when
        this plugin's dockwidget is raised on top-level
        """
        self.url_combo.lineEdit().selectAll()
        return self.url_combo
        
    def closing_plugin(self, cancelable=False):
        """Perform actions before parent main window is closed"""
        self.save_history()
        CONF.set(self.ID, 'zoom_factor', self.get_zoom_factor())
        return True
        
    def refresh_plugin(self):
        """Refresh widget"""
        pass
    
    def get_plugin_actions(self):
        """Setup actions"""
        # Return menu and toolbar actions
        return (None, None)
        