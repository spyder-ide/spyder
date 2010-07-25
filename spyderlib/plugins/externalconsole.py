# -*- coding: utf-8 -*-
#
# Copyright © 2009 Pierre Raybaut
# Licensed under the terms of the MIT License
# (see spyderlib/__init__.py for details)

"""External Console plugin"""

# pylint: disable-msg=C0103
# pylint: disable-msg=R0903
# pylint: disable-msg=R0911
# pylint: disable-msg=R0201

from PyQt4.QtGui import (QVBoxLayout, QFileDialog, QFontDialog, QMessageBox,
                         QInputDialog, QLineEdit)
from PyQt4.QtCore import SIGNAL, QString, Qt

import sys, os
import os.path as osp

# For debugging purpose:
STDOUT = sys.stdout

# Local imports
from spyderlib.config import get_icon
from spyderlib.utils import programs
from spyderlib.utils.qthelpers import create_action, mimedata2url
from spyderlib.widgets.tabs import Tabs
from spyderlib.widgets.externalshell.pythonshell import ExternalPythonShell
from spyderlib.widgets.externalshell.systemshell import ExternalSystemShell
from spyderlib.widgets.shellhelpers import get_error_match
from spyderlib.widgets.findreplace import FindReplace
from spyderlib.plugins import SpyderPluginWidget


