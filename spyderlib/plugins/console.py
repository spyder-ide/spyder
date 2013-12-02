# -*- coding: utf-8 -*-
#
# Copyright © 2009-2010 Pierre Raybaut
# Licensed under the terms of the MIT License
# (see spyderlib/__init__.py for details)

"""Internal Console Plugin"""

# pylint: disable=C0103
# pylint: disable=R0903
# pylint: disable=R0911
# pylint: disable=R0201

from spyderlib.qt.QtGui import (QVBoxLayout, QFontDialog, QInputDialog,
                                QLineEdit, QMenu)
from spyderlib.qt.QtCore import SIGNAL
from spyderlib.qt.compat import getopenfilename

import os
import sys
import os.path as osp


# Local imports
from spyderlib.baseconfig import _, debug_print
from spyderlib.config import CONF
from spyderlib.utils.misc import get_error_match, remove_backslashes
from spyderlib.utils.qthelpers import (get_icon, create_action, add_actions,
                                       mimedata2url, DialogManager)
from spyderlib.utils.environ import EnvDialog
from spyderlib.widgets.internalshell import InternalShell
from spyderlib.widgets.findreplace import FindReplace
from spyderlib.widgets.dicteditor import DictEditor
from spyderlib.plugins import SpyderPluginWidget
from spyderlib.py3compat import to_text_string, getcwd

    
class Console(SpyderPluginWidget):
    """
    Console widget
    """
    CONF_SECTION = 'internal_console'
    def __init__(self, parent=None, namespace=None, commands=[], message=None,
                 exitfunc=None, profile=False, multithreaded=False):
        SpyderPluginWidget.__init__(self, parent)
        
        debug_print("    ..internal console: initializing")
        self.dialog_manager = DialogManager()

        # Shell
        light_background = self.get_option('light_background')
        self.shell = InternalShell(parent, namespace, commands, message,
                                   self.get_option('max_line_count'),
                                   self.get_plugin_font(), exitfunc, profile,
                                   multithreaded,
                                   light_background=light_background)
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
        
        # Initialize plugin
        self.initialize_plugin()
                
        # Find/replace widget
        self.find_widget = FindReplace(self)
        self.find_widget.set_editor(self.shell)
        self.find_widget.hide()
        self.register_widget_shortcuts("Editor", self.find_widget)

        # Main layout
        layout = QVBoxLayout()
        layout.addWidget(self.shell)
        layout.addWidget(self.find_widget)
        self.setLayout(layout)
        
        # Parameters
        self.shell.toggle_wrap_mode(self.get_option('wrap'))
            
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
        return _('Internal console')
    
    def get_focus_widget(self):
        """
        Return the widget to give focus to when
        this plugin's dockwidget is raised on top-level
        """
        return self.shell
        
    def closing_plugin(self, cancelable=False):
        """Perform actions before parent main window is closed"""
        self.dialog_manager.close_all()
        self.shell.exit_interpreter()
        return True
        
    def refresh_plugin(self):
        pass
    
    def get_plugin_actions(self):
        """Return a list of actions related to plugin"""
        quit_action = create_action(self, _("&Quit"),
                                    icon='exit.png', tip=_("Quit"),
                                    triggered=self.quit)
        self.register_shortcut(quit_action, "_", "Quit", "Ctrl+Q")
        run_action = create_action(self, _("&Run..."), None,
                            'run_small.png', _("Run a Python script"),
                            triggered=self.run_script)
        environ_action = create_action(self,
                            _("Environment variables..."),
                            icon = 'environ.png',
                            tip=_("Show and edit environment variables"
                                        " (for current session)"),
                            triggered=self.show_env)
        syspath_action = create_action(self,
                            _("Show sys.path contents..."),
                            icon = 'syspath.png',
                            tip=_("Show (read-only) sys.path"),
                            triggered=self.show_syspath)
        buffer_action = create_action(self,
                            _("Buffer..."), None,
                            tip=_("Set maximum line count"),
                            triggered=self.change_max_line_count)
        font_action = create_action(self,
                            _("&Font..."), None,
                            'font.png', _("Set shell font style"),
                            triggered=self.change_font)
        exteditor_action = create_action(self,
                            _("External editor path..."), None, None,
                            _("Set external editor executable path"),
                            triggered=self.change_exteditor)
        wrap_action = create_action(self,
                            _("Wrap lines"),
                            toggled=self.toggle_wrap_mode)
        wrap_action.setChecked(self.get_option('wrap'))
        calltips_action = create_action(self, _("Display balloon tips"),
            toggled=self.toggle_calltips)
        calltips_action.setChecked(self.get_option('calltips'))
        codecompletion_action = create_action(self,
                                          _("Automatic code completion"),
                                          toggled=self.toggle_codecompletion)
        codecompletion_action.setChecked(self.get_option('codecompletion/auto'))
        codecompenter_action = create_action(self,
                                    _("Enter key selects completion"),
                                    toggled=self.toggle_codecompletion_enter)
        codecompenter_action.setChecked(self.get_option(
                                                    'codecompletion/enter_key'))
        
        option_menu = QMenu(_("Internal console settings"), self)
        option_menu.setIcon(get_icon('tooloptions.png'))
        add_actions(option_menu, (buffer_action, font_action, wrap_action,
                                  calltips_action, codecompletion_action,
                                  codecompenter_action, exteditor_action))
                    
        plugin_actions = [None, run_action, environ_action, syspath_action,
                          option_menu, None, quit_action]
        
        # Add actions to context menu
        add_actions(self.shell.menu, plugin_actions)
        
        return plugin_actions
    
    def register_plugin(self):
        """Register plugin in Spyder's main window"""
        self.connect(self, SIGNAL('focus_changed()'),
                     self.main.plugin_focus_changed)
        self.main.add_dockwidget(self)
        # Connecting the following signal once the dockwidget has been created:
        self.connect(self.shell, SIGNAL('traceback_available()'),
                     self.traceback_available)
    
    def traceback_available(self):
        """Traceback is available in the internal console: showing the 
        internal console automatically to warn the user"""
        if CONF.get('main', 'show_internal_console_if_traceback', False):
            self.dockwidget.show()
            self.dockwidget.raise_()
        
    #------ Public API ---------------------------------------------------------
    def quit(self):
        """Quit mainwindow"""
        self.main.close()
        
    def show_env(self):
        """Show environment variables"""
        self.dialog_manager.show(EnvDialog())

    def show_syspath(self):
        """Show sys.path"""
        editor = DictEditor()
        editor.setup(sys.path, title="sys.path", readonly=True,
                     width=600, icon='syspath.png')
        self.dialog_manager.show(editor)
        
    def run_script(self, filename=None, silent=False, set_focus=False,
                   args=None):
        """Run a Python script"""
        if filename is None:
            self.shell.interpreter.restore_stds()
            filename, _selfilter = getopenfilename(self, _("Run Python script"),
                   getcwd(), _("Python scripts")+" (*.py ; *.pyw ; *.ipy)")
            self.shell.interpreter.redirect_stds()
            if filename:
                os.chdir( osp.dirname(filename) )
                filename = osp.basename(filename)
            else:
                return
        filename = osp.abspath(filename)
        rbs = remove_backslashes
        command = "runfile('%s', args='%s')" % (rbs(filename), rbs(args))
        if set_focus:
            self.shell.setFocus()
        if self.dockwidget and not self.ismaximized:
            self.dockwidget.setVisible(True)
            self.dockwidget.raise_()
        self.shell.write(command+'\n')
        self.shell.run_command(command)

            
    def go_to_error(self, text):
        """Go to error if relevant"""
        match = get_error_match(to_text_string(text))
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
        self.shell.execute_lines(to_text_string(lines))
        self.shell.setFocus()
        
    def change_font(self):
        """Change console font"""
        font, valid = QFontDialog.getFont(self.get_plugin_font(),
                       self, _("Select a new font"))
        if valid:
            self.shell.set_font(font)
            self.set_plugin_font(font)
        
    def change_max_line_count(self):
        "Change maximum line count"""
        mlc, valid = QInputDialog.getInteger(self, _('Buffer'),
                                           _('Maximum line count'),
                                           self.get_option('max_line_count'),
                                           0, 1000000)
        if valid:
            self.shell.setMaximumBlockCount(mlc)
            self.set_option('max_line_count', mlc)

    def change_exteditor(self):
        """Change external editor path"""
        path, valid = QInputDialog.getText(self, _('External editor'),
                          _('External editor executable path:'),
                          QLineEdit.Normal,
                          self.get_option('external_editor/path'))
        if valid:
            self.set_option('external_editor/path', to_text_string(path))
            
    def toggle_wrap_mode(self, checked):
        """Toggle wrap mode"""
        self.shell.toggle_wrap_mode(checked)
        self.set_option('wrap', checked)
            
    def toggle_calltips(self, checked):
        """Toggle calltips"""
        self.shell.set_calltips(checked)
        self.set_option('calltips', checked)
            
    def toggle_codecompletion(self, checked):
        """Toggle automatic code completion"""
        self.shell.set_codecompletion_auto(checked)
        self.set_option('codecompletion/auto', checked)
            
    def toggle_codecompletion_enter(self, checked):
        """Toggle Enter key for code completion"""
        self.shell.set_codecompletion_enter(checked)
        self.set_option('codecompletion/enter_key', checked)
                
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
            lines = to_text_string(source.text())
            self.shell.set_cursor_position('eof')
            self.shell.execute_lines(lines)
        event.acceptProposedAction()
