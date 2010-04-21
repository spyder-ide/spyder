# -*- coding: utf-8 -*-
#
# Copyright © 2009 Pierre Raybaut
# Licensed under the terms of the MIT License
# (see spyderlib/__init__.py for details)

"""Object Inspector Plugin"""

from PyQt4.QtGui import (QHBoxLayout, QVBoxLayout, QLabel, QSizePolicy,
                         QCheckBox)
from PyQt4.QtCore import Qt, SIGNAL

import sys, re, os.path as osp

# For debugging purpose:
STDOUT = sys.stdout

# Local imports
from spyderlib.config import CONF, get_conf_path, get_icon
from spyderlib.utils.qthelpers import create_toolbutton
from spyderlib.widgets.comboboxes import EditableComboBox
from spyderlib.plugins import ReadOnlyEditor
from spyderlib.widgets.externalshell.pythonshell import ExtPyQsciShell


class ObjectComboBox(EditableComboBox):
    """
    QComboBox handling object names
    """
    def __init__(self, parent):
        super(ObjectComboBox, self).__init__(parent)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.tips = {True: self.tr("Press enter to validate this object name"),
                     False: self.tr('This object name is incorrect')}
        
    def is_valid(self, qstr=None):
        """Return True if string is valid"""
        if qstr is None:
            qstr = self.currentText()
        if not re.search('^[a-zA-Z0-9_\.]*$', str(qstr), 0):
            return False
        shell = self.parent().shell
        if shell is not None:
            force_import = CONF.get('inspector', 'automatic_import')
            return shell.is_defined(unicode(qstr), force_import=force_import)
        
    def validate_current_text(self):
        self.validate(self.currentText())


class ObjectInspector(ReadOnlyEditor):
    """
    Docstrings viewer widget
    """
    ID = 'inspector'
    LOG_PATH = get_conf_path('.inspector')
    def __init__(self, parent):
        ReadOnlyEditor.__init__(self, parent)
        
        self.shell = None
        
        # locked = disable link with Console
        self.locked = False
        self._last_text = None
        
        # Object name
        layout_edit = QHBoxLayout()
        layout_edit.addWidget(QLabel(self.tr("Object")))
        self.combo = ObjectComboBox(self)
        layout_edit.addWidget(self.combo)
        self.combo.setMaxCount(CONF.get(self.ID, 'max_history_entries'))
        self.combo.addItems( self.load_history() )
        self.connect(self.combo, SIGNAL("valid(bool)"),
                     lambda valid: self.refresh(force=True))
        
        # Doc/source checkbox
        help_or_doc = QCheckBox(self.tr("Show source"))
        self.connect(help_or_doc, SIGNAL("stateChanged(int)"), self.toggle_help)
        layout_edit.addWidget(help_or_doc)
        self.docstring = None
        self.autosource = False
        self.toggle_help(Qt.Unchecked)
        
        # Automatic import checkbox
        auto_import = QCheckBox(self.tr("Automatic import"))
        self.connect(auto_import, SIGNAL("stateChanged(int)"),
                     self.toggle_auto_import)
        auto_import.setChecked(CONF.get('inspector', 'automatic_import'))
        layout_edit.addWidget(auto_import)
        
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
        return self.tr('Object inspector')
    
    def get_focus_widget(self):
        """
        Return the widget to give focus to when
        this plugin's dockwidget is raised on top-level
        """
        self.combo.lineEdit().selectAll()
        return self.combo
        
    def load_history(self, obj=None):
        """Load history from a text file in user home directory"""
        if osp.isfile(self.LOG_PATH):
            history = [line.replace('\n','')
                       for line in file(self.LOG_PATH, 'r').readlines()]
        else:
            history = []
        return history
    
    def save_history(self):
        """Save history to a text file in user home directory"""
        file(self.LOG_PATH, 'w').write("\n".join( \
            [ unicode( self.combo.itemText(index) )
                for index in range(self.combo.count()) ] ))
        
    def toggle_help(self, state):
        """Toggle between docstring and help()"""
        self.docstring = (state == Qt.Unchecked)
        self.refresh(force=True)
        
    def toggle_auto_import(self, state):
        """Toggle automatic import feature"""
        CONF.set('inspector', 'automatic_import', state == Qt.Checked)
        self.refresh(force=True)
        self.combo.validate_current_text()
        
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
        
    def get_shell(self):
        """Return bound shell instance"""
        return self.shell
        
    def refresh(self, text=None, force=False):
        """Refresh widget"""
        if (self.locked and not force):
            return
        
        if text is None:
            text = self.combo.currentText()
        else:
            self.combo.add_text(text)
            
        self.set_help(text)
        self.save_history()
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
                # binding ObjectInspector to interactive console instead
                self.shell = self.main.console.shell
        obj_text = unicode(obj_text)

        if CONF.get('inspector', 'automatic_import'):
            self.shell.is_defined(obj_text, force_import=True) # force import
        
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