class ExternalConsole(SpyderPluginWidget):
    """
    Console widget
    """
    ID = 'external_shell'
    def __init__(self, parent, light_mode):
        self.light_mode = light_mode
        self.commands = []
        self.tabwidget = None
        self.menu_actions = None
        self.inspector = None
        self.historylog = None
        self.variableexplorer = None # variable explorer plugin
        
        self.ipython_count = 0
        self.python_count = 0
        self.terminal_count = 0
        
        if self.get_option('ipython_options', None) is None:
            self.set_option('ipython_options',
                            self.get_default_ipython_options())
        
        self.shells = []
        self.filenames = []
        self.icons = []
        self.runfile_args = ""
        
        SpyderPluginWidget.__init__(self, parent)
        
        layout = QVBoxLayout()
        self.tabwidget = Tabs(self, self.menu_actions)
        self.connect(self.tabwidget, SIGNAL('currentChanged(int)'),
                     self.refresh_plugin)
        self.connect(self.tabwidget, SIGNAL('move_data(int,int)'),
                     self.move_tab)
                     
        self.tabwidget.set_close_function(self.close_console)

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
        icons = self.icons.pop(index_from)
        
        self.filenames.insert(index_to, filename)
        self.shells.insert(index_to, shell)
        self.icons.insert(index_to, icons)

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
        
    def set_inspector(self, inspector):
        """Bind inspector instance to this console"""
        self.inspector = inspector
        inspector.set_external_console(self)
        
    def set_variableexplorer(self, variableexplorer):
        """Set variable explorer plugin"""
        self.variableexplorer = variableexplorer
        
    def __find_python_shell(self, interpreter_only=False):
        current_index = self.tabwidget.currentIndex()
        if current_index == -1:
            return
        from spyderlib.widgets.externalshell import pythonshell
        for index in [current_index]+range(self.tabwidget.count()):
            shellwidget = self.tabwidget.widget(index)
            if isinstance(shellwidget, pythonshell.ExternalPythonShell):
                if not interpreter_only or shellwidget.is_interpreter():
                    self.tabwidget.setCurrentIndex(index)
                    return shellwidget
                
    def get_running_python_shell(self):
        """
        Called by object inspector to retrieve a running Python shell instance
        """
        current_index = self.tabwidget.currentIndex()
        if current_index == -1:
            return
        from spyderlib.widgets.externalshell import pythonshell
        shellwidgets = [self.tabwidget.widget(index)
                        for index in range(self.tabwidget.count())]
        shellwidgets = [_w for _w in shellwidgets
                        if isinstance(_w, pythonshell.ExternalPythonShell) \
                        and _w.is_running()]
        if shellwidgets:
            # First, iterate on interpreters only:
            for shellwidget in shellwidgets:
                if shellwidget.is_interpreter():
                    return shellwidget.shell
            else:
                return shellwidgets[0].shell
        
    def get_runfile_args(self):
        arguments, valid = QInputDialog.getText(self, self.tr('Arguments'),
                                          self.tr('Command line arguments:'),
                                          QLineEdit.Normal, self.runfile_args)
        if valid:
            self.runfile_args = unicode(arguments)
        return valid
        
    def run_script_in_current_shell(self, filename, ask_for_arguments):
        """Run script in current shell, if any"""
        shellwidget = self.__find_python_shell(interpreter_only=True)
        if shellwidget is not None and shellwidget.is_running():
            if ask_for_arguments:
                if not self.get_runfile_args():
                    return
                line = "runfile(r'%s', args='%s')" % (unicode(filename),
                                                      self.runfile_args)
            else:
                line = "runfile(r'%s')" % unicode(filename)
            shellwidget.shell.execute_lines(line)
            shellwidget.shell.setFocus()
            
    def set_current_shell_working_directory(self, directory):
        """Set current shell working directory"""
        shellwidget = self.__find_python_shell()
        if shellwidget is not None and shellwidget.is_running():
            shellwidget.shell.set_cwd(unicode(directory))
        
    def execute_python_code(self, lines):
        """Execute Python code in an already opened Python interpreter"""
        shellwidget = self.__find_python_shell()
        if shellwidget is not None:
            shellwidget.shell.execute_lines(unicode(lines))
            shellwidget.shell.setFocus()
        
    def start(self, fname, wdir=None, ask_for_arguments=False,
              interact=False, debug=False, python=True,
              ipython=False, arguments=None, current=False):
        """Start new console"""
        # Note: fname is None <=> Python interpreter
        fname = unicode(fname) if isinstance(fname, QString) else fname
        wdir = unicode(wdir) if isinstance(wdir, QString) else wdir

        if fname is not None and fname in self.filenames:
            index = self.filenames.index(fname)
            if self.get_option('single_tab'):
                old_shell = self.shells[index]
                if old_shell.is_running():
                    answer = QMessageBox.question(self, self.get_plugin_title(),
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
        pythonpath = self.main.get_spyder_pythonpath()
        if python:
            mpl_patch_enabled = self.get_option('mpl_patch/enabled')
            umd_enabled = self.get_option('umd/enabled')
            umd_namelist = self.get_option('umd/namelist')
            umd_verbose = self.get_option('umd/verbose')
            shellwidget = ExternalPythonShell(self, fname, wdir, self.commands,
                           interact, debug, path=pythonpath, ipython=ipython,
                           arguments=arguments, stand_alone=self.light_mode,
                           umd_enabled=umd_enabled, umd_namelist=umd_namelist,
                           umd_verbose=umd_verbose,
                           mpl_patch_enabled=mpl_patch_enabled)
            if self.variableexplorer is not None:
                self.variableexplorer.add_shellwidget(shellwidget)
        else:
            shellwidget = ExternalSystemShell(self, wdir, path=pythonpath)
        
        # Code completion / calltips
        case_sensitive = self.get_option('codecompletion/case-sensitivity')
        show_single = self.get_option('codecompletion/select-single')
        from_document = self.get_option('codecompletion/from-document')
        shellwidget.shell.setup_code_completion(case_sensitive, show_single,
                                                 from_document)
        
        shellwidget.shell.setMaximumBlockCount( self.get_option(
                                                          'max_line_count') )
        shellwidget.shell.set_font( self.get_plugin_font() )
        shellwidget.shell.toggle_wrap_mode( self.get_option('wrap') )
        shellwidget.shell.set_calltips( self.get_option('calltips') )
        shellwidget.shell.set_codecompletion_auto( self.get_option(
                                                 'codecompletion/auto') )
        shellwidget.shell.set_codecompletion_enter(self.get_option(
                                                 'codecompletion/enter-key'))
        if python and self.inspector is not None:
            shellwidget.shell.set_inspector(self.inspector)
        if self.historylog is not None:
            self.historylog.add_history(shellwidget.shell.history_filename)
            self.connect(shellwidget.shell,
                         SIGNAL('append_to_history(QString,QString)'),
                         self.historylog.append_to_history)
        self.connect(shellwidget.shell, SIGNAL("go_to_error(QString)"),
                     self.go_to_error)
        self.connect(shellwidget.shell, SIGNAL("focus_changed()"),
                     lambda: self.emit(SIGNAL("focus_changed()")))
        if python:
            if fname is None:
                if ipython:
                    self.ipython_count += 1
                    tab_name = "IPython %d" % self.ipython_count
                    tab_icon1 = get_icon('ipython.png')
                    tab_icon2 = get_icon('ipython_t.png')
                else:
                    self.python_count += 1
                    tab_name = "Python %d" % self.python_count
                    tab_icon1 = get_icon('python.png')
                    tab_icon2 = get_icon('python_t.png')
            else:
                tab_name = osp.basename(fname)
                tab_icon1 = get_icon('run.png')
                tab_icon2 = get_icon('terminated.png')
        else:
            fname = id(shellwidget)
            if os.name == 'nt':
                tab_name = self.tr("Command Window")
            else:
                tab_name = self.tr("Terminal")
            self.terminal_count += 1
            tab_name += (" %d" % self.terminal_count)
            tab_icon1 = get_icon('cmdprompt.png')
            tab_icon2 = get_icon('cmdprompt_t.png')
        self.shells.insert(index, shellwidget)
        self.filenames.insert(index, fname)
        self.icons.insert(index, (tab_icon1, tab_icon2))
        if index is None:
            index = self.tabwidget.addTab(shellwidget, tab_name)
        else:
            self.tabwidget.insertTab(index, shellwidget, tab_name)
        
        self.connect(shellwidget, SIGNAL("started()"),
                     lambda sid=id(shellwidget): self.process_started(sid))
        self.connect(shellwidget, SIGNAL("finished()"),
                     lambda sid=id(shellwidget): self.process_finished(sid))
        self.find_widget.set_editor(shellwidget.shell)
        self.tabwidget.setTabToolTip(index, fname if wdir is None else wdir)
        self.tabwidget.setCurrentIndex(index)
        if self.dockwidget and not self.ismaximized:
            self.dockwidget.setVisible(True)
            self.dockwidget.raise_()
        
        self.toggle_icontext(self.get_option('show_icontext'))
        
        # Start process and give focus to console
        shellwidget.start(ask_for_arguments)
        shellwidget.shell.setFocus()
        
    #------ Private API --------------------------------------------------------
    def process_started(self, shell_id):
        for index, shell in enumerate(self.shells):
            if id(shell) == shell_id:
                icon, _icon = self.icons[index]
                self.tabwidget.setTabIcon(index, icon)
                if self.inspector is not None:
                    self.inspector.set_shell(shell.shell)
                if self.variableexplorer is not None:
                    self.variableexplorer.add_shellwidget(shell)
        
    def process_finished(self, shell_id):
        for index, shell in enumerate(self.shells):
            if id(shell) == shell_id:
                _icon, icon = self.icons[index]
                self.tabwidget.setTabIcon(index, icon)
                if self.inspector is not None:
                    self.inspector.shell_terminated(shell.shell)
        if self.variableexplorer is not None:
            self.variableexplorer.remove_shellwidget(shell_id)
        
    #------ SpyderPluginWidget API ---------------------------------------------    
    def get_plugin_title(self):
        """Return widget title"""
        return self.tr('Console')
    
    def get_focus_widget(self):
        """
        Return the widget to give focus to when
        this plugin's dockwidget is raised on top-level
        """
        return self.tabwidget.currentWidget()
        
    def get_plugin_actions(self):
        """Setup actions"""
        interpreter_action = create_action(self,
                            self.tr("Open &interpreter"), None,
                            'python.png', self.tr("Open a Python interpreter"),
                            triggered=self.open_interpreter)
        if os.name == 'nt':
            text = self.tr("Open &command prompt")
            tip = self.tr("Open a Windows command prompt")
        else:
            text = self.tr("Open &terminal")
            tip = self.tr("Open a terminal window inside Spyder")
        console_action = create_action(self, text, None, 'cmdprompt.png', tip,
                            triggered=self.open_terminal)
        run_action = create_action(self,
                            self.tr("&Run..."), None,
                            'run_small.png', self.tr("Run a Python script"),
                            triggered=self.run_script)

        mpl_patch_action = create_action(self,
                self.tr("Patch Matplotlib figures (options button)"),
                tip=self.tr("Patch the matplotlib library to add the "
                            "options button (plot parameters editing "
                            "dialog box)"),
                toggled=lambda checked:
                self.set_option('mpl_patch/enabled', checked))
        mpl_patch_action.setChecked( self.get_option('mpl_patch/enabled') )
        
        umd_action = create_action(self,
                self.tr("UMD (force modules to be completely reloaded)"),
                tip=self.tr("Force Python to reload modules imported when "
                            "executing a script in the external console "
                            "with the 'runfile' function (UMD: User Module "
                            "Deleter)"),
                toggled=self.toggle_umd)
        umd_action.setChecked( self.get_option('umd/enabled') )
        umd_verbose_action = create_action(self,
                self.tr("Show reloaded modules list"),
                toggled=self.toggle_umd_verbose)
        umd_verbose_action.setChecked( self.get_option('umd/verbose') )
        umd_namelist_action = create_action(self,
                            self.tr("UMD excluded modules..."), None,
                            tip=self.tr("Set UMD excluded modules name list"),
                            triggered=self.set_umd_namelist)
        
        python_startup = self.get_option('open_python_at_startup', None)
        ipython_startup = self.get_option('open_ipython_at_startup', None)
        if ipython_startup is None:
            ipython_startup = programs.is_module_installed("IPython")
            self.set_option('open_ipython_at_startup', ipython_startup)
        if python_startup is None:
            python_startup = not ipython_startup
            self.set_option('open_python_at_startup', python_startup)
        python_startup_action = create_action(self,
                self.tr("Open a Python interpreter at startup"),
                toggled=lambda checked:
                self.set_option('open_python_at_startup', checked))
        python_startup_action.setChecked(python_startup)
        ipython_startup_action = create_action(self,
                self.tr("Open a IPython interpreter at startup"),
                toggled=lambda checked:
                self.set_option('open_ipython_at_startup', checked))
        ipython_startup_action.setChecked(ipython_startup)
        
        buffer_action = create_action(self,
                            self.tr("Buffer..."), None,
                            tip=self.tr("Set maximum line count"),
                            triggered=self.change_max_line_count)
        font_action = create_action(self,
                            self.tr("&Font..."), None,
                            'font.png', self.tr("Set shell font style"),
                            triggered=self.change_font)
        wrap_action = create_action(self,
                            self.tr("Wrap lines"),
                            toggled=self.toggle_wrap_mode)
        wrap_action.setChecked( self.get_option('wrap') )
        calltips_action = create_action(self, self.tr("Balloon tips"),
                            toggled=self.toggle_calltips)
        calltips_action.setChecked( self.get_option('calltips') )
        codecompletion_action = create_action(self,
                                          self.tr("Automatic code completion"),
                                          toggled=self.toggle_codecompletion)
        codecompletion_action.setChecked( self.get_option(
                                                   'codecompletion/auto') )
        codecompenter_action = create_action(self,
                                    self.tr("Enter key selects completion"),
                                    toggled=self.toggle_codecompletion_enter)
        codecompenter_action.setChecked( self.get_option(
                                                  'codecompletion/enter-key') )
        singletab_action = create_action(self,
                            self.tr("One tab per script"),
                            toggled=self.toggle_singletab)
        singletab_action.setChecked( self.get_option('single_tab') )
        icontext_action = create_action(self, self.tr("Show icons and text"),
                                        toggled=self.toggle_icontext)
        icontext_action.setChecked( self.get_option('show_icontext') )
        
        self.menu_actions = [interpreter_action, console_action, run_action]
        if programs.is_module_installed("matplotlib"):
            self.menu_actions += [None, mpl_patch_action]
        self.menu_actions += [
             None, umd_action, umd_verbose_action, umd_namelist_action,
             None, python_startup_action, ipython_startup_action,
             None, buffer_action, font_action, wrap_action, calltips_action,
             codecompletion_action, codecompenter_action, singletab_action,
             icontext_action]
        
        ipython_action = create_action(self,
                            self.tr("Open IPython interpreter"), None,
                            'ipython.png',
                            self.tr("Open an IPython interpreter"),
                            triggered=self.open_ipython)
        ipython_options_action = create_action(self,
                            self.tr("IPython interpreter options..."), None,
                            tip=self.tr("Set IPython interpreter "
                                        "command line arguments"),
                            triggered=self.set_ipython_options)
        if programs.is_module_installed("IPython"):
            self.menu_actions.insert(3, ipython_options_action)
            self.menu_actions.insert(1, ipython_action)
        
        return (self.menu_actions, None)
    
    def open_interpreter_at_startup(self):
        """Open an interpreter at startup, IPython if module is available"""
        if self.get_option('open_ipython_at_startup') \
           and programs.is_module_installed("IPython"):
            self.open_ipython()
        if self.get_option('open_python_at_startup'):
            self.open_interpreter()
        
    def closing_plugin(self, cancelable=False):
        """Perform actions before parent main window is closed"""
        for shell in self.shells:
            shell.process.kill()
        return True
    
    def refresh_plugin(self):
        """Refresh tabwidget"""
        if self.tabwidget.count():
            editor = self.tabwidget.currentWidget().shell
            editor.setFocus()
        else:
            editor = None
        self.find_widget.set_editor(editor)
    
    #------ Public API ---------------------------------------------------------
    def open_interpreter(self, wdir=None):
        """Open interpreter"""
        if wdir is None:
            wdir = os.getcwdu()
        self.start(fname=None, wdir=unicode(wdir), ask_for_arguments=False,
                   interact=True, debug=False, python=True)
        
    def get_default_ipython_options(self):
        """Return default ipython command line arguments"""
        default_options = []
        if programs.is_module_installed('matplotlib'):
            default_options.append("-pylab")
        else:
            default_options.append("-q4thread")
        default_options.append("-colors LightBG")
        default_options.append("-xmode Plain")
        for editor_name in ("scite", "gedit"):
            real_name = programs.get_nt_program_name(editor_name)
            if programs.is_program_installed(real_name):
                default_options.append("-editor "+real_name)
                break
        return " ".join(default_options)
        
    def open_ipython(self, wdir=None):
        """Open IPython"""
        if wdir is None:
            wdir = os.getcwdu()
        self.start(fname=None, wdir=unicode(wdir), ask_for_arguments=False,
                   interact=True, debug=False, python=True, ipython=True,
                   arguments=self.get_option('ipython_options', ""))
        
    def open_terminal(self, wdir=None):
        """Open terminal"""
        if wdir is None:
            wdir = os.getcwdu()
        self.start(fname=None, wdir=unicode(wdir), ask_for_arguments=False,
                   interact=True, debug=False, python=False)
        
    def run_script(self):
        """Run a Python script"""
        self.emit(SIGNAL('redirect_stdio(bool)'), False)
        filename = QFileDialog.getOpenFileName(self,
                      self.tr("Run Python script"), os.getcwdu(),
                      self.tr("Python scripts")+" (*.py ; *.pyw)")
        self.emit(SIGNAL('redirect_stdio(bool)'), True)
        if filename:
            self.start(fname=unicode(filename), wdir=None,
                       ask_for_arguments=False, interact=False, debug=False)
        
    def change_font(self):
        """Change console font"""
        font, valid = QFontDialog.getFont(self.get_plugin_font(),
                       self, self.tr("Select a new font"))
        if valid:
            for index in range(self.tabwidget.count()):
                self.tabwidget.widget(index).shell.set_font(font)
            self.set_plugin_font(font)
        
    def change_max_line_count(self):
        "Change maximum line count"""
        mlc, valid = QInputDialog.getInteger(self, self.tr('Buffer'),
                                           self.tr('Maximum line count'),
                                           self.get_option('max_line_count'),
                                           10, 1000000)
        if valid:
            for index in range(self.tabwidget.count()):
                self.tabwidget.widget(index).shell.setMaximumBlockCount(mlc)
            self.set_option('max_line_count', mlc)
            
    def set_ipython_options(self):
        """Set IPython interpreter arguments"""
        arguments, valid = QInputDialog.getText(self,
                      self.tr('IPython'),
                      self.tr('IPython command line options:\n'
                              '(Qt4 support: -q4thread)\n'
                              '(Qt4 and matplotlib support: -q4thread -pylab)'),
                      QLineEdit.Normal, self.get_option('ipython_options'))
        if valid:
            self.set_option('ipython_options', unicode(arguments))
        
    def toggle_umd(self, checked):
        """Toggle UMD"""
        self.set_option('umd/enabled', checked)
        if checked and self.isVisible():
            QMessageBox.warning(self, self.get_plugin_title(),
                self.tr("This option will enable the User Module Deleter (UMD) "
                        "in Python/IPython interpreters. UMD forces Python to "
                        "reload deeply modules during import when running a "
                        "Python script using the Spyder's builtin function "
                        "<b>runfile</b>."
                        "<br><br><b>1.</b> UMD may require to restart the "
                        "Python interpreter in which it will be called "
                        "(otherwise only newly imported modules will be "
                        "reloaded when executing scripts)."
                        "<br><br><b>2.</b> If errors occur when re-running a "
                        "PyQt-based program, please check that the Qt objects "
                        "are properly destroyed (e.g. you may have to use the "
                        "attribute <b>Qt.WA_DeleteOnClose</b> on your main "
                        "window, using the <b>setAttribute</b> method)"),
                QMessageBox.Ok)
            
    def __umd_settings_info(self):
        QMessageBox.information(self, self.tr('UMD'),
                                self.tr("Please note that these changes will "
                                        "be applied only to new Python/IPython "
                                        "interpreters"),
                                QMessageBox.Ok)
            
    def toggle_umd_verbose(self, checked):
        """Toggle UMD"""
        self.set_option('umd/verbose', checked)
        if self.isVisible():
            self.__umd_settings_info()
            
    def set_umd_namelist(self):
        """Set UMD excluded modules name list"""
        arguments, valid = QInputDialog.getText(self, self.tr('UMD'),
                                  self.tr('UMD excluded modules:\n'
                                          '(example: guidata, guiqwt)'),
                                  QLineEdit.Normal,
                                  ", ".join(self.get_option('umd/namelist')))
        if valid:
            namelist = unicode(arguments).replace(' ', '').split(',')
            fixed_namelist = [module_name for module_name in namelist
                              if programs.is_module_installed(module_name)]
            invalid = ", ".join(set(namelist)-set(fixed_namelist))
            if invalid:
                QMessageBox.warning(self, self.tr('UMD'),
                                    self.tr("The following modules are not "
                                            "installed on your machine:\n%1"
                                            ).arg(invalid), QMessageBox.Ok)
            self.__umd_settings_info()
            self.set_option('umd/namelist', fixed_namelist)
        
    def toggle_wrap_mode(self, checked):
        """Toggle wrap mode"""
        if self.tabwidget is None:
            return
        for shell in self.shells:
            shell.shell.toggle_wrap_mode(checked)
        self.set_option('wrap', checked)
            
    def toggle_calltips(self, checked):
        """Toggle calltips"""
        if self.tabwidget is None:
            return
        for shell in self.shells:
            shell.shell.set_calltips(checked)
        self.set_option('calltips', checked)
            
    def toggle_codecompletion(self, checked):
        """Toggle automatic code completion"""
        if self.tabwidget is None:
            return
        for shell in self.shells:
            shell.shell.set_codecompletion_auto(checked)
        self.set_option('codecompletion/auto', checked)
            
    def toggle_codecompletion_enter(self, checked):
        """Toggle Enter key for code completion"""
        if self.tabwidget is None:
            return
        for shell in self.shells:
            shell.shell.set_codecompletion_enter(checked)
        self.set_option('codecompletion/enter-key', checked)
        
    def toggle_singletab(self, checked):
        """Toggle single tab mode"""
        self.set_option('single_tab', checked)

    def toggle_icontext(self, checked):
        """Toggle icon text"""
        self.set_option('show_icontext', checked)
        if self.tabwidget is None:
            return
        for index in range(self.tabwidget.count()):
            for widget in self.tabwidget.widget(index).get_toolbar_buttons():
                if checked:
                    widget.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
                else:
                    widget.setToolButtonStyle(Qt.ToolButtonIconOnly)
                
    def go_to_error(self, text):
        """Go to error if relevant"""
        match = get_error_match(unicode(text))
        if match:
            fname, lnb = match.groups()
            self.emit(SIGNAL("edit_goto(QString,int,QString)"),
                      osp.abspath(fname), int(lnb), '')
            
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
        if source.hasUrls():
            if mimedata2url(source):
                pathlist = mimedata2url(source)
                shellwidget = self.tabwidget.currentWidget()
                if all([self.__is_python_script(qstr) for qstr in pathlist]):
                    event.acceptProposedAction()
                elif shellwidget is None or not shellwidget.is_running():
                    event.ignore()
                else:
                    event.acceptProposedAction()
            else:
                event.ignore()
        elif source.hasText():
            event.acceptProposedAction()            
            
    def dropEvent(self, event):
        """Reimplement Qt method
        Unpack dropped data and handle it"""
        source = event.mimeData()
        shellwidget = self.tabwidget.currentWidget()
        if source.hasText():
            qstr = source.text()
            if self.__is_python_script(qstr):
                self.start(qstr, ask_for_arguments=True)
            elif shellwidget:
                shellwidget.shell.insert_text(qstr)
        elif source.hasUrls():
            pathlist = mimedata2url(source)
            if all([self.__is_python_script(qstr) for qstr in pathlist]):
                for fname in pathlist:
                    self.start(fname, ask_for_arguments=True)
            elif shellwidget:
                shellwidget.shell.drop_pathlist(pathlist)
        event.acceptProposedAction()
