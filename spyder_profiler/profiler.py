# -*- coding:utf-8 -*-
#
# Copyright © Spyder Project Contributors
# based on p_pylint.py by Pierre Raybaut
#
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""Profiler Plugin."""

# Standard library imports
import os.path as osp

# Third party imports
from qtpy.QtCore import Qt
from qtpy.QtWidgets import QGroupBox, QLabel, QVBoxLayout

# Local imports
from spyder.config.base import get_translation
from spyder.api.plugins import SpyderPluginWidget
from spyder.api.preferences import PluginConfigPage
from spyder.plugins.runconfig import get_run_configuration
from spyder.utils import icon_manager as ima
from spyder.utils.qthelpers import create_action
from .widgets.profilergui import (ProfilerWidget, is_profiler_installed)


_ = get_translation("profiler", "spyder_profiler")


class ProfilerConfigPage(PluginConfigPage):
    def setup_page(self):
        results_group = QGroupBox(_("Results"))
        results_label1 = QLabel(_("Profiler plugin results "
                                  "(the output of python's profile/cProfile)\n"
                                  "are stored here:"))
        results_label1.setWordWrap(True)

        # Warning: do not try to regroup the following QLabel contents with
        # widgets above -- this string was isolated here in a single QLabel
        # on purpose: to fix Issue 863
        results_label2 = QLabel(ProfilerWidget.DATAPATH)

        results_label2.setTextInteractionFlags(Qt.TextSelectableByMouse)
        results_label2.setWordWrap(True)

        results_layout = QVBoxLayout()
        results_layout.addWidget(results_label1)
        results_layout.addWidget(results_label2)
        results_group.setLayout(results_layout)

        vlayout = QVBoxLayout()
        vlayout.addWidget(results_group)
        vlayout.addStretch(1)
        self.setLayout(vlayout)


class Profiler(SpyderPluginWidget):
    """Profiler (after python's profile and pstats)."""

    CONF_SECTION = 'profiler'
    CONFIGWIDGET_CLASS = ProfilerConfigPage

    def __init__(self, parent=None):
        SpyderPluginWidget.__init__(self, parent)

        max_entries = self.get_option('max_entries', 50)
        self.profiler = ProfilerWidget(self, max_entries,
                                       options_button=self.options_button)

        layout = QVBoxLayout()
        layout.addWidget(self.profiler)
        self.setLayout(layout)

        # Initialize plugin
        self.initialize_plugin()
        
    #------ SpyderPluginWidget API ---------------------------------------------    
    def get_plugin_title(self):
        """Return widget title"""
        return _("Profiler")

    def get_plugin_icon(self):
        """Return widget icon"""
        path = osp.join(self.PLUGIN_PATH, self.IMG_PATH)
        return ima.icon('profiler', icon_path=path)

    def get_focus_widget(self):
        """
        Return the widget to give focus to when
        this plugin's dockwidget is raised on top-level
        """
        return self.profiler.datatree
    
    def get_plugin_actions(self):
        """Return a list of actions related to plugin"""
        return []

    def on_first_registration(self):
        """Action to be performed on first plugin registration"""
        self.main.tabify_plugins(self.main.help, self)
        self.dockwidget.hide()

    def register_plugin(self):
        """Register plugin in Spyder's main window"""
        self.profiler.datatree.sig_edit_goto.connect(self.main.editor.load)
        self.profiler.redirect_stdio.connect(
            self.main.redirect_internalshell_stdio)
        self.main.add_dockwidget(self)

        profiler_act = create_action(self, _("Profile"),
                                     icon=self.get_plugin_icon(),
                                     triggered=self.run_profiler)
        profiler_act.setEnabled(is_profiler_installed())
        self.register_shortcut(profiler_act, context="Profiler",
                               name="Run profiler")
        
        self.main.run_menu_actions += [profiler_act]
        self.main.editor.pythonfile_dependent_actions += [profiler_act]

    def refresh_plugin(self):
        """Refresh profiler widget"""
        #self.remove_obsolete_items()  # FIXME: not implemented yet
        
    def closing_plugin(self, cancelable=False):
        """Perform actions before parent main window is closed"""
        return True
            
    def apply_plugin_settings(self, options):
        """Apply configuration file's plugin settings"""
        # The history depth option will be applied at 
        # next Spyder startup, which is soon enough
        pass
        
    #------ Public API ---------------------------------------------------------        
    def run_profiler(self):
        """Run profiler"""
        if self.main.editor.save():
            self.analyze(self.main.editor.get_current_filename())

    def analyze(self, filename):
        """Reimplement analyze method"""
        if self.dockwidget and not self.ismaximized:
            self.dockwidget.setVisible(True)
            self.dockwidget.setFocus()
            self.dockwidget.raise_()
        pythonpath = self.main.get_spyder_pythonpath()
        runconf = get_run_configuration(filename)
        wdir, args = None, []
        if runconf is not None:
            if runconf.wdir_enabled:
                wdir = runconf.wdir
            if runconf.args_enabled:
                args = runconf.args
        self.profiler.analyze(filename, wdir=wdir, args=args,
                              pythonpath=pythonpath)
