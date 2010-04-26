# -*- coding: utf-8 -*-
#
# Copyright © 2009 Pierre Raybaut
# Licensed under the terms of the MIT License
# (see spyderlib/__init__.py for details)

"""Pylint Code Analysis Plugin"""

# pylint: disable-msg=C0103
# pylint: disable-msg=R0903
# pylint: disable-msg=R0911
# pylint: disable-msg=R0201

from PyQt4.QtGui import QFontDialog, QInputDialog

import sys

# For debugging purpose:
STDOUT = sys.stdout

# Local imports
from spyderlib.config import CONF, get_font, set_font
from spyderlib.utils.qthelpers import create_action
from spyderlib.widgets.pylintgui import PylintWidget
from spyderlib.plugins import SpyderPluginMixin


class Pylint(PylintWidget, SpyderPluginMixin):
    """Python source code analysis based on pylint"""
    ID = 'pylint'
    def __init__(self, parent=None):
        PylintWidget.__init__(self, parent=parent,
                              max_entries=CONF.get(self.ID, 'max_entries'))
        SpyderPluginMixin.__init__(self, parent)

        self.set_font(get_font(self.ID))
        
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
        """Setup actions"""
        # Font
        history_action = create_action(self, self.tr("History..."),
                                       None, 'history.png',
                                       self.tr("Set history maximum entries"),
                                       triggered=self.change_history_depth)
        font_action = create_action(self, self.tr("&Font..."),
                                    None, 'font.png', self.tr("Set font style"),
                                    triggered=self.change_font)
        self.treewidget.common_actions += (None, history_action, font_action)
        return (None, None)
        
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
                                       CONF.get(self.ID, 'max_entries'),
                                       10, 10000)
        if valid:
            CONF.set(self.ID, 'max_entries', depth)
        
    def change_font(self):
        """Change font"""
        font, valid = QFontDialog.getFont(get_font(self.ID), self,
                                          self.tr("Select a new font"))
        if valid:
            self.set_font(font)
            set_font(font, self.ID)
            
    def set_font(self, font):
        """Set pylint widget font"""
        self.ratelabel.setFont(font)
        self.treewidget.setFont(font)
        
    def analyze(self, filename):
        """Reimplement analyze method"""
        if self.dockwidget and not self.ismaximized:
            self.dockwidget.setVisible(True)
            self.dockwidget.setFocus()
            self.dockwidget.raise_()
        PylintWidget.analyze(self, filename)

