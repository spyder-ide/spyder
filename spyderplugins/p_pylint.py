# -*- coding:utf-8 -*-
#
# Copyright © 2009 Pierre Raybaut
# Licensed under the terms of the MIT License
# (see spyderlib/__init__.py for details)

"""Pylint Code Analysis Plugin"""

# pylint: disable-msg=C0103
# pylint: disable-msg=R0903
# pylint: disable-msg=R0911
# pylint: disable-msg=R0201

from PyQt4.QtGui import QInputDialog, QVBoxLayout, QGroupBox, QLabel
from PyQt4.QtCore import SIGNAL, Qt

import sys

# For debugging purpose:
STDOUT = sys.stdout

# Local imports
from spyderlib.config import get_icon
from spyderlib.utils.qthelpers import create_action
from spyderlib.widgets.pylintgui import PylintWidget, is_pylint_installed
from spyderlib.plugins import SpyderPluginMixin, PluginConfigPage


class PylintConfigPage(PluginConfigPage):
    def setup_page(self):
        hist_group = QGroupBox(self.tr("History"))
        hist_label = QLabel(self.tr("Pylint plugin results are stored here:\n"
                                    "%1\n\nThe following option "
                                    "will be applied at next startup.\n"
                                    ).arg(PylintWidget.DATAPATH))
        hist_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        hist_label.setWordWrap(True)
        hist_spin = self.create_spinbox(self.tr("History: "),
                            self.tr(" results"), 'max_entries', default=50,
                            min_=10, max_=1000000, step=10)

        hist_layout = QVBoxLayout()
        hist_layout.addWidget(hist_label)
        hist_layout.addWidget(hist_spin)
        hist_group.setLayout(hist_layout)

        vlayout = QVBoxLayout()
        vlayout.addWidget(hist_group)
        vlayout.addStretch(1)
        self.setLayout(vlayout)


class Pylint(PylintWidget, SpyderPluginMixin):
    """Python source code analysis based on pylint"""
    CONF_SECTION = 'pylint'
    CONFIGWIDGET_CLASS = PylintConfigPage
    def __init__(self, parent=None):
        PylintWidget.__init__(self, parent=parent,
                              max_entries=self.get_option('max_entries', 50))
        SpyderPluginMixin.__init__(self, parent)
        
    #------ SpyderPluginWidget API ---------------------------------------------    
    def get_plugin_title(self):
        """Return widget title"""
        return self.tr("Pylint")
    
    def get_plugin_icon(self):
        """Return widget icon"""
        return get_icon('pylint.png')
    
    def get_focus_widget(self):
        """
        Return the widget to give focus to when
        this plugin's dockwidget is raised on top-level
        """
        return self.treewidget
    
    def get_plugin_actions(self):
        """Return a list of actions related to plugin"""
        # Font
        history_action = create_action(self, self.tr("History..."),
                                       None, 'history.png',
                                       self.tr("Set history maximum entries"),
                                       triggered=self.change_history_depth)
        self.treewidget.common_actions += (None, history_action)
        return []
    
    def register_plugin(self):
        """Register plugin in Spyder's main window"""
        self.connect(self, SIGNAL("edit_goto(QString,int,QString)"),
                     self.main.editor.load)
        self.connect(self, SIGNAL('redirect_stdio(bool)'),
                     self.main.redirect_internalshell_stdio)
        self.main.add_dockwidget(self)
        
        pylint_act = create_action(self, self.tr("Run pylint code analysis"),
                                   triggered=self.run_pylint)
        pylint_act.setEnabled(is_pylint_installed())
        self.register_shortcut(pylint_act, context="Pylint",
                               name="Run analysis", default="F8")
        
        self.main.source_menu_actions += [pylint_act]
        self.main.editor.pythonfile_dependent_actions += [pylint_act]
                    
    def refresh_plugin(self):
        """Refresh pylint widget"""
        self.remove_obsolete_items()
        
    def closing_plugin(self, cancelable=False):
        """Perform actions before parent main window is closed"""
        return True
            
    def apply_plugin_settings(self, options):
        """Apply configuration file's plugin settings"""
        # The history depth option will be applied at 
        # next Spyder startup, which is soon enough
        pass
        
    #------ Public API ---------------------------------------------------------
    def change_history_depth(self):
        "Change history max entries"""
        depth, valid = QInputDialog.getInteger(self, self.tr('History'),
                                       self.tr('Maximum entries'),
                                       self.get_option('max_entries'),
                                       10, 10000)
        if valid:
            self.set_option('max_entries', depth)
        
    def run_pylint(self):
        """Run pylint code analysis"""
        self.analyze( self.main.editor.get_current_filename() )
        
    def analyze(self, filename):
        """Reimplement analyze method"""
        if self.dockwidget and not self.ismaximized:
            self.dockwidget.setVisible(True)
            self.dockwidget.setFocus()
            self.dockwidget.raise_()
        PylintWidget.analyze(self, filename)


#===============================================================================
# The following statements are required to register this 3rd party plugin:
#===============================================================================
PLUGIN_CLASS = Pylint

