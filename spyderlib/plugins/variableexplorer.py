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
        self.shellwidgets = {}
        
    #------ Public API ---------------------------------------------------------
    def add_shellwidget(self, shellwidget):
        shellwidget_id = id(shellwidget)
        # Add shell only once: this method may be called two times in a row 
        # by the External console plugin (dev. convenience)
        from spyderlib.widgets.externalshell import systemshell
        if isinstance(shellwidget, systemshell.ExternalSystemShell):
            return
        if shellwidget_id not in self.shellwidgets:
            nsb = NamespaceBrowser(self)
            nsb.set_shellwidget(shellwidget)
            self.addWidget(nsb)
            self.shellwidgets[shellwidget_id] = nsb
            shellwidget.set_namespacebrowser(nsb)
        
    def remove_shellwidget(self, shellwidget_id):
        # If shellwidget_id is not in self.shellwidgets, it simply means
        # that shell was not a Python/IPython-based console (it was a terminal)
        if shellwidget_id in self.shellwidgets:
            nsb = self.shellwidgets.pop(shellwidget_id)
            self.removeWidget(nsb)
            nsb.close()
    
    def set_shellwidget(self, shellwidget):
        shellwidget_id = id(shellwidget)
        if shellwidget_id in self.shellwidgets:
            self.setCurrentWidget(self.shellwidgets[shellwidget_id])

    #------ SpyderPluginMixin API ---------------------------------------------
    def visibility_changed(self, enable):
        """DockWidget visibility has changed"""
        SpyderPluginMixin.visibility_changed(self, enable)
        for nsb in self.shellwidgets.values():
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
        