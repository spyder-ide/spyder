# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""Files and Directories Explorer Plugin"""

# pylint: disable=C0103
# pylint: disable=R0903
# pylint: disable=R0911
# pylint: disable=R0201

# Standard library imports
import os.path as osp

# Third party imports
from qtpy.QtCore import Signal

# Local imports
from spyder.config.base import _
from spyder.plugins import SpyderPluginMixin
from spyder.py3compat import to_text_string
from spyder.widgets.explorer import ExplorerWidget


class Explorer(ExplorerWidget, SpyderPluginMixin):
    """File and Directories Explorer DockWidget"""

    CONF_SECTION = 'explorer'

    open_interpreter = Signal(str)
    edit = Signal(str)
    removed = Signal(str)
    removed_tree = Signal(str)
    renamed = Signal(str, str)
    create_module = Signal(str)
    run = Signal(str)
    open_dir = Signal(str)
    
    def __init__(self, parent=None):
        ExplorerWidget.__init__(self, parent=parent,
                                name_filters=self.get_option('name_filters'),
                                show_all=self.get_option('show_all'),
                                show_icontext=self.get_option('show_icontext'))
        SpyderPluginMixin.__init__(self, parent)

        # Initialize plugin
        self.initialize_plugin()

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
        return []
    
    def register_plugin(self):
        """Register plugin in Spyder's main window"""
        self.main.add_dockwidget(self)
        self.edit.connect(self.main.editor.load)
        self.removed.connect(self.main.editor.removed)
        self.removed_tree.connect(self.main.editor.removed_tree)
        self.renamed.connect(self.main.editor.renamed)
        self.main.editor.open_dir.connect(self.chdir)
        self.create_module.connect(self.main.editor.new)
        # Signal "set_explorer_cwd(QString)" will refresh only the
        # contents of path passed by the signal in explorer:
        self.main.workingdirectory.set_explorer_cwd.connect(
                     lambda directory: self.refresh_plugin(new_path=directory,
                                                           force_current=True))
        self.open_dir.connect(
                     lambda dirname:
                     self.main.workingdirectory.chdir(dirname,
                                                      refresh_explorer=False,
                                                      refresh_console=True))

        self.sig_open_file.connect(self.main.open_file)
        self.sig_new_file.connect(lambda t: self.main.editor.new(text=t))
        
    def refresh_plugin(self, new_path=None, force_current=True):
        """Refresh explorer widget"""
        self.treewidget.update_history(new_path)
        self.treewidget.refresh(new_path, force_current=force_current)
        
    def closing_plugin(self, cancelable=False):
        """Perform actions before parent main window is closed"""
        return True

    #------ Public API ---------------------------------------------------------
    def chdir(self, directory):
        """Set working directory"""
        self.treewidget.chdir(directory)
