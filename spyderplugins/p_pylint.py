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

from PyQt4.QtCore import SIGNAL
from PyQt4.QtGui import QFontDialog, QInputDialog

import sys

# For debugging purpose:
STDOUT = sys.stdout

# Local imports
from spyderlib.utils.qthelpers import create_action
from spyderlib.widgets.pylintgui import PylintWidget, is_pylint_installed
from spyderlib.plugins import SpyderPluginMixin


class Pylint(PylintWidget, SpyderPluginMixin):
    """Python source code analysis based on pylint"""
    CONF_SECTION = 'pylint'
    def __init__(self, parent=None):
        PylintWidget.__init__(self, parent=parent,
                              max_entries=self.get_option('max_entries'))
        SpyderPluginMixin.__init__(self, parent)

        self.set_font(self.get_plugin_font())
        
    #------ SpyderPluginWidget API ---------------------------------------------    
    def get_plugin_title(self):
        """Return widget title"""
        return self.tr("Pylint")
    
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
        font_action = create_action(self, self.tr("&Font..."),
                                    None, 'font.png', self.tr("Set font style"),
                                    triggered=self.change_font)
        self.treewidget.common_actions += (None, history_action, font_action)
        return []
    
    def register_plugin(self):
        """Register plugin in Spyder's main window"""
        self.connect(self, SIGNAL("edit_goto(QString,int,QString)"),
                     self.main.editor.load)
        self.connect(self, SIGNAL('redirect_stdio(bool)'),
                     self.main.redirect_internalshell_stdio)
        self.main.add_dockwidget(self)
        
        pylint_action = create_action(self, self.tr("Run pylint code analysis"),
                                      "F8", triggered=self.run_pylint)
        pylint_action.setEnabled(is_pylint_installed())
        
        self.main.source_menu_actions += [pylint_action]
        self.main.editor.pythonfile_dependent_actions += [pylint_action]
                    
    def refresh_plugin(self):
        """Refresh pylint widget"""
        self.remove_obsolete_items()
        
    def closing_plugin(self, cancelable=False):
        """Perform actions before parent main window is closed"""
        return True
        
    #------ Public API ---------------------------------------------------------
    def change_history_depth(self):
        "Change history max entries"""
        depth, valid = QInputDialog.getInteger(self, self.tr('History'),
                                       self.tr('Maximum entries'),
                                       self.get_option('max_entries'),
                                       10, 10000)
        if valid:
            self.set_option('max_entries', depth)
        
    def change_font(self):
        """Change font"""
        font, valid = QFontDialog.getFont(self.get_plugin_font(), self,
                                          self.tr("Select a new font"))
        if valid:
            self.set_font(font)
            self.set_plugin_font(font)
            
    def set_font(self, font):
        """Set pylint widget font"""
        self.ratelabel.setFont(font)
        self.treewidget.setFont(font)

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

