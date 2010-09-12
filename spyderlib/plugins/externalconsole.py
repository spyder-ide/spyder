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

from PyQt4.QtGui import (QVBoxLayout, QFileDialog, QMessageBox, QInputDialog,
                         QLineEdit, QPushButton, QGroupBox, QLabel, QTabWidget,
                         QFontComboBox)
from PyQt4.QtCore import SIGNAL, QString, Qt

import sys, os
import os.path as osp

# For debugging purpose:
STDOUT = sys.stdout

# Local imports
from spyderlib.config import get_icon, CONF
from spyderlib.utils import programs, remove_trailing_single_backslash
from spyderlib.utils.qthelpers import create_action, mimedata2url
from spyderlib.widgets.tabs import Tabs
from spyderlib.widgets.externalshell.pythonshell import ExternalPythonShell
from spyderlib.widgets.externalshell.systemshell import ExternalSystemShell
from spyderlib.widgets.shellhelpers import get_error_match
from spyderlib.widgets.findreplace import FindReplace
from spyderlib.plugins import SpyderPluginWidget, PluginConfigPage


class ExternalConsoleConfigPage(PluginConfigPage):
    def setup_page(self):
        interface_group = QGroupBox(self.tr("Interface"))
        font_group = self.create_fontgroup(option=None, text=None,
                                    fontfilters=QFontComboBox.MonospacedFonts)
        newcb = self.create_checkbox
        singletab_box = newcb(self.tr("One tab per script"), 'single_tab')
        icontext_box = newcb(self.tr("Show icons and text"), 'show_icontext')

        # Interface Group
        interface_layout = QVBoxLayout()
        interface_layout.addWidget(singletab_box)
        interface_layout.addWidget(icontext_box)
        interface_group.setLayout(interface_layout)
        
        # Source Code Group
        display_group = QGroupBox(self.tr("Source code"))
        buffer_spin = self.create_spinbox(
                            self.tr("Buffer: "), self.tr(" lines"),
                            'max_line_count', min_=100, max_=1000000, step=100,
                            tip=self.tr("Set maximum line count"))
        wrap_mode_box = newcb(self.tr("Wrap lines"), 'wrap')
        
        display_layout = QVBoxLayout()
        display_layout.addWidget(buffer_spin)
        display_layout.addWidget(wrap_mode_box)
        display_group.setLayout(display_layout)
        
        # Background Color Group
        bg_group = QGroupBox(self.tr("Background color"))
        bg_label = QLabel(self.tr("This option will be applied the next time "
                                  "a Python console or a terminal is opened."))
        bg_label.setWordWrap(True)
        lightbg_box = newcb(self.tr("Light background (white color)"),
                            'light_background')
        bg_layout = QVBoxLayout()
        bg_layout.addWidget(bg_label)
        bg_layout.addWidget(lightbg_box)
        bg_group.setLayout(bg_layout)

        # Advanced settings
        source_group = QGroupBox(self.tr("Source code"))
        calltips_box = newcb(self.tr("Balloon tips"), 'calltips')
        completion_box = newcb(self.tr("Automatic code completion"),
                               'codecompletion/auto')
        comp_enter_box = newcb(self.tr("Enter key selects completion"),
                               'codecompletion/enter-key')
        
        source_layout = QVBoxLayout()
        source_layout.addWidget(calltips_box)
        source_layout.addWidget(completion_box)
        source_layout.addWidget(comp_enter_box)
        source_group.setLayout(source_layout)

        # UMD Group
        umd_group = QGroupBox(self.tr("User Module Deleter (UMD)"))
        umd_label = QLabel(self.tr("UMD forces Python to reload modules "
                               "imported when executing a script in the "
                               "external console with the 'runfile' function"))
        umd_label.setWordWrap(True)
        umd_enabled_box = newcb(self.tr("Enable UMD"), 'umd/enabled',
                                msg_if_enabled=True, msg_warning=self.tr(
                        "This option will enable the User Module Deleter (UMD) "
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
                                )
        umd_verbose_box = newcb(self.tr("Show reloaded modules list"),
                                'umd/verbose', msg_info=self.tr(
                                        "Please note that these changes will "
                                        "be applied only to new Python/IPython "
                                        "interpreters"),
                                )
        umd_namelist_btn = QPushButton(
                            self.tr("Set UMD excluded (not reloaded) modules"))
        self.connect(umd_namelist_btn, SIGNAL('clicked()'),
                     self.plugin.set_umd_namelist)
        
        umd_layout = QVBoxLayout()
        umd_layout.addWidget(umd_label)
        umd_layout.addWidget(umd_enabled_box)
        umd_layout.addWidget(umd_verbose_box)
        umd_layout.addWidget(umd_namelist_btn)
        umd_group.setLayout(umd_layout)
        
        # Startup Group
        startup_group = QGroupBox(self.tr("Startup"))
        pystartup_box = newcb(self.tr("Open a Python interpreter at startup"),
                              'open_python_at_startup')
        ipystartup_box = newcb(self.tr("Open an IPython interpreter at startup"),
                               'open_ipython_at_startup')
        ipystartup_box.setEnabled(programs.is_module_installed('IPython'))
        
        startup_layout = QVBoxLayout()
        startup_layout.addWidget(pystartup_box)
        startup_layout.addWidget(ipystartup_box)
        startup_group.setLayout(startup_layout)
        
        # IPython Group
        ipython_group = QGroupBox(self.tr("IPython"))
        ipython_edit = self.create_lineedit(self.tr(
                            "IPython interpreter command line options:\n"
                            "(Qt4 support: -q4thread)\n"
                            "(Qt4 and matplotlib support: -q4thread -pylab)"),
                            'ipython_options', alignment=Qt.Vertical)
        
        ipython_layout = QVBoxLayout()
        ipython_layout.addWidget(ipython_edit)
        ipython_group.setLayout(ipython_layout)
        ipython_group.setEnabled(programs.is_module_installed("IPython"))
        
        # Matplotlib Group
        mpl_group = QGroupBox(self.tr("Matplotlib"))
        mpl_label = QLabel(self.tr("Patching Matplotlib library will add a "
                                   "button to customize figure options "
                                   "(curves/images plot parameters) through a "
                                   "simple dialog box.\n"
                                   "This Spyder feature has been integrated in "
                                   "Matplotlib v1.0 and later versions."))
        mpl_label.setWordWrap(True)
        mpl_patch_box = newcb(self.tr("Patch Matplotlib figures"),
                              'mpl_patch/enabled')
        
        mpl_layout = QVBoxLayout()
        mpl_layout.addWidget(mpl_label)
        mpl_layout.addWidget(mpl_patch_box)
        mpl_group.setLayout(mpl_layout)
        mpl_group.setEnabled(programs.is_module_installed('matplotlib'))
        
        # ETS Group
        ets_group = QGroupBox(self.tr("Enthought Tool Suite"))
        ets_label = QLabel(self.tr("Enthought Tool Suite (ETS) supports "
                                   "PyQt4 (qt4) and wxPython (wx) graphical "
                                   "user interfaces."))
        ets_label.setWordWrap(True)
        ets_edit = self.create_lineedit(self.tr("ETS_TOOLKIT "
                                                "(default value: qt4):"),
                                        'ets_backend', default='qt4',
                                        alignment=Qt.Vertical)
        
        ets_layout = QVBoxLayout()
        ets_layout.addWidget(ets_label)
        ets_layout.addWidget(ets_edit)
        ets_group.setLayout(ets_layout)
        ets_group.setEnabled(programs.is_module_installed(
                                                    "enthought.etsconfig.api"))
        
        tabs = QTabWidget()
        tabs.addTab(self.create_tab(font_group, interface_group, display_group,
                                    bg_group),
                    self.tr("Display"))
        tabs.addTab(self.create_tab(source_group, startup_group, umd_group),
                    self.tr("Advanced settings"))
        tabs.addTab(self.create_tab(ipython_group, mpl_group, ets_group),
                    self.tr("External modules"))
        
        vlayout = QVBoxLayout()
        vlayout.addWidget(tabs)
        self.setLayout(vlayout)


class ExternalConsole(SpyderPluginWidget):
    """
    Console widget
    """
    CONF_SECTION = 'console'
    CONFIGWIDGET_CLASS = ExternalConsoleConfigPage
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

        python_startup = self.get_option('open_python_at_startup', None)
        ipython_startup = self.get_option('open_ipython_at_startup', None)
        if ipython_startup is None:
            ipython_startup = programs.is_module_installed("IPython")
            self.set_option('open_ipython_at_startup', ipython_startup)
        if python_startup is None:
            python_startup = not ipython_startup
            self.set_option('open_python_at_startup', python_startup)
        
        if self.get_option('ipython_options', None) is None:
            self.set_option('ipython_options',
                            self.get_default_ipython_options())
        
        self.shellwidgets = []
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
        self.register_widget_shortcuts("Editor", self.find_widget)
        
        layout.addWidget(self.find_widget)
        
        self.setLayout(layout)
            
        # Accepting drops
        self.setAcceptDrops(True)
        
    def move_tab(self, index_from, index_to):
        """
        Move tab (tabs themselves have already been moved by the tabwidget)
        """
        filename = self.filenames.pop(index_from)
        shell = self.shellwidgets.pop(index_from)
        icons = self.icons.pop(index_from)
        
        self.filenames.insert(index_to, filename)
        self.shellwidgets.insert(index_to, shell)
        self.icons.insert(index_to, icons)

    def close_console(self, index=None):
        if not self.tabwidget.count():
            return
        if index is None:
            index = self.tabwidget.currentIndex()
        self.tabwidget.widget(index).close()
        self.tabwidget.removeTab(index)
        self.filenames.pop(index)
        self.shellwidgets.pop(index)
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
        
    def run_script_in_current_shell(self, filename, wdir, args, debug):
        """Run script in current shell, if any"""
        shellwidget = self.__find_python_shell(interpreter_only=True)
        if shellwidget is not None and shellwidget.is_running():
            line = "%s(r'%s'" % ('debugfile' if debug else 'runfile',
                                 unicode(filename))
            norm = lambda text: remove_trailing_single_backslash(unicode(text))
            if args:
                line += ", args=r'%s'" % norm(args)
            if wdir:
                line += ", wdir=r'%s'" % norm(wdir)
            line += ")"
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
            
    def pdb_has_stopped(self, fname, lineno, shell):
        """Python debugger has just stopped at frame (fname, lineno)"""
        self.emit(SIGNAL("edit_goto(QString,int,QString)"),
                  fname, lineno, '')
        shell.setFocus()
        
    def start(self, fname, wdir=None, args='', interact=False, debug=False,
              python=True, ipython=False, python_args=''):
        """
        Start new console
        
        fname:
          string: filename of script to run
          None: open an interpreter
        wdir: working directory
        args: command line options of the Python script
        interact: inspect script interactively after its execution
        debug: run pdb
        python: True: Python interpreter, False: terminal
        ipython: True: IPython interpreter, False: Python interpreter
        python_args: additionnal Python interpreter command line options
                   (option "-u" is mandatory, see widgets.externalshell package)
        """
        # Note: fname is None <=> Python interpreter
        fname = unicode(fname) if isinstance(fname, QString) else fname
        wdir = unicode(wdir) if isinstance(wdir, QString) else wdir
        
        if fname is not None and fname in self.filenames:
            index = self.filenames.index(fname)
            if self.get_option('single_tab'):
                old_shell = self.shellwidgets[index]
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
        light_background = self.get_option('light_background')
        if python:
            mpl_patch_enabled = self.get_option('mpl_patch/enabled')
            ets_backend = self.get_option('ets_backend', 'qt4')
            umd_enabled = self.get_option('umd/enabled')
            umd_namelist = self.get_option('umd/namelist')
            umd_verbose = self.get_option('umd/verbose')
            ar_timeout = CONF.get('variable_explorer', 'autorefresh/timeout')
            if self.light_mode:
                from spyderlib.plugins.variableexplorer import VariableExplorer
                sa_settings = VariableExplorer.get_settings()
            else:
                sa_settings = None
            shellwidget = ExternalPythonShell(self, fname, wdir, self.commands,
                           interact, debug, path=pythonpath,
                           python_args=python_args, ipython=ipython,
                           arguments=args, stand_alone=sa_settings,
                           umd_enabled=umd_enabled, umd_namelist=umd_namelist,
                           umd_verbose=umd_verbose, ets_backend=ets_backend,
                           mpl_patch_enabled=mpl_patch_enabled,
                           autorefresh_timeout=ar_timeout,
                           light_background=light_background)
            if self.variableexplorer is not None:
                self.variableexplorer.add_shellwidget(shellwidget)
            self.connect(shellwidget, SIGNAL('pdb(QString,int)'),
                         lambda fname, lineno, shell=shellwidget.shell:
                         self.pdb_has_stopped(fname, lineno, shell))
        else:
            shellwidget = ExternalSystemShell(self, wdir, path=pythonpath,
                                              light_background=light_background)
        
        # Code completion / calltips
        case_sensitive = self.get_option('codecompletion/case-sensitivity')
        show_single = self.get_option('codecompletion/select-single')
        from_document = self.get_option('codecompletion/from-document')
        shellwidget.shell.setup_code_completion(case_sensitive, show_single,
                                                 from_document)
        
        shellwidget.shell.setMaximumBlockCount(
                                            self.get_option('max_line_count') )
        shellwidget.shell.set_font( self.get_plugin_font() )
        shellwidget.shell.toggle_wrap_mode( self.get_option('wrap') )
        shellwidget.shell.set_calltips( self.get_option('calltips') )
        shellwidget.shell.set_codecompletion_auto(
                                self.get_option('codecompletion/auto') )
        shellwidget.shell.set_codecompletion_enter(
                                self.get_option('codecompletion/enter-key') )
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
        self.shellwidgets.insert(index, shellwidget)
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
        
        shellwidget.set_icontext_visible(self.get_option('show_icontext'))
        
        # Start process and give focus to console
        shellwidget.start_shell()
        shellwidget.shell.setFocus()
        
    #------ Private API --------------------------------------------------------
    def process_started(self, shell_id):
        for index, shell in enumerate(self.shellwidgets):
            if id(shell) == shell_id:
                icon, _icon = self.icons[index]
                self.tabwidget.setTabIcon(index, icon)
                if self.inspector is not None:
                    self.inspector.set_shell(shell.shell)
                if self.variableexplorer is not None:
                    self.variableexplorer.add_shellwidget(shell)
        
    def process_finished(self, shell_id):
        for index, shell in enumerate(self.shellwidgets):
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
    
    def get_plugin_icon(self):
        """Return widget icon"""
        return get_icon('console.png')
    
    def get_focus_widget(self):
        """
        Return the widget to give focus to when
        this plugin's dockwidget is raised on top-level
        """
        return self.tabwidget.currentWidget()
        
    def get_plugin_actions(self):
        """Return a list of actions related to plugin"""
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
        terminal_action = create_action(self, text, None, 'cmdprompt.png', tip,
                                        triggered=self.open_terminal)
        run_action = create_action(self,
                            self.tr("&Run..."), None,
                            'run_small.png', self.tr("Run a Python script"),
                            triggered=self.run_script)

        run_menu_actions = [interpreter_action]
        tools_menu_actions = [terminal_action]
        self.menu_actions = [interpreter_action, terminal_action, run_action]
        
        ipython_action = create_action(self,
                            self.tr("Open IPython interpreter"), None,
                            'ipython.png',
                            self.tr("Open an IPython interpreter"),
                            triggered=self.open_ipython)
        if programs.is_module_installed("IPython"):
            self.menu_actions.insert(1, ipython_action)
            run_menu_actions.append(ipython_action)
        
        self.main.run_menu_actions += [None]+run_menu_actions
        self.main.tools_menu_actions += tools_menu_actions
        
        return self.menu_actions+run_menu_actions+tools_menu_actions
    
    def register_plugin(self):
        """Register plugin in Spyder's main window"""
        if self.main.light:
            self.main.setCentralWidget(self)
            self.main.widgetlist.append(self)
        else:
            self.main.add_dockwidget(self)
            self.set_inspector(self.main.inspector)
            self.set_historylog(self.main.historylog)
            self.connect(self, SIGNAL("edit_goto(QString,int,QString)"),
                         self.main.editor.load)
            self.connect(self.main.editor,
                         SIGNAL('run_in_current_console(QString,QString,QString,bool)'),
                         self.run_script_in_current_shell)
            self.connect(self.main.editor, SIGNAL("open_dir(QString)"),
                         self.set_current_shell_working_directory)
            self.connect(self.main.workingdirectory,
                         SIGNAL("set_current_console_wd(QString)"),
                         self.set_current_shell_working_directory)
            self.connect(self, SIGNAL('focus_changed()'),
                         self.main.plugin_focus_changed)
            self.connect(self, SIGNAL('redirect_stdio(bool)'),
                         self.main.redirect_internalshell_stdio)
            expl = self.main.explorer
            if expl is not None:
                self.connect(expl, SIGNAL("open_terminal(QString)"),
                             self.open_terminal)
                self.connect(expl, SIGNAL("open_interpreter(QString)"),
                             self.open_interpreter)
                self.connect(expl, SIGNAL("open_ipython(QString)"),
                             self.open_ipython)
            pexpl = self.main.projectexplorer
            if pexpl is not None:
                self.connect(pexpl, SIGNAL("open_terminal(QString)"),
                             self.open_terminal)
                self.connect(pexpl, SIGNAL("open_interpreter(QString)"),
                             self.open_interpreter)
                self.connect(pexpl, SIGNAL("open_ipython(QString)"),
                             self.open_ipython)
        
    def closing_plugin(self, cancelable=False):
        """Perform actions before parent main window is closed"""
        for shellwidget in self.shellwidgets:
            shellwidget.process.kill()
        return True
    
    def refresh_plugin(self):
        """Refresh tabwidget"""
        if self.tabwidget.count():
            editor = self.tabwidget.currentWidget().shell
            editor.setFocus()
        else:
            editor = None
        self.find_widget.set_editor(editor)
    
    def apply_plugin_settings(self, options):
        """Apply configuration file's plugin settings"""
        font = self.get_plugin_font()
        icontext = self.get_option('show_icontext')
        calltips = self.get_option('calltips')
        wrap = self.get_option('wrap')
        compauto = self.get_option('codecompletion/auto')
        compenter = self.get_option('codecompletion/enter-key')
        mlc = self.get_option('max_line_count')
        for shellwidget in self.shellwidgets:
            shellwidget.shell.set_font(font)
            shellwidget.set_icontext_visible(icontext)
            shellwidget.shell.set_calltips(calltips)
            shellwidget.shell.toggle_wrap_mode(wrap)
            shellwidget.shell.set_codecompletion_auto(compauto)
            shellwidget.shell.set_codecompletion_enter(compenter)
            shellwidget.shell.setMaximumBlockCount(mlc)
    
    #------ Public API ---------------------------------------------------------
    def open_interpreter_at_startup(self):
        """Open an interpreter at startup, IPython if module is available"""
        if self.get_option('open_ipython_at_startup') \
           and programs.is_module_installed("IPython"):
            self.open_ipython()
        if self.get_option('open_python_at_startup'):
            self.open_interpreter()
            
    def open_interpreter(self, wdir=None):
        """Open interpreter"""
        if wdir is None:
            wdir = os.getcwdu()
        self.start(fname=None, wdir=unicode(wdir), args='',
                   interact=True, debug=False, python=True)
        
    def get_default_ipython_options(self):
        """Return default ipython command line arguments"""
        default_options = []
        if programs.is_module_installed('matplotlib'):
            default_options.append("-pylab")
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
        args = self.get_option('ipython_options', "")
        self.start(fname=None, wdir=unicode(wdir), args=args,
                   interact=True, debug=False, python=True, ipython=True)
        
    def open_terminal(self, wdir=None):
        """Open terminal"""
        if wdir is None:
            wdir = os.getcwdu()
        self.start(fname=None, wdir=unicode(wdir), args='',
                   interact=True, debug=False, python=False)
        
    def run_script(self):
        """Run a Python script"""
        self.emit(SIGNAL('redirect_stdio(bool)'), False)
        filename = QFileDialog.getOpenFileName(self,
                      self.tr("Run Python script"), os.getcwdu(),
                      self.tr("Python scripts")+" (*.py ; *.pyw ; *.ipy)")
        self.emit(SIGNAL('redirect_stdio(bool)'), True)
        if filename:
            self.start(fname=unicode(filename), wdir=None, args='',
                       interact=False, debug=False)
        
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
            QMessageBox.information(self, self.tr('UMD'),
                                    self.tr("Please note that these changes will "
                                            "be applied only to new Python/IPython "
                                            "interpreters"),
                                    QMessageBox.Ok)
            self.set_option('umd/namelist', fixed_namelist)
        
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
               ( fname.endswith('.py') or fname.endswith('.pyw') \
                 or fname.endswith('.ipy') )
        
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

