# -*- coding:utf-8 -*-
"""Spyder's pylint code analysis plugin"""

from PyQt4.QtCore import SIGNAL

from spyderlib.plugins import pylintgui


class Pylint(pylintgui.Pylint):    
    def register_plugin(self):
        """Register plugin in Spyder's main window"""
        self.connect(self.main.editor, SIGNAL('run_pylint(QString)'),
                     self.analyze)
        self.connect(self, SIGNAL("edit_goto(QString,int,QString)"),
                     self.main.editor.load)
        self.connect(self, SIGNAL('redirect_stdio(bool)'),
                     self.main.redirect_internalshell_stdio)
        self.main.add_dockwidget(self)


PLUGIN_CLASS = Pylint
