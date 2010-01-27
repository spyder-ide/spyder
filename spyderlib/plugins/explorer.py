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
from PyQt4.QtCore import SIGNAL, Qt

import sys
import os.path as osp

# For debugging purpose:
STDOUT = sys.stdout

# Local imports
from spyderlib.config import CONF, get_font, set_font
from spyderlib.utils.qthelpers import create_action, translate
from spyderlib.widgets.explorer import ExplorerWidget
from spyderlib.plugins import PluginMixin


class Explorer(ExplorerWidget, PluginMixin):
    """File and Directories Explorer DockWidget"""
    ID = 'explorer'
    LOCATION = Qt.RightDockWidgetArea
    def __init__(self, parent=None, path=None):
        ExplorerWidget.__init__(self, parent=parent, path=path,
                            name_filters=CONF.get(self.ID, 'name_filters'),
                            valid_types=CONF.get(self.ID, 'valid_filetypes'),
                            show_all=CONF.get(self.ID, 'show_all'),
                            show_toolbar=CONF.get(self.ID, 'show_toolbar'),
                            show_icontext=CONF.get(self.ID, 'show_icontext'))
        PluginMixin.__init__(self, parent)

        self.set_font(get_font(self.ID))
        
        self.connect(self, SIGNAL("open_file(QString)"), self.open_file)
        
    def set_editor_valid_types(self, valid_types):
        self.editor_valid_types = valid_types
        self.treewidget.valid_types += valid_types
        
    def refresh(self, new_path=None, force_current=True):
        """Refresh explorer widget"""
        self.treewidget.refresh(new_path, force_current=force_current)
        
    def refresh_folder(self, folder):
        """Refresh only *folder*"""
        self.treewidget.refresh_folder(folder)

    def get_widget_title(self):
        """Return widget title"""
        return self.tr("File explorer")
    
    def get_focus_widget(self):
        """
        Return the widget to give focus to when
        this plugin's dockwidget is raised on top-level
        """
        return self.treewidget
    
    def set_actions(self):
        """Setup actions"""
        # Font
        font_action = create_action(self, translate('Explorer', "&Font..."),
                                    None, 'font.png',
                                    translate("Explorer", "Set font style"),
                                    triggered=self.change_font)
        self.treewidget.common_actions.append(font_action)
        return (None, None)
        
    def closing(self, cancelable=False):
        """Perform actions before parent main window is closed"""
        return True
        
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

