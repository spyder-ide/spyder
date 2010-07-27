# -*- coding:utf-8 -*-
"""Spyder's pylint code analysis plugin"""

from PyQt4.QtCore import SIGNAL

from spyderlib.utils.qthelpers import create_action
from spyderlib.widgets.pylintgui import is_pylint_installed
from spyderlib.plugins import pylintgui


class Pylint(pylintgui.Pylint):    
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
            
    def run_pylint(self):
        """Run pylint code analysis"""
        self.analyze( self.main.editor.get_current_filename() )


PLUGIN_CLASS = Pylint
