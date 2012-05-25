# -*- coding: utf-8 -*-
#
# Copyright © 2011 Pierre Raybaut
# Licensed under the terms of the MIT License
# (see spyderlib/__init__.py for details)

"""IPython v0.12+ Plugin"""

from spyderlib.qt.QtGui import QHBoxLayout, QMessageBox

# Local imports
from spyderlib.baseconfig import _
from spyderlib.widgets.ipython import IPythonApp
from spyderlib.plugins import SpyderPluginWidget


class IPythonPlugin(SpyderPluginWidget):
    """Find in files DockWidget"""
    CONF_SECTION = 'ipython'
    def __init__(self, parent, connection_file, kernel_widget_id, kernel_name):
        super(IPythonPlugin, self).__init__(parent)
        
        self.already_closed = False

        self.connection_file = connection_file
        self.kernel_widget_id = kernel_widget_id
        self.kernel_name = kernel_name
        
        self.ipython_widget = None
        
        # Initialize plugin
        self.initialize_plugin()
        
    def toggle(self, state):
        """Toggle widget visibility"""
        if self.dockwidget:
            self.dockwidget.setVisible(state)
        
    #------ SpyderPluginWidget API ---------------------------------------------
    def get_plugin_title(self):
        """Return widget title"""
        return _("IPython client (%s)") % self.kernel_name
    
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
        argv = ['--existing']+[self.connection_file]

        iapp = self.main.ipython_app
        if iapp is None:
            self.main.ipython_app = iapp = IPythonApp()
            iapp.initialize_all_except_qt(argv=argv)

        iapp.parse_command_line(argv=argv)
        exit_callback = self.close_client
        self.ipython_widget = iapp.new_frontend_from_existing(exit_callback)

        layout = QHBoxLayout()
        layout.addWidget(self.ipython_widget)
        self.setLayout(layout)

        self.main.add_ipython_frontend(self)
    
    def refresh_plugin(self):
        """Refresh widget"""
        pass
        
    def closing_plugin(self, cancelable=False):
        """Perform actions before parent main window is closed"""
        return True

    #------ Public API --------------------------------------------------------
    def close_client(self):
        """Closing IPython client and eventually the associated kernel"""
        if self.already_closed:
            return
        console = self.main.extconsole
        index = console.get_shell_index_from_id(self.kernel_widget_id)
        if index is not None:
            answer = QMessageBox.question(self, self.get_plugin_title(),
                            _("This IPython frontend will be closed.\n"
                              "Do you want to kill the associated kernel and "
                              "the all of its clients?"),
                            QMessageBox.Yes|QMessageBox.No|QMessageBox.Cancel)
            if answer == QMessageBox.Yes:
                console.close_console(index=index)
                self.main.close_related_ipython_frontends(self)
            elif answer == QMessageBox.Cancel:
                return
        self.already_closed = True
        
        self.main.remove_ipython_frontend(self)
