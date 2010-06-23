# -*- coding: utf-8 -*-
#
# Copyright © 2009 Pierre Raybaut
# Licensed under the terms of the MIT License
# (see spyderlib/__init__.py for details)

"""Internal Console Plugin"""

# pylint: disable-msg=C0103
# pylint: disable-msg=R0903
# pylint: disable-msg=R0911
# pylint: disable-msg=R0201

from PyQt4.QtGui import (QVBoxLayout, QFileDialog, QFontDialog, QInputDialog,
                         QLineEdit, QMenu)
from PyQt4.QtCore import SIGNAL

import os, sys
import os.path as osp

# For debugging purpose:
STDOUT = sys.stdout

# Local imports
from spyderlib.config import CONF, get_font, set_font, get_icon
from spyderlib.utils.qthelpers import create_action, add_actions, mimedata2url
from spyderlib.utils.environ import EnvDialog
from spyderlib.widgets.internalshell import InternalShell
from spyderlib.widgets.shellhelpers import get_error_match
from spyderlib.widgets.findreplace import FindReplace
from spyderlib.widgets.dicteditor import DictEditor
from spyderlib.plugins import SpyderPluginWidget

    
def show_syspath():
    """Show sys.path"""
    dlg = DictEditor(sys.path, title="sys.path",
                     width=600, icon='syspath.png', readonly=True)
    dlg.exec_()

