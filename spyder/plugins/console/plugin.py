# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""Internal Console Plugin"""

# pylint: disable=C0103
# pylint: disable=R0903
# pylint: disable=R0911
# pylint: disable=R0201

# Standard library imports
import os
import os.path as osp
import sys
import logging

# Third party imports
from qtpy.compat import getopenfilename
from qtpy.QtCore import Qt, Signal, Slot
from qtpy.QtWidgets import QInputDialog, QLineEdit, QMenu, QHBoxLayout

# Local imports
from spyder.config.base import _, DEV, get_debug_level
from spyder.config.manager import CONF
from spyder.utils import icon_manager as ima
from spyder.utils.environ import EnvDialog
from spyder.utils.misc import (get_error_match, remove_backslashes,
                               getcwd_or_home)
from spyder.utils.qthelpers import (add_actions, create_action,
                                    create_plugin_layout, DialogManager,
                                    mimedata2url, MENU_SEPARATOR)
from spyder.plugins.console.widgets.internalshell import InternalShell
from spyder.widgets.findreplace import FindReplace
from spyder.plugins.variableexplorer.widgets.collectionseditor import (
        CollectionsEditor)
from spyder.widgets.reporterror import SpyderErrorDialog
from spyder.api.plugins import SpyderPluginWidget
from spyder.py3compat import to_text_string

logger = logging.getLogger(__name__)


