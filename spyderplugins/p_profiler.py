# -*- coding:utf-8 -*-
#
# Copyright © 2011 Santiago Jaramillo
# based on p_pylint.py by Pierre Raybaut
#
# Licensed under the terms of the MIT License
# (see spyderlib/__init__.py for details)

"""Profiler Plugin"""

from PyQt4.QtGui import QInputDialog, QVBoxLayout, QGroupBox, QLabel
from PyQt4.QtCore import SIGNAL, Qt

import sys

# For debugging purpose:
STDOUT = sys.stdout

# Local imports
from spyderlib.config import get_icon
from spyderlib.utils.qthelpers import create_action
from spyderlib.plugins import SpyderPluginMixin, PluginConfigPage

from spyderplugins.widgets.profilergui import ProfilerWidget, is_profiler_installed


class ProfilerConfigPage(PluginConfigPage):
    def setup_page(self):
        results_group = QGroupBox(self.tr("Results"))
        results_label = QLabel(self.tr("Profiler plugin results (the output of python's profile/cProfile)\n"
                                    "are stored here:\n"
                                    "%1\n"
                                    ).arg(ProfilerWidget.DATAPATH))
        results_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        results_label.setWordWrap(True)

        results_layout = QVBoxLayout()
        results_layout.addWidget(results_label)
        results_group.setLayout(results_layout)

        vlayout = QVBoxLayout()
        vlayout.addWidget(results_group)
        vlayout.addStretch(1)
        self.setLayout(vlayout)

class Profiler(ProfilerWidget, SpyderPluginMixin):
    """Profiler (after python's profile and pstats)"""
    CONF_SECTION = 'profiler'
    CONFIGWIDGET_CLASS = ProfilerConfigPage
    def __init__(self, parent=None):
        ProfilerWidget.__init__(self, parent=parent,
                              max_entries=self.get_option('max_entries', 50))
        SpyderPluginMixin.__init__(self, parent)
        
    #------ SpyderPluginWidget API ---------------------------------------------    
    def get_plugin_title(self):
        """Return widget title"""
        return self.tr("Profiler")

    def get_plugin_icon(self):
        """Return widget icon"""
        return get_icon('profiler.png')
    
    def get_focus_widget(self):
        """
        Return the widget to give focus to when
        this plugin's dockwidget is raised on top-level
        """
        return self.datatree
    
    def get_plugin_actions(self):
        """Return a list of actions related to plugin"""
        return []
    
    def register_plugin(self):
        """Register plugin in Spyder's main window"""
        self.connect(self, SIGNAL("edit_goto(QString,int,QString)"),
                     self.main.editor.load)
        self.connect(self, SIGNAL('redirect_stdio(bool)'),
                     self.main.redirect_internalshell_stdio)
        self.main.add_dockwidget(self)
        
        profiler_act = create_action(self, self.tr("Profile code"),
                                   triggered=self.run_profiler)
        profiler_act.setEnabled(is_profiler_installed())
        self.register_shortcut(profiler_act, context="Profiler",
                               name="Run profiler", default="F10")
        
        #self.main.source_menu_actions += [profiler_act]
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
        self.analyze( self.main.editor.get_current_filename() )

    def analyze(self, filename):
        """Reimplement analyze method"""
        if self.dockwidget and not self.ismaximized:
            self.dockwidget.setVisible(True)
            self.dockwidget.setFocus()
            self.dockwidget.raise_()
        ProfilerWidget.analyze(self, filename)


#===============================================================================
# The following statements are required to register this 3rd party plugin:
#===============================================================================
PLUGIN_CLASS = Profiler

