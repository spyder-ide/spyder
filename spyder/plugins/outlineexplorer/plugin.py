# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""Outline Explorer Plugin

Data for outline are provided by the outlineexplorer data of
highlighter of assigned editor. For example, for Python files code editor uses
highlighter spyder.utils.syntaxhighlighters.PythonSH
"""

# Third party imports
from qtpy.QtWidgets import QVBoxLayout

# Local imports
from spyder.config.base import _
from spyder.api.plugins import SpyderPluginWidget
from spyder.py3compat import is_text_string
from spyder.utils import icon_manager as ima
from spyder.plugins.outlineexplorer.widgets import OutlineExplorerWidget


class OutlineExplorer(SpyderPluginWidget):
    """Outline Explorer plugin."""

    CONF_SECTION = 'outline_explorer'

    def __init__(self, parent=None):
        SpyderPluginWidget.__init__(self, parent)

        show_fullpath = self.get_option('show_fullpath')
        show_all_files = self.get_option('show_all_files')
        group_cells = self.get_option('group_cells')
        show_comments = self.get_option('show_comments')
        sort_files_alphabetically = self.get_option(
            'sort_files_alphabetically')

        self.explorer = OutlineExplorerWidget(
           self,
           show_fullpath=show_fullpath,
           show_all_files=show_all_files,
           group_cells=group_cells,
           show_comments=show_comments,
           sort_files_alphabetically=sort_files_alphabetically,
           options_button=self.options_button)
        layout = QVBoxLayout()
        layout.addWidget(self.explorer)
        self.setLayout(layout)

        # Menu as corner widget
        self.explorer.treewidget.header().hide()
        self.load_config()

        # Initialize plugin
        self.initialize_plugin()

    #------ SpyderPluginWidget API ---------------------------------------------    
    def get_plugin_title(self):
        """Return widget title"""
        return _("Outline")

    def get_plugin_icon(self):
        """Return widget icon"""
        return ima.icon('outline_explorer')
    
    def get_focus_widget(self):
        """
        Return the widget to give focus to when
        this plugin's dockwidget is raised on top-level
        """
        return self.explorer.treewidget
    
    def get_plugin_actions(self):
        """Return a list of actions related to plugin"""
        return self.explorer.treewidget.get_menu_actions()
    
    def register_plugin(self):
        """Register plugin in Spyder's main window"""
        self.main.restore_scrollbar_position.connect(
                                               self.restore_scrollbar_position)
        self.main.add_dockwidget(self)
        
    def refresh_plugin(self):
        """Refresh project explorer widget"""
        pass
        
    def closing_plugin(self, cancelable=False):
        """Perform actions before parent main window is closed"""
        self.save_config()
        return True

    #------ SpyderPluginMixin API ---------------------------------------------
    def visibility_changed(self, enable):
        """DockWidget visibility has changed"""
        super(SpyderPluginWidget, self).visibility_changed(enable)
        if enable:
            self.explorer.is_visible.emit()
            
    #------ Public API ---------------------------------------------------------
    def restore_scrollbar_position(self):
        """Restoring scrollbar position after main window is visible"""
        scrollbar_pos = self.get_option('scrollbar_position', None)
        if scrollbar_pos is not None:
            self.explorer.treewidget.set_scrollbar_position(scrollbar_pos)

    def save_config(self):
        """Save configuration: tree widget state"""
        for option, value in list(self.explorer.get_options().items()):
            self.set_option(option, value)
        self.set_option('expanded_state',
                        self.explorer.treewidget.get_expanded_state())
        self.set_option('scrollbar_position',
                        self.explorer.treewidget.get_scrollbar_position())
        
    def load_config(self):
        """Load configuration: tree widget state"""
        expanded_state = self.get_option('expanded_state', None)
        # Sometimes the expanded state option may be truncated in .ini file
        # (for an unknown reason), in this case it would be converted to a
        # string by 'userconfig':
        if is_text_string(expanded_state):
            expanded_state = None
        if expanded_state is not None:
            self.explorer.treewidget.set_expanded_state(expanded_state)
