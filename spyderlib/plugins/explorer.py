# -*- coding: utf-8 -*-
#
# Copyright © 2009 Pierre Raybaut
# Licensed under the terms of the MIT License
# (see spyderlib/__init__.py for details)

"""Files and Directories Explorer Plugin"""

# pylint: disable-msg=C0103
# pylint: disable-msg=R0903
# pylint: disable-msg=R0911
# pylint: disable-msg=R0201

from PyQt4.QtGui import QFontDialog
from PyQt4.QtCore import SIGNAL

import sys, os, os.path as osp

# For debugging purpose:
STDOUT = sys.stdout

# Local imports
from spyderlib.config import CONF, get_font, set_font
from spyderlib.utils.qthelpers import create_action, translate
from spyderlib.widgets.explorer import ExplorerWidget
from spyderlib.plugins import SpyderPluginMixin


class Explorer(ExplorerWidget, SpyderPluginMixin):
    """File and Directories Explorer DockWidget"""
    ID = 'explorer'
    def __init__(self, parent=None):
        ExplorerWidget.__init__(self, parent=parent,
                            path=CONF.get(self.ID, 'path', None),
                            name_filters=CONF.get(self.ID, 'name_filters'),
                            valid_types=CONF.get(self.ID, 'valid_filetypes'),
                            show_all=CONF.get(self.ID, 'show_all'),
                            show_toolbar=CONF.get(self.ID, 'show_toolbar'),
                            show_icontext=CONF.get(self.ID, 'show_icontext'))
        SpyderPluginMixin.__init__(self, parent)

        self.editor_valid_types = None
        
        self.set_font(get_font(self.ID))
        
        self.connect(self, SIGNAL("open_file(QString)"), self.open_file)
        
    #------ Private API --------------------------------------------------------
    def set_editor_valid_types(self, valid_types):
        self.editor_valid_types = valid_types
        self.treewidget.valid_types += valid_types

    #------ SpyderPluginWidget API ---------------------------------------------    
    def get_plugin_title(self):
        """Return widget title"""
        return self.tr("File explorer")
    
    def get_focus_widget(self):
        """
        Return the widget to give focus to when
        this plugin's dockwidget is raised on top-level
        """
        return self.treewidget
    
    def get_plugin_actions(self):
        """Setup actions"""
        # Font
        font_action = create_action(self, translate('Explorer', "&Font..."),
                                    None, 'font.png',
                                    translate("Explorer", "Set font style"),
                                    triggered=self.change_font)
        self.treewidget.common_actions.append(font_action)
        return (None, None)
        
    def refresh_plugin(self, new_path=None, force_current=True):
        """Refresh explorer widget"""
        self.treewidget.refresh(new_path, force_current=force_current)
        
    def closing_plugin(self, cancelable=False):
        """Perform actions before parent main window is closed"""
        CONF.set(self.ID, 'path', os.getcwdu())
        return True
        
    #------ Public API ---------------------------------------------------------        
    def refresh_folder(self, folder):
        """Refresh only *folder*"""
        self.treewidget.refresh_folder(folder)
        
    def chdir(self, directory):
        """Set working directory"""
        self.treewidget.chdir(directory)
        
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
        
    def change_font(self):
        """Change font"""
        font, valid = QFontDialog.getFont(get_font(self.ID), self,
                                  translate("Explorer", "Select a new font"))
        if valid:
            self.set_font(font)
            set_font(font, self.ID)
            
    def set_font(self, font):
        """Set explorer widget font"""
        self.setFont(font)
        self.treewidget.setFont(font)

