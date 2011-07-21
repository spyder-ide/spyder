# -*- coding: utf-8 -*-
#
# Copyright © 2009-2010 Pierre Raybaut
# Licensed under the terms of the MIT License
# (see spyderlib/__init__.py for details)

"""Files and Directories Explorer Plugin"""

# pylint: disable=C0103
# pylint: disable=R0903
# pylint: disable=R0911
# pylint: disable=R0201

from spyderlib.qt.QtGui import QFontDialog
from spyderlib.qt.QtCore import SIGNAL

import sys, os.path as osp

# For debugging purpose:
STDOUT = sys.stdout

# Local imports
from spyderlib.baseconfig import _
from spyderlib.utils.qthelpers import create_action
from spyderlib.widgets.explorer import ExplorerWidget
from spyderlib.plugins import SpyderPluginMixin


class Explorer(ExplorerWidget, SpyderPluginMixin):
    """File and Directories Explorer DockWidget"""
    CONF_SECTION = 'explorer'
    def __init__(self, parent=None):
        ExplorerWidget.__init__(self, parent=parent,
                            name_filters=self.get_option('name_filters'),
                            valid_types=self.get_option('valid_filetypes'),
                            show_all=self.get_option('show_all'),
                            show_cd_only=self.get_option('show_cd_only'),
                            show_toolbar=self.get_option('show_toolbar'),
                            show_icontext=self.get_option('show_icontext'))
        SpyderPluginMixin.__init__(self, parent)

        # Initialize plugin
        self.initialize_plugin()
        
        self.editor_valid_types = None
        
        self.set_font(self.get_plugin_font())
        
        self.sig_open_file.connect(self.open_file)
        
    #------ Private API --------------------------------------------------------
    def set_editor_valid_types(self, valid_types):
        self.editor_valid_types = valid_types
        self.treewidget.valid_types += valid_types

    #------ SpyderPluginWidget API ---------------------------------------------    
    def get_plugin_title(self):
        """Return widget title"""
        return _("File explorer")
    
    def get_focus_widget(self):
        """
        Return the widget to give focus to when
        this plugin's dockwidget is raised on top-level
        """
        return self.treewidget
    
    def get_plugin_actions(self):
        """Return a list of actions related to plugin"""
        # Font
        font_action = create_action(self, _("&Font..."), None, 'font.png',
                                    _("Set font style"),
                                    triggered=self.change_font)
        self.treewidget.common_actions.append(font_action)
        return []
    
    def register_plugin(self):
        """Register plugin in Spyder's main window"""
        self.main.add_dockwidget(self)
        valid_types = self.main.editor.get_valid_types()
        self.set_editor_valid_types(valid_types)
        self.connect(self, SIGNAL("edit(QString)"), self.main.editor.load)
        self.connect(self, SIGNAL("removed(QString)"), self.main.editor.removed)
        self.connect(self, SIGNAL("renamed(QString,QString)"),
                     self.main.editor.renamed)
        self.connect(self.main.editor, SIGNAL("open_dir(QString)"), self.chdir)
        self.connect(self, SIGNAL("create_module(QString)"),
                     self.main.editor.new)
        self.connect(self, SIGNAL("run(QString)"),
                     lambda fname:
                     self.main.open_external_console(unicode(fname),
                                                 osp.dirname(unicode(fname)),
                                                 '', False, False, True, ''))
        # Signal "refresh_explorer()" will eventually force the
        # explorer to change the opened directory:
        self.connect(self.main.console.shell, SIGNAL("refresh_explorer()"),
                     lambda: self.refresh_plugin(force_current=True))
        # Signal "refresh_explorer(QString)" will refresh only the
        # contents of path passed by the signal in explorer:
        self.connect(self.main.console.shell,
                     SIGNAL("refresh_explorer(QString)"), self.refresh_folder)
        self.connect(self.main.editor, SIGNAL("refresh_explorer(QString)"),
                     self.refresh_folder)
        self.connect(self.main.workingdirectory,
                     SIGNAL("refresh_explorer(QString)"),
                     lambda directory: self.refresh_plugin(new_path=directory,
                                                           force_current=True))
        self.connect(self, SIGNAL("open_dir(QString)"),
                     lambda dirname:
                     self.main.workingdirectory.chdir(dirname,
                                                      refresh_explorer=False))
        
    def refresh_plugin(self, new_path=None, force_current=True):
        """Refresh explorer widget"""
        self.treewidget.update_history(new_path)
        self.treewidget.refresh(new_path, force_current=force_current)
        
    def closing_plugin(self, cancelable=False):
        """Perform actions before parent main window is closed"""
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
        font, valid = QFontDialog.getFont(self.get_plugin_font(), self,
                                          _("Select a new font"))
        if valid:
            self.set_font(font)
            self.set_plugin_font(font)
            
    def set_font(self, font):
        """Set explorer widget font"""
        self.setFont(font)
        self.treewidget.setFont(font)

