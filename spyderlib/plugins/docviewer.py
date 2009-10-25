# -*- coding: utf-8 -*-
#
# Copyright © 2009 Pierre Raybaut
# Licensed under the terms of the MIT License
# (see spyderlib/__init__.py for details)

"""Editor widgets"""

from PyQt4.QtGui import (QHBoxLayout, QVBoxLayout, QLabel, QSizePolicy,
                         QCheckBox, QComboBox)
from PyQt4.QtCore import Qt, SIGNAL

import sys
import os.path as osp

# For debugging purpose:
STDOUT = sys.stdout

# Local imports
from spyderlib.config import CONF, get_conf_path, get_icon
from spyderlib.utils.qthelpers import create_toolbutton
from spyderlib.widgets.comboboxes import EditableComboBox
from spyderlib.plugins import ReadOnlyEditor
from spyderlib.widgets.externalshell.pythonshell import ExtPyQsciShell


class DocComboBox(EditableComboBox):
    """
    QComboBox handling doc viewer history
    """
    def __init__(self, parent):
        super(DocComboBox, self).__init__(parent)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.tips = {True: self.tr("Press enter to validate this object name"),
                     False: self.tr('This object name is incorrect')}
        
    def is_valid(self, qstr):
        """Return True if string is valid"""
        shell = self.parent().shell
        if hasattr(shell, 'interpreter'):
            _, valid = shell.interpreter.eval(unicode(qstr))
            return valid
        
    def keyPressEvent(self, event):
        """Handle key press events"""
        if event.key() == Qt.Key_Return or event.key() == Qt.Key_Enter:
            text = self.currentText()
            valid = self.is_valid(text)
            if valid or valid is None:
                self.parent().refresh(text, force=True)
                self.set_default_style()
        else:
            QComboBox.keyPressEvent(self, event)
    
class DocViewer(ReadOnlyEditor):
    """
    Docstrings viewer widget
    """
    ID = 'docviewer'
    LOG_PATH = get_conf_path('.docviewer')
    def __init__(self, parent):
        ReadOnlyEditor.__init__(self, parent)
        
        self.shell = None
        
        # locked = disable link with Console
        self.locked = False
        self._last_text = None
        
        # Object name
        layout_edit = QHBoxLayout()
        layout_edit.addWidget(QLabel(self.tr("Object")))
        self.combo = DocComboBox(self)
        layout_edit.addWidget(self.combo)
        self.combo.setMaxCount(CONF.get(self.ID, 'max_history_entries'))
        dvhistory = self.load_dvhistory()
        self.combo.addItems( dvhistory )
        
        # Doc/source checkbox
        self.help_or_doc = QCheckBox(self.tr("Show source"))
        self.connect(self.help_or_doc, SIGNAL("stateChanged(int)"),
                     self.toggle_help)
        layout_edit.addWidget(self.help_or_doc)
        self.docstring = None
        self.autosource = False
        self.toggle_help(Qt.Unchecked)
        
        # Lock checkbox
        self.locked_button = create_toolbutton(self,
                                               triggered=self.toggle_locked)
        layout_edit.addWidget(self.locked_button)
        self._update_lock_icon()

        # Main layout
        layout = QVBoxLayout()
        layout.addLayout(layout_edit)
        layout.addWidget(self.editor)
        layout.addWidget(self.find_widget)
        self.setLayout(layout)
            
    def get_widget_title(self):
        """Return widget title"""
        return self.tr('Doc')
    
    def get_focus_widget(self):
        """
        Return the widget to give focus to when
        this plugin's dockwidget is raised on top-level
        """
        self.combo.lineEdit().selectAll()
        return self.combo
        
    def load_dvhistory(self, obj=None):
        """Load history from a text file in user home directory"""
        if osp.isfile(self.LOG_PATH):
            dvhistory = [line.replace('\n','')
                         for line in file(self.LOG_PATH, 'r').readlines()]
        else:
            dvhistory = [ ]
        return dvhistory
    
    def save_dvhistory(self):
        """Save history to a text file in user home directory"""
        file(self.LOG_PATH, 'w').write("\n".join( \
            [ unicode( self.combo.itemText(index) )
                for index in range(self.combo.count()) ] ))
        
    def toggle_help(self, state):
        """Toggle between docstring and help()"""
        self.docstring = (state == Qt.Unchecked)
        self.refresh(force=True)
        
    def toggle_locked(self):
        """
        Toggle locked state
        locked = disable link with Console
        """
        self.locked = not self.locked
        self._update_lock_icon()
        
    def _update_lock_icon(self):
        """Update locked state icon"""
        icon = get_icon("lock.png" if self.locked else "lock_open.png")
        self.locked_button.setIcon(icon)
        tip = self.tr("Unlock") if self.locked else self.tr("Lock")
        self.locked_button.setToolTip(tip)
        
    def set_shell(self, shell):
        """Bind to shell"""
        self.shell = shell
        
    def refresh(self, text=None, force=False):
        """Refresh widget"""
        if (self.locked and not force):
            return
        
        if text is None:
            text = self.combo.currentText()
        else:
            index = self.combo.findText(text)
            while index!=-1:
                self.combo.removeItem(index)
                index = self.combo.findText(text)
            self.combo.insertItem(0, text)
            self.combo.setCurrentIndex(0)
            
        self.set_help(text)
        self.save_dvhistory()
        if hasattr(self.main, 'tabifiedDockWidgets'):
            # 'QMainWindow.tabifiedDockWidgets' was introduced in PyQt 4.5
            if self.dockwidget and self.dockwidget.isVisible() \
               and not self.ismaximized and text != self._last_text:
                dockwidgets = self.main.tabifiedDockWidgets(self.dockwidget)
                if self.main.console.dockwidget not in dockwidgets and \
                   (hasattr(self.main, 'extconsole') and \
                    self.main.extconsole.dockwidget not in dockwidgets):
                    self.dockwidget.raise_()
        self._last_text = text
        
    def set_help(self, obj_text):
        """Show help"""
        if self.shell is None:
            return
        if isinstance(self.shell, ExtPyQsciShell):
            if not self.shell.externalshell.is_running():
                # Binded external shell was stopped:
                # binding DocViewer to interactive console instead
                self.shell = self.main.console.shell
        obj_text = unicode(obj_text)
        doc_text = self.shell.get_doc(obj_text)
        try:
            source_text = self.shell.get_source(obj_text)
        except (TypeError, IOError):
            source_text = None
        if self.docstring:
            hlp_text = doc_text
            if hlp_text is None:
                hlp_text = source_text
                if hlp_text is None:
                    hlp_text = self.tr("No documentation available.")
        else:
            hlp_text = source_text
            if hlp_text is None:
                hlp_text = doc_text
                if hlp_text is None:
                    hlp_text = self.tr("No source code available.")
        self.editor.set_text(hlp_text)
        self.editor.set_cursor_position('sof')
