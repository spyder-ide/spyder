# -*- coding: utf-8 -*-
#
# Copyright © 2010 Pierre Raybaut
# Licensed under the terms of the MIT License
# (see spyderlib/__init__.py for details)

"""Project Explorer Plugin"""

from spyderlib.qt.QtGui import QFontDialog
from spyderlib.qt.QtCore import SIGNAL

# Local imports
from spyderlib.baseconfig import _
from spyderlib.utils.qthelpers import get_icon, create_action
from spyderlib.widgets.projectexplorer import ProjectExplorerWidget
from spyderlib.plugins import SpyderPluginMixin
from spyderlib.py3compat import is_text_string


class ProjectExplorer(ProjectExplorerWidget, SpyderPluginMixin):
    """Project explorer plugin"""
    CONF_SECTION = 'project_explorer'
    
    def __init__(self, parent=None):
        ProjectExplorerWidget.__init__(self, parent=parent,
                    name_filters=self.get_option('name_filters'),
                    show_all=self.get_option('show_all', False),
                    show_hscrollbar=self.get_option('show_hscrollbar'))
        SpyderPluginMixin.__init__(self, parent)

        # Initialize plugin
        self.initialize_plugin()

        self.treewidget.header().hide()
        self.set_font(self.get_plugin_font())
        self.load_config()
        
    #------ SpyderPluginWidget API ---------------------------------------------    
    def get_plugin_title(self):
        """Return widget title"""
        return _("Project explorer")
    
    def get_focus_widget(self):
        """
        Return the widget to give focus to when
        this plugin's dockwidget is raised on top-level
        """
        return self.treewidget
    
    def get_plugin_actions(self):
        """Return a list of actions related to plugin"""
        new_project_act = create_action(self, text=_('New project...'),
                                        icon=get_icon('project_expanded.png'),
                                        triggered=self.create_new_project)

        font_action = create_action(self, _("&Font..."),
                                    None, 'font.png', _("Set font style"),
                                    triggered=self.change_font)
        self.treewidget.common_actions += (None, font_action)
        
        self.main.file_menu_actions.insert(1, new_project_act)
        
        return []
    
    def register_plugin(self):
        """Register plugin in Spyder's main window"""
        self.main.pythonpath_changed()
        self.connect(self.main, SIGNAL('restore_scrollbar_position()'),
                     self.restore_scrollbar_position)
        self.connect(self, SIGNAL("pythonpath_changed()"),
                     self.main.pythonpath_changed)
        self.connect(self, SIGNAL("projects_were_closed()"),
                     self.projects_were_closed)
        self.connect(self, SIGNAL("create_module(QString)"),
                     self.main.editor.new)
        self.connect(self, SIGNAL("edit(QString)"), self.main.editor.load)
        self.connect(self, SIGNAL("removed(QString)"),
                     self.main.editor.removed)
        self.connect(self, SIGNAL("removed_tree(QString)"),
                     self.main.editor.removed_tree)
        self.connect(self, SIGNAL("renamed(QString,QString)"),
                     self.main.editor.renamed)
        self.main.editor.set_projectexplorer(self)
        self.main.add_dockwidget(self)

        self.sig_open_file.connect(self.main.open_file)
        
    def refresh_plugin(self):
        """Refresh project explorer widget"""
        pass
        
    def closing_plugin(self, cancelable=False):
        """Perform actions before parent main window is closed"""
        self.save_config()
        self.closing_widget()
        return True
        
    #------ Public API ---------------------------------------------------------
    def create_new_project(self):
        """Create new project"""
        if self.dockwidget.isHidden():
            self.dockwidget.show()
        self.dockwidget.raise_()
        if not self.treewidget.new_project():
            # Notify dockwidget to schedule a repaint
            self.dockwidget.update()

    def projects_were_closed(self):
        """Project were just closed: checking if related files are opened in 
        the editor and closing them"""
        for fname in self.main.editor.get_filenames():
            if self.treewidget.workspace.is_file_in_closed_project(fname):
                self.main.editor.close_file_from_name(fname)
        
    def change_font(self):
        """Change font"""
        font, valid = QFontDialog.getFont(self.get_plugin_font(), self,
                                          _("Select a new font"))
        if valid:
            self.set_font(font)
            self.set_plugin_font(font)
            
    def set_font(self, font):
        """Set project explorer widget font"""
        self.treewidget.setFont(font)
        
    def save_config(self):
        """Save configuration: opened projects & tree widget state"""
        self.set_option('workspace', self.get_workspace())
        self.set_option('expanded_state', self.treewidget.get_expanded_state())
        self.set_option('scrollbar_position',
                        self.treewidget.get_scrollbar_position())
        
    def load_config(self):
        """Load configuration: opened projects & tree widget state"""
        self.set_workspace(self.get_option('workspace', None))
        expanded_state = self.get_option('expanded_state', None)
        # Sometimes the expanded state option may be truncated in .ini file
        # (for an unknown reason), in this case it would be converted to a
        # string by 'userconfig':
        if is_text_string(expanded_state):
            expanded_state = None
        if expanded_state is not None:
            self.treewidget.set_expanded_state(expanded_state)
        
    def restore_scrollbar_position(self):
        """Restoring scrollbar position after main window is visible"""
        scrollbar_pos = self.get_option('scrollbar_position', None)
        if scrollbar_pos is not None:
            self.treewidget.set_scrollbar_position(scrollbar_pos)