class Console(SpyderPluginWidget):
    """
    Console widget
    """
    CONF_SECTION = 'internal_console'
    CONF_FILE = False
    focus_changed = Signal()
    redirect_stdio = Signal(bool)
    edit_goto = Signal(str, int, str)
    
    def __init__(self, parent=None, namespace=None, commands=[], message=None,
                 exitfunc=None, profile=False, multithreaded=False):
        SpyderPluginWidget.__init__(self, parent)
        logger.info("Initializing...")
        self.dialog_manager = DialogManager()

        # Shell
        self.shell = InternalShell(parent, namespace, commands, message,
                                   self.get_option('max_line_count'),
                                   self.get_font(), exitfunc, profile,
                                   multithreaded)
        self.shell.status.connect(lambda msg:
                                  self.sig_show_status_message.emit(msg, 0))
        self.shell.go_to_error.connect(self.go_to_error)
        self.shell.focus_changed.connect(lambda: self.focus_changed.emit())

        # Redirecting some signals:
        self.shell.redirect_stdio.connect(lambda state:
                                          self.redirect_stdio.emit(state))

        # Find/replace widget
        self.find_widget = FindReplace(self)
        self.find_widget.set_editor(self.shell)
        self.find_widget.hide()
        self.register_widget_shortcuts(self.find_widget)

        # Main layout
        btn_layout = QHBoxLayout()
        btn_layout.setAlignment(Qt.AlignLeft)
        btn_layout.addStretch()
        btn_layout.addWidget(self.options_button, Qt.AlignRight)
        layout = create_plugin_layout(btn_layout)
        layout.addWidget(self.shell)
        layout.addWidget(self.find_widget)
        self.setLayout(layout)
        
        # Parameters
        self.shell.toggle_wrap_mode(self.get_option('wrap'))
            
        # Accepting drops
        self.setAcceptDrops(True)

        # Traceback MessageBox
        self.error_dlg = None
        self.error_traceback = ""
        self.dismiss_error = False

    #------ Private API --------------------------------------------------------
    def set_historylog(self, historylog):
        """Bind historylog instance to this console
        Not used anymore since v2.0"""
        historylog.add_history(self.shell.history_filename)
        self.shell.append_to_history.connect(historylog.append_to_history)

    def set_help(self, help_plugin):
        """Bind help instance to this console"""
        self.shell.help = help_plugin

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

    def update_font(self):
        """Update font from Preferences"""
        font = self.get_font()
        self.shell.set_font(font)

    def closing_plugin(self, cancelable=False):
        """Perform actions before parent main window is closed"""
        self.dialog_manager.close_all()
        self.shell.exit_interpreter()
        return True

    def get_plugin_actions(self):
        """Return a list of actions related to plugin"""
        quit_action = create_action(self, _("&Quit"),
                                    icon=ima.icon('exit'), 
                                    tip=_("Quit"),
                                    triggered=self.quit)
        self.register_shortcut(quit_action, "_", "Quit", "Ctrl+Q")
        run_action = create_action(self, _("&Run..."), None,
                            ima.icon('run_small'),
                            _("Run a Python script"),
                            triggered=self.run_script)
        environ_action = create_action(self,
                            _("Environment variables..."),
                            icon=ima.icon('environ'),
                            tip=_("Show and edit environment variables"
                                        " (for current session)"),
                            triggered=self.show_env)
        syspath_action = create_action(self,
                            _("Show sys.path contents..."),
                            icon=ima.icon('syspath'),
                            tip=_("Show (read-only) sys.path"),
                            triggered=self.show_syspath)
        buffer_action = create_action(self,
                            _("Buffer..."), None,
                            tip=_("Set maximum line count"),
                            triggered=self.change_max_line_count)
        exteditor_action = create_action(self,
                            _("External editor path..."), None, None,
                            _("Set external editor executable path"),
                            triggered=self.change_exteditor)
        wrap_action = create_action(self,
                            _("Wrap lines"),
                            toggled=self.toggle_wrap_mode)
        wrap_action.setChecked(self.get_option('wrap'))
        codecompletion_action = create_action(self,
                                          _("Automatic code completion"),
                                          toggled=self.toggle_codecompletion)
        codecompletion_action.setChecked(self.get_option('codecompletion/auto'))
        
        option_menu = QMenu(_('Internal console settings'), self)
        option_menu.setIcon(ima.icon('tooloptions'))
        add_actions(option_menu, (buffer_action, wrap_action,
                                  codecompletion_action,
                                  exteditor_action))
                    
        plugin_actions = [None, run_action, environ_action, syspath_action,
                          option_menu, MENU_SEPARATOR, quit_action]

        return plugin_actions
    
    def register_plugin(self):
        """Register plugin in Spyder's main window"""
        self.focus_changed.connect(self.main.plugin_focus_changed)
        self.add_dockwidget()
        # Connecting the following signal once the dockwidget has been created:
        self.shell.exception_occurred.connect(self.exception_occurred)
    
    def exception_occurred(self, text, is_traceback, is_pyls_error=False):
        """
        Exception ocurred in the internal console.

        Show a QDialog or the internal console to warn the user.
        """
        # Skip errors without traceback or dismiss
        if (not is_traceback and self.error_dlg is None) or self.dismiss_error:
            return

        if CONF.get('main', 'show_internal_errors'):
            if self.error_dlg is None:
                self.error_dlg = SpyderErrorDialog(self)
                self.error_dlg.set_color_scheme(CONF.get('appearance',
                                                         'selected'))
                self.error_dlg.close_btn.clicked.connect(self.close_error_dlg)
                self.error_dlg.rejected.connect(self.remove_error_dlg)
                self.error_dlg.details.go_to_error.connect(self.go_to_error)

            if is_pyls_error:
                title = "Internal Python Language Server error"
                self.error_dlg.set_title(title)
                self.error_dlg.title.setEnabled(False)
            self.error_dlg.append_traceback(text)
            self.error_dlg.show()
        elif DEV or get_debug_level():
            self.switch_to_plugin()

    def close_error_dlg(self):
        """Close error dialog."""
        if self.error_dlg.dismiss_box.isChecked():
            self.dismiss_error = True
        self.error_dlg.reject()

    def remove_error_dlg(self):
        """Remove error dialog."""
        self.error_dlg = None

    #------ Public API ---------------------------------------------------------
    @Slot()
    def quit(self):
        """Quit mainwindow"""
        self.main.close()
    
    @Slot()
    def show_env(self):
        """Show environment variables"""
        self.dialog_manager.show(EnvDialog(parent=self))
    
    def get_sys_path(self):
        """Return the `sys.path`."""
        return sys.path

    @Slot()
    def show_syspath(self):
        """Show sys.path"""
        editor = CollectionsEditor(parent=self)
        editor.setup(sys.path, title="sys.path", readonly=True,
                     width=600, icon=ima.icon('syspath'))
        self.dialog_manager.show(editor)
    
    @Slot()
    def run_script(self, filename=None, silent=False, set_focus=False,
                   args=None):
        """Run a Python script"""
        if filename is None:
            self.shell.interpreter.restore_stds()
            filename, _selfilter = getopenfilename(
                    self, _("Run Python script"), getcwd_or_home(),
                    _("Python scripts")+" (*.py ; *.pyw ; *.ipy)")
            self.shell.interpreter.redirect_stds()
            if filename:
                os.chdir( osp.dirname(filename) )
                filename = osp.basename(filename)
            else:
                return
        logger.debug("Running script with %s", args)
        filename = osp.abspath(filename)
        rbs = remove_backslashes
        command = "runfile('%s', args='%s')" % (rbs(filename), rbs(args))
        if set_focus:
            self.shell.setFocus()
        if self.dockwidget:
            self.switch_to_plugin()
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
            self.edit_goto.emit(osp.abspath(filename), goto, '')
        
    def execute_lines(self, lines):
        """Execute lines and give focus to shell"""
        self.shell.execute_lines(to_text_string(lines))
        self.shell.setFocus()

    @Slot()
    def change_max_line_count(self):
        "Change maximum line count"""
        mlc, valid = QInputDialog.getInt(self, _('Buffer'),
                                           _('Maximum line count'),
                                           self.get_option('max_line_count'),
                                           0, 1000000)
        if valid:
            self.shell.setMaximumBlockCount(mlc)
            self.set_option('max_line_count', mlc)

    @Slot()
    def change_exteditor(self):
        """Change external editor path"""
        path, valid = QInputDialog.getText(self, _('External editor'),
                          _('External editor executable path:'),
                          QLineEdit.Normal,
                          self.get_option('external_editor/path'))
        if valid:
            self.set_option('external_editor/path', to_text_string(path))
    
    @Slot(bool)
    def toggle_wrap_mode(self, checked):
        """Toggle wrap mode"""
        self.shell.toggle_wrap_mode(checked)
        self.set_option('wrap', checked)

    @Slot(bool)
    def toggle_codecompletion(self, checked):
        """Toggle automatic code completion"""
        self.shell.set_codecompletion_auto(checked)
        self.set_option('codecompletion/auto', checked)

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
