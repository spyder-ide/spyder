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
from qtpy.QtWidgets import QVBoxLayout

# Local imports
from spyder.config.base import _
from spyder.api.plugins import SpyderPluginWidget
from spyder.utils.qthelpers import add_actions, MENU_SEPARATOR
from spyder.plugins.explorer.widgets import ExplorerWidget

class Explorer(SpyderPluginWidget):
    """File and Directories Explorer DockWidget."""

    CONF_SECTION = 'explorer'

    def __init__(self, parent=None):
        """Initialization."""
        SpyderPluginWidget.__init__(self, parent)

        self.fileexplorer = ExplorerWidget(
            self,
            name_filters=self.get_option('name_filters'),
            show_all=self.get_option('show_all'),
            show_icontext=self.get_option('show_icontext'),
            options_button=self.options_button,
            single_click_to_open=self.get_option('single_click_to_open'),
        )

        # Initialize plugin
        self.initialize_plugin()

        layout = QVBoxLayout()
        layout.addWidget(self.fileexplorer)
        self.setLayout(layout)

        self.fileexplorer.sig_option_changed.connect(
            self._update_config_options)

    #------ SpyderPluginWidget API ---------------------------------------------
    def get_plugin_title(self):
        """Return widget title"""
        return _("Files")
    
    def get_focus_widget(self):
        """
        Return the widget to give focus to when
        this plugin's dockwidget is raised on top-level
        """
        return self.fileexplorer.treewidget
    
    def get_plugin_actions(self):
        """Return a list of actions related to plugin"""
        return self.fileexplorer.treewidget.common_actions
    
    def register_plugin(self):
        """Register plugin in Spyder's main window"""
        ipyconsole = self.main.ipyconsole
        treewidget = self.fileexplorer.treewidget

        self.main.add_dockwidget(self)
        self.fileexplorer.sig_open_file.connect(self.main.open_file)
        self.register_widget_shortcuts(treewidget)

        treewidget.sig_edit.connect(self.main.editor.load)
        treewidget.sig_removed.connect(self.main.editor.removed)
        treewidget.sig_removed_tree.connect(self.main.editor.removed_tree)
        treewidget.sig_renamed.connect(self.main.editor.renamed)
        treewidget.sig_renamed_tree.connect(self.main.editor.renamed_tree)
        treewidget.sig_create_module.connect(self.main.editor.new)
        treewidget.sig_new_file.connect(lambda t: self.main.editor.new(text=t))
        treewidget.sig_open_interpreter.connect(
            ipyconsole.create_client_from_path)
        treewidget.redirect_stdio.connect(
            self.main.redirect_internalshell_stdio)
        treewidget.sig_run.connect(
            lambda fname:
            ipyconsole.run_script(fname, osp.dirname(fname), '', False, False,
                                  False, True))
        treewidget.sig_open_dir.connect(
            lambda dirname:
            self.main.workingdirectory.chdir(dirname,
                                             refresh_explorer=False,
                                             refresh_console=True))

        self.main.editor.open_dir.connect(self.chdir)

        # Signal "set_explorer_cwd(QString)" will refresh only the
        # contents of path passed by the signal in explorer:
        self.main.workingdirectory.set_explorer_cwd.connect(
                     lambda directory: self.refresh_plugin(new_path=directory,
                                                           force_current=True))

    def refresh_plugin(self, new_path=None, force_current=True):
        """Refresh explorer widget"""
        self.fileexplorer.treewidget.update_history(new_path)
        self.fileexplorer.treewidget.refresh(new_path,
                                             force_current=force_current)
        
    def closing_plugin(self, cancelable=False):
        """Perform actions before parent main window is closed"""
        return True

    def on_first_registration(self):
        """Action to be performed on first plugin registration"""
        self.main.tabify_plugins(self.main.variableexplorer, self)

    #------ Public API ---------------------------------------------------------
    def chdir(self, directory):
        """Set working directory"""
        self.fileexplorer.treewidget.chdir(directory)

    def _update_config_options(self, option, value):
        """Update the config options of the explorer to make them permanent."""
        self.set_option(option, value)