class Console(SpyderPluginWidget):
    """
    Console widget
    """
    ID = 'shell'
    def __init__(self, parent=None, namespace=None, commands=[], message="",
                 debug=False, exitfunc=None, profile=False, multithreaded=True):
        # Shell
        self.shell = InternalShell(parent, namespace, commands, message,
                                   CONF.get(self.ID, 'max_line_count'),
                                   get_font(self.ID),
                                   debug, exitfunc, profile, multithreaded)
        self.connect(self.shell, SIGNAL('status(QString)'),
                     lambda msg:
                     self.emit(SIGNAL('show_message(QString,int)'), msg, 0))
        self.connect(self.shell, SIGNAL("go_to_error(QString)"),
                     self.go_to_error)
        self.connect(self.shell, SIGNAL("focus_changed()"),
                     lambda: self.emit(SIGNAL("focus_changed()")))
        # Redirecting some SIGNALs:
        self.connect(self.shell, SIGNAL('redirect_stdio(bool)'),
                     lambda state: self.emit(SIGNAL('redirect_stdio(bool)'),
                                             state))
        
        SpyderPluginWidget.__init__(self, parent)
        
        # Find/replace widget
        self.find_widget = FindReplace(self)
        self.find_widget.set_editor(self.shell)
        self.find_widget.hide()

        # Main layout
        layout = QVBoxLayout()
        layout.addWidget(self.shell)
        layout.addWidget(self.find_widget)
        self.setLayout(layout)
        
        # Parameters
        self.shell.toggle_wrap_mode( CONF.get(self.ID, 'wrap') )
            
        # Accepting drops
        self.setAcceptDrops(True)
        
    #------ Private API --------------------------------------------------------
    def set_historylog(self, historylog):
        """Bind historylog instance to this console
        Not used anymore since v2.0"""
        historylog.add_history(self.shell.history_filename)
        self.connect(self.shell, SIGNAL('append_to_history(QString,QString)'),
                     historylog.append_to_history)
        
    def set_inspector(self, inspector):
        """Bind inspector instance to this console"""
        self.shell.inspector = inspector

    #------ SpyderPluginWidget API ---------------------------------------------
    def get_plugin_title(self):
        """Return widget title"""
        return self.tr('Internal console')
    
    def get_focus_widget(self):
        """
        Return the widget to give focus to when
        this plugin's dockwidget is raised on top-level
        """
        return self.shell
        
    def closing_plugin(self, cancelable=False):
        """Perform actions before parent main window is closed"""
        self.shell.exit_interpreter()
        return True
        
    def refresh_plugin(self):
        pass
    
    def get_plugin_actions(self):
        """Setup actions"""
        quit_action = create_action(self, self.tr("&Quit"), self.tr("Ctrl+Q"),
                            'exit.png', self.tr("Quit"),
                            triggered=self.quit)
        run_action = create_action(self, self.tr("&Run..."), None,
                            'run_small.png', self.tr("Run a Python script"),
                            triggered=self.run_script)
        environ_action = create_action(self,
                            self.tr("Environment variables..."),
                            icon = 'environ.png',
                            tip=self.tr("Show and edit environment variables"
                                        " (for current session)"),
                            triggered=self.show_env)
        syspath_action = create_action(self,
                            self.tr("Show sys.path contents..."),
                            icon = 'syspath.png',
                            tip=self.tr("Show (read-only) sys.path"),
                            triggered=show_syspath)
        buffer_action = create_action(self,
                            self.tr("Buffer..."), None,
                            tip=self.tr("Set maximum line count"),
                            triggered=self.change_max_line_count)
        font_action = create_action(self,
                            self.tr("&Font..."), None,
                            'font.png', self.tr("Set shell font style"),
                            triggered=self.change_font)
        exteditor_action = create_action(self,
                            self.tr("External editor path..."), None, None,
                            self.tr("Set external editor executable path"),
                            triggered=self.change_exteditor)
        wrap_action = create_action(self,
                            self.tr("Wrap lines"),
                            toggled=self.toggle_wrap_mode)
        wrap_action.setChecked( CONF.get(self.ID, 'wrap') )
        calltips_action = create_action(self, self.tr("Balloon tips"),
            toggled=self.toggle_calltips)
        calltips_action.setChecked( CONF.get(self.ID, 'calltips') )
        codecompletion_action = create_action(self,
                                          self.tr("Automatic code completion"),
                                          toggled=self.toggle_codecompletion)
        codecompletion_action.setChecked( CONF.get(self.ID,
                                                   'codecompletion/auto') )
        codecompenter_action = create_action(self,
                                    self.tr("Enter key selects completion"),
                                    toggled=self.toggle_codecompletion_enter)
        codecompenter_action.setChecked( CONF.get(self.ID,
                                                   'codecompletion/enter-key') )
        
        option_menu = QMenu(self.tr("Internal console settings"), self)
        option_menu.setIcon(get_icon('tooloptions.png'))
        add_actions(option_menu, (buffer_action, font_action, wrap_action,
                                  calltips_action, codecompletion_action,
                                  codecompenter_action, exteditor_action))
                    
        menu_actions = [None, run_action, environ_action, syspath_action,
                        option_menu, None, quit_action]
        toolbar_actions = []
        
        # Add actions to context menu
        add_actions(self.shell.menu, menu_actions)
        
        return menu_actions, toolbar_actions
        
    #------ Public API ---------------------------------------------------------
    def quit(self):
        """Quit mainwindow"""
        self.main.close()
        
    def show_env(self):
        """Show environment variables"""
        dlg = EnvDialog()
        dlg.exec_()
        
    def run_script(self, filename=None, silent=False, set_focus=False,
                   args=None):
        """Run a Python script"""
        if filename is None:
            self.shell.interpreter.restore_stds()
            filename = QFileDialog.getOpenFileName(self,
                          self.tr("Run Python script"), os.getcwdu(),
                          self.tr("Python scripts")+" (*.py ; *.pyw)")
            self.shell.interpreter.redirect_stds()
            if filename:
                filename = unicode(filename)
                os.chdir( os.path.dirname(filename) )
                filename = os.path.basename(filename)
                self.emit(SIGNAL("refresh()"))
            else:
                return
        command = "runfile(%s, args=%s)" % (repr(osp.abspath(filename)),
                                            repr(args))
        if set_focus:
            self.shell.setFocus()
        if self.dockwidget and not self.ismaximized:
            self.dockwidget.setVisible(True)
            self.dockwidget.raise_()
        self.shell.write(command+'\n')
        self.shell.run_command(command)

            
    def go_to_error(self, text):
        """Go to error if relevant"""
        match = get_error_match(unicode(text))
        if match:
            fname, lnb = match.groups()
            self.edit_script(fname, int(lnb))
            
    def edit_script(self, filename=None, goto=-1):
        """Edit script"""
        # Called from InternalShell
        if not hasattr(self, 'main') \
           or not hasattr(self.main, 'editor'):
            self.shell.external_editor(filename, goto)
            return
        if filename is not None:
            self.emit(SIGNAL("edit_goto(QString,int,QString)"),
                      osp.abspath(filename), goto, '')
        
    def execute_lines(self, lines):
        """Execute lines and give focus to shell"""
        self.shell.execute_lines(unicode(lines))
        self.shell.setFocus()
        
    def change_font(self):
        """Change console font"""
        font, valid = QFontDialog.getFont(get_font(self.ID),
                       self, self.tr("Select a new font"))
        if valid:
            self.shell.set_font(font)
            set_font(font, self.ID)
        
    def change_max_line_count(self):
        "Change maximum line count"""
        mlc, valid = QInputDialog.getInteger(self, self.tr('Buffer'),
                                           self.tr('Maximum line count'),
                                           CONF.get(self.ID, 'max_line_count'),
                                           10, 1000000)
        if valid:
            self.shell.setMaximumBlockCount(mlc)
            CONF.set(self.ID, 'max_line_count', mlc)

    def change_exteditor(self):
        """Change external editor path"""
        path, valid = QInputDialog.getText(self, self.tr('External editor'),
                          self.tr('External editor executable path:'),
                          QLineEdit.Normal,
                          CONF.get(self.ID, 'external_editor/path'))
        if valid:
            CONF.set(self.ID, 'external_editor/path', unicode(path))
            
    def toggle_wrap_mode(self, checked):
        """Toggle wrap mode"""
        self.shell.toggle_wrap_mode(checked)
        CONF.set(self.ID, 'wrap', checked)
            
    def toggle_calltips(self, checked):
        """Toggle calltips"""
        self.shell.set_calltips(checked)
        CONF.set(self.ID, 'calltips', checked)
            
    def toggle_codecompletion(self, checked):
        """Toggle automatic code completion"""
        self.shell.set_codecompletion_auto(checked)
        CONF.set(self.ID, 'codecompletion/auto', checked)
            
    def toggle_codecompletion_enter(self, checked):
        """Toggle Enter key for code completion"""
        self.shell.set_codecompletion_enter(checked)
        CONF.set(self.ID, 'codecompletion/enter-key', checked)
                
    #----Drag and drop                    
    def dragEnterEvent(self, event):
        """Reimplement Qt method
        Inform Qt about the types of data that the widget accepts"""
        source = event.mimeData()
        if source.hasUrls():
            if mimedata2url(source):
                event.acceptProposedAction()
            else:
                event.ignore()
        elif source.hasText():
            event.acceptProposedAction()
            
    def dropEvent(self, event):
        """Reimplement Qt method
        Unpack dropped data and handle it"""
        source = event.mimeData()
        if source.hasUrls():
            pathlist = mimedata2url(source)
            self.shell.drop_pathlist(pathlist)
        elif source.hasText():
            lines = unicode(source.text())
            self.shell.set_cursor_position('eof')
            self.shell.execute_lines(lines)
        event.acceptProposedAction()
