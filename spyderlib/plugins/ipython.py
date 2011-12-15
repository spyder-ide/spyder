# -*- coding: utf-8 -*-
#
# Copyright © 2011 Pierre Raybaut
# Licensed under the terms of the MIT License
# (see spyderlib/__init__.py for details)

"""IPython v0.11+ Plugin"""

from spyderlib.qt.QtGui import QHBoxLayout

# Local imports
from spyderlib.widgets.ipython import create_widget
from spyderlib.plugins import SpyderPluginWidget


class IPythonPlugin(SpyderPluginWidget):
    """Find in files DockWidget"""
    CONF_SECTION = 'ipython'
    def __init__(self, parent, args, kernel_widget, kernel_name):
        super(IPythonPlugin, self).__init__(parent)

        self.kernel_widget = kernel_widget
        self.kernel_name = kernel_name
        
        self.ipython_widget = create_widget(argv=args.split())

        layout = QHBoxLayout()
        layout.addWidget(self.ipython_widget)
        self.setLayout(layout)
        
        # Initialize plugin
        self.initialize_plugin()
        
    def toggle(self, state):
        """Toggle widget visibility"""
        if self.dockwidget:
            self.dockwidget.setVisible(state)
        
    #------ SpyderPluginWidget API ---------------------------------------------    
    def get_plugin_title(self):
        """Return widget title"""
        return "IPython (%s) - Experimental!" % self.kernel_name
    
    def get_focus_widget(self):
        """
        Return the widget to give focus to when
        this plugin's dockwidget is raised on top-level
        """
        return self.ipython_widget._control
    
    def get_plugin_actions(self):
        """Return a list of actions related to plugin"""
        return []
    
    def register_plugin(self):
        """Register plugin in Spyder's main window"""
        self.main.add_dockwidget(self)
    
    def refresh_plugin(self):
        """Refresh widget"""
        pass
        
    def closing_plugin(self, cancelable=False):
        """Perform actions before parent main window is closed"""
        return True
