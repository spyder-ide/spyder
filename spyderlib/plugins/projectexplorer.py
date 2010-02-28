# -*- coding: utf-8 -*-
#
# Copyright © 2010 Pierre Raybaut
# Licensed under the terms of the MIT License
# (see spyderlib/__init__.py for details)

"""Project Explorer Plugin"""

from PyQt4.QtGui import QFontDialog
from PyQt4.QtCore import SIGNAL

import sys, cPickle, os.path as osp

# For debugging purpose:
STDOUT = sys.stdout

# Local imports
from spyderlib.config import get_font, set_font, get_conf_path, CONF
from spyderlib.utils.qthelpers import create_action
from spyderlib.widgets.projectexplorer import ProjectExplorerWidget
from spyderlib.plugins import PluginMixin


class ProjectExplorer(ProjectExplorerWidget, PluginMixin):
    """Python source code analysis based on pylint"""
    ID = 'project_explorer'
    DATAPATH = get_conf_path('.projects')
    def __init__(self, parent=None):
        include = CONF.get(self.ID, 'include', '.')
        exclude = CONF.get(self.ID, 'exclude', r'\.pyc$|\.pyo$|\.orig$|^\.')
        show_all = CONF.get(self.ID, 'show_all', False)
        ProjectExplorerWidget.__init__(self, parent=parent, include=include,
                                       exclude=exclude, show_all=show_all)
        PluginMixin.__init__(self, parent)

        self.editor_valid_types = None

        self.set_font(get_font(self.ID))
        
        if osp.isfile(self.DATAPATH):
            self.load_config()

        self.connect(self, SIGNAL("open_file(QString)"), self.open_file)
        
    def refresh(self):
        """Refresh project explorer widget"""
        pass
        
    def get_widget_title(self):
        """Return widget title"""
        return self.tr("Project explorer")
    
    def get_focus_widget(self):
        """
        Return the widget to give focus to when
        this plugin's dockwidget is raised on top-level
        """
        return self.treewidget
    
    def set_actions(self):
        """Setup actions"""
        font_action = create_action(self, self.tr("&Font..."),
                                    None, 'font.png', self.tr("Set font style"),
                                    triggered=self.change_font)
        self.treewidget.common_actions += (None, font_action)
        return (None, None)
        
    def closing(self, cancelable=False):
        """Perform actions before parent main window is closed"""
        self.save_config()
        return True
        
    def change_font(self):
        """Change font"""
        font, valid = QFontDialog.getFont(get_font(self.ID), self,
                                          self.tr("Select a new font"))
        if valid:
            self.set_font(font)
            set_font(font, self.ID)
            
    def set_font(self, font):
        """Set project explorer widget font"""
        self.treewidget.setFont(font)
        
    def save_config(self):
        """Save configuration: opened projects"""
        data = self.get_project_config()
        cPickle.dump(data, file(self.DATAPATH, 'w'))
        
    def load_config(self):
        data = cPickle.load(file(self.DATAPATH))
        self.set_project_config(data)
        
    def set_editor_valid_types(self, valid_types):
        self.editor_valid_types = valid_types
        self.treewidget.valid_types += valid_types

    def open_file(self, fname):
        """
        Open filename with the appropriate application
        Redirect to the right widget (txt -> editor, spydata -> workspace, ...)
        """
        fname = unicode(fname)
        ext = osp.splitext(fname)[1]
        if ext in self.editor_valid_types:
            self.emit(SIGNAL("edit(QString)"), fname)
        elif ext in ('.spydata', '.npy', '.mat'):
            self.emit(SIGNAL("import_data(QString)"), fname)
        else:
            self.treewidget.startfile(fname)
