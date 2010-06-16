# -*- coding: utf-8 -*-
#
# Copyright © 2009 Pierre Raybaut
# Licensed under the terms of the MIT License
# (see spyderlib/__init__.py for details)

"""Namespace Browser Plugin"""

import sys

from PyQt4.QtGui import QStackedWidget

# For debugging purpose:
STDOUT = sys.stdout

# Local imports
from spyderlib.config import CONF
from spyderlib.plugins import SpyderPluginMixin
from spyderlib.widgets.externalshell.namespacebrowser import NamespaceBrowser


class VariableExplorer(QStackedWidget, SpyderPluginMixin):
    """
    Variable Explorer Plugin
    """
    ID = 'variable_explorer'
    def __init__(self, parent):
        QStackedWidget.__init__(self, parent)
        SpyderPluginMixin.__init__(self, parent)
        self.shells = {}
        
    #------ Public API ---------------------------------------------------------
    def add_shell(self, shell):
        shell_id = id(shell)
        nsb = NamespaceBrowser(self)
        nsb.set_shell(shell)
        self.addWidget(nsb)
        self.shells[shell_id] = nsb
        shell.set_namespacebrowser(nsb)
        
    def remove_shell(self, shell_id):
        nsb = self.shells.pop(shell_id)
        self.removeWidget(nsb)
        nsb.close()
    
    def set_shell(self, shell):
        shell_id = id(shell)
        if shell_id in self.shells:
            self.setCurrentWidget(self.shells[shell_id])

    #------ SpyderPluginMixin API ---------------------------------------------
    def visibility_changed(self, enable):
        """DockWidget visibility has changed"""
        SpyderPluginMixin.visibility_changed(self, enable)
        for nsb in self.shells.values():
            nsb.visibility_changed(enable and nsb is self.currentWidget())
    
    #------ SpyderPluginWidget API ---------------------------------------------
    def get_plugin_title(self):
        """Return widget title"""
        return self.tr('Variable explorer')
    
    def get_focus_widget(self):
        """
        Return the widget to give focus to when
        this plugin's dockwidget is raised on top-level
        """
        return self.currentWidget()
        
    def closing_plugin(self, cancelable=False):
        """Perform actions before parent main window is closed"""
        return True
        
    def refresh_plugin(self):
        """Refresh widget"""
        pass
    
    def get_plugin_actions(self):
        """Setup actions"""
        # Return menu and toolbar actions
        return (None, None)
        