# -*- coding: utf-8 -*-
#
# Copyright © 2009 Pierre Raybaut
# Licensed under the terms of the MIT License
# (see spyderlib/__init__.py for details)

"""External Console widget"""

# pylint: disable-msg=C0103
# pylint: disable-msg=R0903
# pylint: disable-msg=R0911
# pylint: disable-msg=R0201

from PyQt4.QtGui import QVBoxLayout, QFileDialog, QFontDialog, QMessageBox
from PyQt4.QtCore import Qt, SIGNAL, QString

import sys, os
import os.path as osp

# For debugging purpose:
STDOUT = sys.stdout

# Local imports
from spyderlib.config import CONF, get_font, get_icon, set_font
from spyderlib.qthelpers import create_toolbutton, create_action, mimedata2url
from spyderlib.widgets.tabs import Tabs
from spyderlib.widgets.externalshell.pythonshell import ExternalPythonShell
from spyderlib.widgets.externalshell.systemshell import ExternalSystemShell
from spyderlib.widgets.shellhelpers import get_error_match
from spyderlib.widgets.findreplace import FindReplace
from spyderlib.plugins import PluginWidget


class ExternalConsole(PluginWidget):
    """
    Console widget
    """
    ID = 'external_shell'
    location = Qt.RightDockWidgetArea
    def __init__(self, parent, commands=None):
        self.commands = commands
        self.tabwidget = None
        self.menu_actions = None
        self.docviewer = None
        self.historylog = None
        
        self.shells = []
        self.filenames = []
        self.icons = []
        
        PluginWidget.__init__(self, parent)
        
        layout = QVBoxLayout()
        self.tabwidget = Tabs(self, self.menu_actions)
        self.connect(self.tabwidget, SIGNAL('currentChanged(int)'),
                     self.refresh)
        self.connect(self.tabwidget, SIGNAL("close_tab(int)"),
                     self.tabwidget.removeTab)
        self.connect(self.tabwidget, SIGNAL('move_data(int,int)'),
                     self.move_tab)
        self.close_button = create_toolbutton(self.tabwidget,
                                          icon=get_icon("fileclose.png"),
                                          triggered=self.close_console,
                                          tip=self.tr("Close current console"))
        self.tabwidget.setCornerWidget(self.close_button)
        layout.addWidget(self.tabwidget)
        
        # Find/replace widget
        self.find_widget = FindReplace(self)
        self.find_widget.hide()
        layout.addWidget(self.find_widget)
        
        self.setLayout(layout)
            
        # Accepting drops
        self.setAcceptDrops(True)
        
    def move_tab(self, index_from, index_to):
        """
        Move tab (tabs themselves have already been moved by the tabwidget)
        """
        filename = self.filenames.pop(index_from)
        shell = self.shells.pop(index_from)
        icon = self.icons.pop(index_from)
        
        self.filenames.insert(index_to, filename)
        self.shells.insert(index_to, shell)
        self.icons.insert(index_to, icon)

    def close_console(self, index=None):
        if not self.tabwidget.count():
            return
        if index is None:
            index = self.tabwidget.currentIndex()
        self.tabwidget.widget(index).close()
        self.tabwidget.removeTab(index)
        self.filenames.pop(index)
        self.shells.pop(index)
        self.icons.pop(index)
        
    def set_historylog(self, historylog):
        """Bind historylog instance to this console"""
        self.historylog = historylog
        
    def set_docviewer(self, docviewer):
        """Bind docviewer instance to this console"""
        self.docviewer = docviewer
        
    def execute_python_code(self, lines):
        """Execute Python code in an already opened Python interpreter"""
        from spyderlib.widgets.externalshell.pythonshell import ExtPyQsciShell
        def execute(index):
            shell = self.tabwidget.widget(index).shell
            if isinstance(shell, ExtPyQsciShell):
                self.tabwidget.setCurrentIndex(index)
                shell.execute_lines(unicode(lines))
                shell.setFocus()
                return True
        # Find the Python shell, starting with current widget:
        current_index = self.tabwidget.currentIndex()
        if current_index == -1:
            # No shell!
            return
        if not execute(current_index):
            for index in self.tabwidget.count():
                execute(index)
        
    def start(self, fname, wdir=None, ask_for_arguments=False,
              interact=False, debug=False, python=True):
        """Start new console"""
        # Note: fname is None <=> Python interpreter
        fname = unicode(fname) if isinstance(fname, QString) else fname
        wdir = unicode(wdir) if isinstance(wdir, QString) else wdir

        if fname is not None and fname in self.filenames:
            index = self.filenames.index(fname)
            if CONF.get(self.ID, 'single_tab'):
                old_shell = self.shells[index]
                if old_shell.is_running():
                    answer = QMessageBox.question(self, self.get_widget_title(),
                        self.tr("%1 is already running in a separate process.\n"
                                "Do you want to kill the process before starting "
                                "a new one?").arg(osp.basename(fname)),
                        QMessageBox.Yes | QMessageBox.Cancel)
                    if answer == QMessageBox.Yes:
                        old_shell.process.kill()
                        old_shell.process.waitForFinished()
                    else:
                        return
                self.close_console(index)
        else:
            index = 0

        # Creating a new external shell
        if python:
            shell = ExternalPythonShell(self, fname, wdir, self.commands,
                                        interact, debug, path=self.main.path)
        else:
            shell = ExternalSystemShell(self, wdir)
        shell.shell.set_font( get_font(self.ID) )
        shell.shell.toggle_wrap_mode( CONF.get(self.ID, 'wrap') )
        if python:
            shell.shell.set_docviewer(self.docviewer)
        self.historylog.add_history(shell.shell.history_filename)
        self.connect(shell.shell, SIGNAL('append_to_history(QString,QString)'),
                     self.historylog.append_to_history)
        self.connect(shell.shell, SIGNAL("go_to_error(QString)"),
                     self.go_to_error)
        self.connect(shell.shell, SIGNAL("focus_changed()"),
                     lambda: self.emit(SIGNAL("focus_changed()")))
        if python:
            if fname is None:
                name = "Python"
                icon = get_icon('python.png')
            else:
                name = osp.basename(fname)
                icon = get_icon('run.png')
        else:
            name = "Command Window"
            icon = get_icon('cmdprompt.png')
        self.shells.insert(index, shell)
        self.filenames.insert(index, fname)
        self.icons.insert(index, icon)
        if index is None:
            index = self.tabwidget.addTab(shell, name)
        else:
            self.tabwidget.insertTab(index, shell, name)
        
        self.connect(shell, SIGNAL("started()"),
                     lambda sid=id(shell): self.process_started(sid))
        self.connect(shell, SIGNAL("finished()"),
                     lambda sid=id(shell): self.process_finished(sid))
        self.find_widget.set_editor(shell.shell)
        self.tabwidget.setTabToolTip(index, fname if wdir is None else wdir)
        self.tabwidget.setCurrentIndex(index)
        if self.dockwidget and not self.ismaximized:
            self.dockwidget.setVisible(True)
            self.dockwidget.raise_()
        
        # Start process and give focus to console
        shell.start(ask_for_arguments)
        shell.shell.setFocus()
        
    def process_started(self, shell_id):
        for index, shell in enumerate(self.shells):
            if id(shell) == shell_id:
                self.tabwidget.setTabIcon(index, self.icons[index])
        
    def process_finished(self, shell_id):
        for index, shell in enumerate(self.shells):
            if id(shell) == shell_id:
                self.tabwidget.setTabIcon(index, get_icon('terminated.png'))
        
    def get_widget_title(self):
        """Return widget title"""
        return self.tr('External console')
    
    def get_focus_widget(self):
        """
        Return the widget to give focus to when
        this plugin's dockwidget is raised on top-level
        """
        return self.tabwidget.currentWidget()
        
    def set_actions(self):
        """Setup actions"""
        interpreter_action = create_action(self,
                            self.tr("Open &interpreter"), None,
                            'python.png', self.tr("Open a Python interpreter"),
                            triggered=self.open_interpreter)
        if os.name == 'nt':
            text = self.tr("Open &command prompt")
            tip = self.tr("Open a Windows command prompt")
        else:
            text = self.tr("Open &command shell")
            tip = self.tr("Open a shell window inside Spyder")
        console_action = create_action(self, text, None, 'cmdprompt.png', tip,
                            triggered=self.open_console)
        run_action = create_action(self,
                            self.tr("&Run..."), None,
                            'run_small.png', self.tr("Run a Python script"),
                            triggered=self.run_script)
        font_action = create_action(self,
                            self.tr("&Font..."), None,
                            'font.png', self.tr("Set shell font style"),
                            triggered=self.change_font)
        wrap_action = create_action(self,
                            self.tr("Wrap lines"),
                            toggled=self.toggle_wrap_mode)
        wrap_action.setChecked( CONF.get(self.ID, 'wrap') )
        calltips_action = create_action(self, self.tr("Balloon tips"),
                            toggled=self.toggle_calltips)
        calltips_action.setChecked( CONF.get(self.ID, 'calltips') )
        codecompletion_action = create_action(self, self.tr("Code completion"),
                            toggled=self.toggle_codecompletion)
        codecompletion_action.setChecked( CONF.get(self.ID,
                                                   'autocompletion/enabled') )
        singletab_action = create_action(self,
                            self.tr("One tab per script"),
                            toggled=self.toggle_singletab)
        singletab_action.setChecked( CONF.get(self.ID, 'single_tab') )
        self.menu_actions = [interpreter_action, run_action, None,
                             font_action, wrap_action, calltips_action,
                             codecompletion_action, singletab_action]
        if console_action:
            self.menu_actions.insert(1, console_action)
        return (self.menu_actions, None)
        
    def open_interpreter(self):
        """Open interpreter"""
        self.start(None, os.getcwdu(), False, True, False)
        
    def open_console(self):
        """Open interpreter"""
        self.start(None, os.getcwdu(), False, True, False, python=False)
        
    def run_script(self):
        """Run a Python script"""
        self.emit(SIGNAL('redirect_stdio(bool)'), False)
        filename = QFileDialog.getOpenFileName(self,
                      self.tr("Run Python script"), os.getcwdu(),
                      self.tr("Python scripts")+" (*.py ; *.pyw)")
        self.emit(SIGNAL('redirect_stdio(bool)'), False)
        if filename:
            self.start(unicode(filename), None, False, False, False)
        
    def change_font(self):
        """Change console font"""
        font, valid = QFontDialog.getFont(get_font(self.ID),
                       self, self.tr("Select a new font"))
        if valid:
            for index in range(self.tabwidget.count()):
                self.tabwidget.widget(index).shell.set_font(font)
            set_font(font, self.ID)
            
    def toggle_wrap_mode(self, checked):
        """Toggle wrap mode"""
        if self.tabwidget is None:
            return
        for shell in self.shells:
            shell.shell.toggle_wrap_mode(checked)
        CONF.set(self.ID, 'wrap', checked)
            
    def toggle_calltips(self, checked):
        """Toggle calltips"""
        if self.tabwidget is None:
            return
        for shell in self.shells:
            shell.shell.set_calltips(checked)
        CONF.set(self.ID, 'calltips', checked)
            
    def toggle_codecompletion(self, checked):
        """Toggle code completion"""
        if self.tabwidget is None:
            return
        for shell in self.shells:
            shell.shell.set_codecompletion(checked)
        CONF.set(self.ID, 'autocompletion/enabled', checked)
        
    def toggle_singletab(self, checked):
        """Toggle single tab mode"""
        CONF.set(self.ID, 'single_tab', checked)
        
    def closing(self, cancelable=False):
        """Perform actions before parent main window is closed"""
        return True
    
    def refresh(self):
        """Refresh tabwidget"""
        if self.tabwidget.count():
            editor = self.tabwidget.currentWidget().shell
            editor.setFocus()
        else:
            editor = None
        self.find_widget.set_editor(editor)
    
    def go_to_error(self, text):
        """Go to error if relevant"""
        match = get_error_match(unicode(text))
        if match:
            fname, lnb = match.groups()
            self.emit(SIGNAL("edit_goto(QString,int)"),
                      osp.abspath(fname), int(lnb))
            
            
    #----Drag and drop
    def __is_python_script(self, qstr):
        """Is it a valid Python script?"""
        fname = unicode(qstr)
        return osp.isfile(fname) and \
               ( fname.endswith('.py') or fname.endswith('.pyw') )
        
    def dragEnterEvent(self, event):
        """Reimplement Qt method
        Inform Qt about the types of data that the widget accepts"""
        source = event.mimeData()
        if source.hasUrls() or \
           ( source.hasText() and self.__is_python_script(source.text()) ):
            event.acceptProposedAction()            
            
    def dropEvent(self, event):
        """Reimplement Qt method
        Unpack dropped data and handle it"""
        source = event.mimeData()
        if source.hasText():
            self.start(source.text())
        elif source.hasUrls():
            files = mimedata2url(source)
            for fname in files:
                if self.__is_python_script(fname):
                    self.start(fname)
        event.acceptProposedAction()
