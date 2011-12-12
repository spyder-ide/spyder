# -*- coding: utf-8 -*-
#
# Copyright © 2009-2010 Pierre Raybaut
# Licensed under the terms of the MIT License
# (see spyderlib/__init__.py for details)

"""External Console plugin"""

# pylint: disable=C0103
# pylint: disable=R0903
# pylint: disable=R0911
# pylint: disable=R0201

from spyderlib.qt.QtGui import (QVBoxLayout, QMessageBox, QInputDialog,
                                QLineEdit, QPushButton, QGroupBox, QLabel,
                                QTabWidget, QFontComboBox, QHBoxLayout)
from spyderlib.qt.QtCore import SIGNAL, Qt
from spyderlib.qt.compat import getopenfilename

import sys
import os
import os.path as osp
import imp

# For debugging purpose:
STDOUT = sys.stdout

# Local imports
from spyderlib.baseconfig import _, SCIENTIFIC_STARTUP
from spyderlib.config import get_icon, CONF
from spyderlib.utils import programs
from spyderlib.utils.misc import (get_error_match, get_python_executable,
                                  remove_trailing_single_backslash)
from spyderlib.utils.qthelpers import create_action, mimedata2url
from spyderlib.widgets.tabs import Tabs
from spyderlib.widgets.externalshell.pythonshell import ExternalPythonShell
from spyderlib.widgets.externalshell.systemshell import ExternalSystemShell
from spyderlib.widgets.findreplace import FindReplace
from spyderlib.plugins import SpyderPluginWidget, PluginConfigPage


class ExternalConsoleConfigPage(PluginConfigPage):
    def __init__(self, plugin, parent):
        PluginConfigPage.__init__(self, plugin, parent)
        self.get_name = lambda: _("Console")

    def setup_page(self):
        interface_group = QGroupBox(_("Interface"))
        font_group = self.create_fontgroup(option=None, text=None,
                                    fontfilters=QFontComboBox.MonospacedFonts)
        newcb = self.create_checkbox
        singletab_box = newcb(_("One tab per script"), 'single_tab')
        showtime_box = newcb(_("Show elapsed time"), 'show_elapsed_time')
        icontext_box = newcb(_("Show icons and text"), 'show_icontext')

        # Interface Group
        interface_layout = QVBoxLayout()
        interface_layout.addWidget(singletab_box)
        interface_layout.addWidget(showtime_box)
        interface_layout.addWidget(icontext_box)
        interface_group.setLayout(interface_layout)
        
        # Source Code Group
        display_group = QGroupBox(_("Source code"))
        buffer_spin = self.create_spinbox(
                            _("Buffer: "), _(" lines"),
                            'max_line_count', min_=0, max_=1000000, step=100,
                            tip=_("Set maximum line count"))
        wrap_mode_box = newcb(_("Wrap lines"), 'wrap')
        merge_channels_box = newcb(
               _("Merge process standard output/error channels"),
               'merge_output_channels',
               tip=_("Merging the output channels of the process means that\n"
                     "the standard error won't be written in red anymore,\n"
                     "but this has the effect of speeding up display.\n\n"
                     "This option has no effect on IPython."))
        colorize_sys_stderr_box = newcb(
               _("Colorize standard error channel using ANSI escape codes"),
               'colorize_sys_stderr',
               tip=_("This method is the only way to have colorized standard\n"
                     "error channel when the output channels have been "
                     "merged.\n\nThis option has no effect on IPython."))
        self.connect(merge_channels_box, SIGNAL("toggled(bool)"),
                     colorize_sys_stderr_box.setEnabled)
        self.connect(merge_channels_box, SIGNAL("toggled(bool)"),
                     colorize_sys_stderr_box.setChecked)
        colorize_sys_stderr_box.setEnabled(
                                    self.get_option('merge_output_channels'))
        
        display_layout = QVBoxLayout()
        display_layout.addWidget(buffer_spin)
        display_layout.addWidget(wrap_mode_box)
        display_layout.addWidget(merge_channels_box)
        display_layout.addWidget(colorize_sys_stderr_box)
        display_group.setLayout(display_layout)
        
        # Background Color Group
        bg_group = QGroupBox(_("Background color"))
        bg_label = QLabel(_("This option will be applied the next time "
                            "a Python console or a terminal is opened."))
        bg_label.setWordWrap(True)
        lightbg_box = newcb(_("Light background (white color)"),
                            'light_background')
        ipybg_box = newcb(_("Set the appropriate IPython color option"),
                          'ipython_set_color')
        ipython_is_installed = programs.is_module_installed('IPython', '0.1')
        ipybg_box.setEnabled(ipython_is_installed)
        bg_layout = QVBoxLayout()
        bg_layout.addWidget(bg_label)
        bg_layout.addWidget(lightbg_box)
        bg_layout.addWidget(ipybg_box)
        bg_group.setLayout(bg_layout)

        # Advanced settings
        source_group = QGroupBox(_("Source code"))
        completion_box = newcb(_("Automatic code completion"),
                               'codecompletion/auto')
        case_comp_box = newcb(_("Case sensitive code completion"),
                              'codecompletion/case_sensitive')
        show_single_box = newcb(_("Show single completion"),
                               'codecompletion/show_single')
        comp_enter_box = newcb(_("Enter key selects completion"),
                               'codecompletion/enter_key')
        calltips_box = newcb(_("Balloon tips"), 'calltips')
        inspector_box = newcb(
                  _("Automatic notification to object inspector"),
                  'object_inspector', default=True,
                  tip=_("If this option is enabled, object inspector\n"
                        "will automatically show informations on functions\n"
                        "entered in console (this is triggered when entering\n"
                        "a left parenthesis after a valid function name)"))
        
        source_layout = QVBoxLayout()
        source_layout.addWidget(completion_box)
        source_layout.addWidget(case_comp_box)
        source_layout.addWidget(show_single_box)
        source_layout.addWidget(comp_enter_box)
        source_layout.addWidget(calltips_box)
        source_layout.addWidget(inspector_box)
        source_group.setLayout(source_layout)

        # UMD Group
        umd_group = QGroupBox(_("User Module Deleter (UMD)"))
        umd_label = QLabel(_("UMD forces Python to reload modules which were "
                             "imported when executing a \nscript in the "
                             "external console with the 'runfile' function."))
        umd_enabled_box = newcb(_("Enable UMD"), 'umd/enabled',
                                msg_if_enabled=True, msg_warning=_(
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
        umd_verbose_box = newcb(_("Show reloaded modules list"),
                                'umd/verbose', msg_info=_(
                                        "Please note that these changes will "
                                        "be applied only to new Python/IPython "
                                        "interpreters"),
                                )
        umd_namelist_btn = QPushButton(
                            _("Set UMD excluded (not reloaded) modules"))
        self.connect(umd_namelist_btn, SIGNAL('clicked()'),
                     self.plugin.set_umd_namelist)
        
        umd_layout = QVBoxLayout()
        umd_layout.addWidget(umd_label)
        umd_layout.addWidget(umd_enabled_box)
        umd_layout.addWidget(umd_verbose_box)
        umd_layout.addWidget(umd_namelist_btn)
        umd_group.setLayout(umd_layout)
        
        # Python executable Group
        pyexec_group = QGroupBox(_("Python executable"))
        pyexec_label = QLabel(_("Path to Python interpreter "
                                "executable binary:"))
        if os.name == 'nt':
            filters = _("Executables")+" (*.exe)"
        else:
            filters = None
        pyexec_file = self.create_browsefile('', 'pythonexecutable',
                                             filters=filters)
        
        pyexec_layout = QVBoxLayout()
        pyexec_layout.addWidget(pyexec_label)
        pyexec_layout.addWidget(pyexec_file)
        pyexec_group.setLayout(pyexec_layout)
        
        # Startup Group
        startup_group = QGroupBox(_("Startup"))
        pystartup_box = newcb(_("Open a Python interpreter at startup"),
                              'open_python_at_startup')
        ipystartup_box = newcb(_("Open an IPython interpreter at startup"),
                               'open_ipython_at_startup')
        is_ipython_010 = programs.is_module_installed('IPython', '0.10')
        ipystartup_box.setEnabled(is_ipython_010)
        if not is_ipython_010:
            ipystartup_box.setToolTip(
                        _("This option is not available for IPython\n"
                          "versions which are not fully supported\n"
                          "through Spyder's console (i.e. IPython v0.11+)."))
        
        startup_layout = QVBoxLayout()
        startup_layout.addWidget(pystartup_box)
        startup_layout.addWidget(ipystartup_box)
        startup_group.setLayout(startup_layout)
        
        # PYTHONSTARTUP replacement
        pystartup_group = QGroupBox(_("PYTHONSTARTUP replacement"))
        pystartup_label = QLabel(_("This option will override the "
                                   "PYTHONSTARTUP environment variable which\n"
                                   "defines the script to be executed during "
                                   "the Python interpreter startup."))
        default_radio = self.create_radiobutton(
                                        _("Default PYTHONSTARTUP script"),
                                        'pythonstartup/default', True)
        custom_radio = self.create_radiobutton(
                                        _("Use the following startup script:"),
                                        'pythonstartup/custom', False)
        pystartup_file = self.create_browsefile('', 'pythonstartup', '',
                                                filters=_("Python scripts")+\
                                                " (*.py)")
        self.connect(default_radio, SIGNAL("toggled(bool)"),
                     pystartup_file.setDisabled)
        self.connect(custom_radio, SIGNAL("toggled(bool)"),
                     pystartup_file.setEnabled)
        
        pystartup_layout = QVBoxLayout()
        pystartup_layout.addWidget(pystartup_label)
        pystartup_layout.addWidget(default_radio)
        pystartup_layout.addWidget(custom_radio)
        pystartup_layout.addWidget(pystartup_file)
        pystartup_group.setLayout(pystartup_layout)
        
        # Monitor Group
        monitor_group = QGroupBox(_("Monitor"))
        monitor_label = QLabel(_("The monitor provides introspection "
                                 "features to console: code completion, "
                                 "calltips and variable explorer. "
                                 "Because it relies on several modules, "
                                 "disabling the monitor may be useful "
                                 "to accelerate console startup."))
        monitor_label.setWordWrap(True)
        monitor_box = newcb(_("Enable monitor"), 'monitor/enabled')
        for obj in (completion_box, case_comp_box, show_single_box,
                    comp_enter_box, calltips_box):
            self.connect(monitor_box, SIGNAL("toggled(bool)"), obj.setEnabled)
            obj.setEnabled(self.get_option('monitor/enabled'))
        
        monitor_layout = QVBoxLayout()
        monitor_layout.addWidget(monitor_label)
        monitor_layout.addWidget(monitor_box)
        monitor_group.setLayout(monitor_layout)
        
        # Qt Group
        # Do not test if PyQt4 or PySide is installed with the function 
        # spyderlib.utils.programs.is_module_installed because it will 
        # fail (both libraries can't be imported at the same time):
        try:
            imp.find_module('PyQt4')
            has_pyqt4 = True
        except ImportError:
            has_pyqt4 = False
        try:
            imp.find_module('PySide')
            has_pyside = True
        except ImportError:
            has_pyside = False
        opts = []
        if has_pyqt4:
            opts.append( ('PyQt4', 'pyqt') )
        if has_pyside:
            opts.append( ('PySide', 'pyside') )
        qt_group = QGroupBox(_("Qt (PyQt/PySide)"))
        qt_setapi_box = self.create_combobox(
                         _("Qt-Python bindings library selection:"),
                         [(_("Default library"), None)]+opts,
                         'qt/api', default=None, tip=_(
"""This option will act on libraries such as Matplotlib, guidata or ETS"""))
        qt_hook_box = newcb(_("Install Spyder's input hook for Qt"),
                              'qt/install_inputhook',
                              tip=_(
"""PyQt installs an input hook that allows creating and interacting
with Qt widgets in an interactive interpreter without blocking it. 
On Windows platforms, it is strongly recommended to replace it by Spyder's. 
Regarding PySide, note that it does not install an input hook, so it is 
required to enable this feature in order to be able to manipulate PySide/Qt 
objects interactively. Note that this feature requires the monitor to be 
enabled and that it has no effect in IPython."""))
        
        qt_layout = QVBoxLayout()
        qt_layout.addWidget(qt_setapi_box)
        qt_layout.addWidget(qt_hook_box)
        qt_group.setLayout(qt_layout)
        qt_group.setEnabled(has_pyqt4 or has_pyside)
        
        # PyQt Group
        pyqt_group = QGroupBox(_("PyQt"))
        pyqt_setapi_box = self.create_combobox(
                _("API selection for QString and QVariant objects:"),
                ((_("Default API"), 0), (_("API #1"), 1), (_("API #2"), 2)),
                'pyqt/api_version', default=0, tip=_(
"""PyQt API #1 is the default API for Python 2. PyQt API #2 is the default 
API for Python 3 and is compatible with PySide.
Note that switching to API #2 may require to enable the Matplotlib patch."""))
        pyqt_ignore_api_box = newcb(_("Ignore API change errors (sip.setapi)"),
                                    'pyqt/ignore_sip_setapi_errors', tip=_(
"""Enabling this option will ignore errors when changing PyQt API.
As PyQt does not support dynamic API changes, it is strongly recommended
to use this feature wisely, e.g. for debugging purpose.
"""))
        try:
            from sip import setapi #analysis:ignore
        except ImportError:
            pyqt_setapi_box.setDisabled(True)
            pyqt_ignore_api_box.setDisabled(True)
        
        pyqt_layout = QVBoxLayout()
        pyqt_layout.addWidget(pyqt_setapi_box)
        pyqt_layout.addWidget(pyqt_ignore_api_box)
        pyqt_group.setLayout(pyqt_layout)
        if has_pyqt4:
            qt_layout.addWidget(pyqt_group)
        
        # IPython Group
        ipython_group = QGroupBox(
                            _("IPython interpreter command line options"))
        ipython_layout = QVBoxLayout()
        if ipython_is_installed:
            if programs.is_module_installed('IPython', '0.12'):
                ipython_edit_012 = self.create_lineedit("IPython >=v0.12",
                             'ipython_kernel_options', alignment=Qt.Horizontal)
                ipython_layout.addWidget(ipython_edit_012)
            else:
                ipython_edit_010 = self.create_lineedit("IPython v0.10",
                                    'ipython_options', alignment=Qt.Horizontal)
                ipython_layout.addWidget(ipython_edit_010)
        else:
            ipython_label = QLabel(_("<b>Note:</b><br>"
                                     "IPython >=<u>v0.10</u> is not "
                                     "installed on this computer."))
            ipython_label.setWordWrap(True)
            ipython_layout.addWidget(ipython_label)
        ipython_group.setLayout(ipython_layout)
        ipython_group.setEnabled(ipython_is_installed)
        
        # Matplotlib Group
        mpl_group = QGroupBox(_("Matplotlib"))
        mpl_backend_box = newcb('', 'matplotlib/backend/enabled', True)
        mpl_backend_edit = self.create_lineedit(_("GUI backend:"),
                                'matplotlib/backend/value', "Qt4Agg",
                                _("Set the GUI toolkit used by Matplotlib to "
                                  "show figures (default: Qt4Agg)"),
                                alignment=Qt.Horizontal)
        self.connect(mpl_backend_box, SIGNAL("toggled(bool)"),
                     mpl_backend_edit.setEnabled)
        mpl_backend_layout = QHBoxLayout()
        mpl_backend_layout.addWidget(mpl_backend_box)
        mpl_backend_layout.addWidget(mpl_backend_edit)
        mpl_backend_edit.setEnabled(
                                self.get_option('matplotlib/backend/enabled'))
        mpl_patch_box = newcb(_("Patch Matplotlib figures"),
                              'matplotlib/patch', False)
        mpl_patch_label = QLabel(_("Patching Matplotlib library will add a "
                                   "button to customize figure options "
                                   "(Qt4Agg only) and fix some issues."))
        mpl_patch_label.setWordWrap(True)
        self.connect(mpl_patch_box, SIGNAL("toggled(bool)"),
                     mpl_patch_label.setEnabled)
        
        mpl_installed = programs.is_module_installed('matplotlib')
        if mpl_installed:
            from spyderlib import mpl_patch
            if not mpl_patch.is_available():
                mpl_patch_box.hide()
                mpl_patch_label.hide()
        
        mpl_layout = QVBoxLayout()
        mpl_layout.addLayout(mpl_backend_layout)
        mpl_layout.addWidget(mpl_patch_box)
        mpl_layout.addWidget(mpl_patch_label)
        mpl_group.setLayout(mpl_layout)
        mpl_group.setEnabled(mpl_installed)
        
        # ETS Group
        ets_group = QGroupBox(_("Enthought Tool Suite"))
        ets_label = QLabel(_("Enthought Tool Suite (ETS) supports "
                             "PyQt4 (qt4) and wxPython (wx) graphical "
                             "user interfaces."))
        ets_label.setWordWrap(True)
        ets_edit = self.create_lineedit(_("ETS_TOOLKIT:"), 'ets_backend',
                                        default='qt4', alignment=Qt.Horizontal)
        
        ets_layout = QVBoxLayout()
        ets_layout.addWidget(ets_label)
        ets_layout.addWidget(ets_edit)
        ets_group.setLayout(ets_layout)
        ets_group.setEnabled(programs.is_module_installed(
                                                    "enthought.etsconfig.api"))
        
        tabs = QTabWidget()
        tabs.addTab(self.create_tab(font_group, interface_group, display_group,
                                    bg_group),
                    _("Display"))
        tabs.addTab(self.create_tab(monitor_group, source_group),
                    _("Introspection"))
        tabs.addTab(self.create_tab(pyexec_group, startup_group,
                                    pystartup_group, umd_group),
                    _("Advanced settings"))
        tabs.addTab(self.create_tab(qt_group, ipython_group,
                                    mpl_group, ets_group),
                    _("External modules"))
        
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
        SpyderPluginWidget.__init__(self, parent)
        self.light_mode = light_mode
        self.commands = []
        self.tabwidget = None
        self.menu_actions = None
        
        self.inspector = None # Object inspector plugin
        self.historylog = None # History log plugin
        self.variableexplorer = None # Variable explorer plugin
        
        self.ipython_shell_count = 0
        self.ipython_kernel_count = 0
        self.python_count = 0
        self.terminal_count = 0

        try:
            from sip import setapi #analysis:ignore
        except ImportError:
            self.set_option('pyqt/ignore_sip_setapi_errors', False)

        scientific = programs.is_module_installed('numpy') and\
                     programs.is_module_installed('scipy') and\
                     programs.is_module_installed('matplotlib')
        if self.get_option('pythonstartup/default', None) is None:
            self.set_option('pythonstartup/default', not scientific)
        if not osp.isfile(self.get_option('pythonstartup', '')):
            self.set_option('pythonstartup', SCIENTIFIC_STARTUP)
            self.set_option('pythonstartup/default', not scientific)
        # default/custom settings are mutually exclusive:
        self.set_option('pythonstartup/custom',
                        not self.get_option('pythonstartup/default'))
        
        if self.get_option('ipython_options', None) is None:
            self.set_option('ipython_options',
                            self.get_default_ipython_options())
        if self.get_option('ipython_kernel_options', None) is None:
            self.set_option('ipython_kernel_options',
                            self.get_default_ipython_kernel_options())
        
        executable = self.get_option('pythonexecutable',
                                     get_python_executable())
        if not osp.isfile(executable):
            # This is absolutely necessary, in case the Python interpreter
            # executable has been moved since last Spyder execution (following
            # a Python distribution upgrade for example)
            self.set_option('pythonexecutable', get_python_executable())
        elif executable.endswith('pythonw.exe'):
            # That should not be necessary because this case is already taken
            # care of by the `get_python_executable` function but, this was
            # implemented too late, so we have to fix it here too, in case
            # the Python executable has already been set with pythonw.exe:
            self.set_option('pythonexecutable',
                            executable.replace("pythonw.exe", "python.exe"))
        
        self.shellwidgets = []
        self.filenames = []
        self.icons = []
        self.runfile_args = ""
        
        # Initialize plugin
        self.initialize_plugin()
        
        layout = QVBoxLayout()
        self.tabwidget = Tabs(self, self.menu_actions)
        if hasattr(self.tabwidget, 'setDocumentMode')\
           and not sys.platform == 'darwin':
            self.tabwidget.setDocumentMode(True)
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
        self.emit(SIGNAL('update_plugin_title()'))

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
        self.emit(SIGNAL('update_plugin_title()'))
        
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
                if not interpreter_only or shellwidget.is_interpreter:
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
                if shellwidget.is_interpreter:
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
              python=True, ipython_shell=False, ipython_kernel=False,
              python_args=''):
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
        if fname is not None and not isinstance(fname, basestring):
            fname = unicode(fname)
        if wdir is not None and not isinstance(wdir, basestring):
            wdir = unicode(wdir)
        
        if fname is not None and fname in self.filenames:
            index = self.filenames.index(fname)
            if self.get_option('single_tab'):
                old_shell = self.shellwidgets[index]
                if old_shell.is_running():
                    answer = QMessageBox.question(self, self.get_plugin_title(),
                        _("%s is already running in a separate process.\n"
                          "Do you want to kill the process before starting "
                          "a new one?") % osp.basename(fname),
                        QMessageBox.Yes | QMessageBox.Cancel)
                    if answer == QMessageBox.Yes:
                        old_shell.process.kill()
                        old_shell.process.waitForFinished()
                    else:
                        return
                self.close_console(index)
        else:
            index = self.tabwidget.count()

        # Creating a new external shell
        pythonpath = self.main.get_spyder_pythonpath()
        light_background = self.get_option('light_background')
        show_elapsed_time = self.get_option('show_elapsed_time')
        if python:
            pythonexecutable = self.get_option('pythonexecutable')
            if self.get_option('pythonstartup/default', True):
                pythonstartup = None
            else:
                pythonstartup = self.get_option('pythonstartup', None)
            monitor_enabled = self.get_option('monitor/enabled')
            mpl_patch_enabled = self.get_option('matplotlib/patch')
            if self.get_option('matplotlib/backend/enabled'):
                mpl_backend = self.get_option('matplotlib/backend/value')
            else:
                mpl_backend = None
            ets_backend = self.get_option('ets_backend', 'qt4')
            qt_api = self.get_option('qt/api')
            install_qt_inputhook = self.get_option('qt/install_inputhook')
            pyqt_api = self.get_option('pyqt/api_version', 0)
            ignore_sip_setapi_errors = self.get_option(
                                            'pyqt/ignore_sip_setapi_errors')
            merge_output_channels = self.get_option('merge_output_channels')
            colorize_sys_stderr = self.get_option('colorize_sys_stderr')
            umd_enabled = self.get_option('umd/enabled')
            umd_namelist = self.get_option('umd/namelist')
            umd_verbose = self.get_option('umd/verbose')
            ar_timeout = CONF.get('variable_explorer', 'autorefresh/timeout')
            ar_state = CONF.get('variable_explorer', 'autorefresh')
            if self.light_mode:
                from spyderlib.plugins.variableexplorer import VariableExplorer
                sa_settings = VariableExplorer.get_settings()
            else:
                sa_settings = None
            shellwidget = ExternalPythonShell(self, fname, wdir, self.commands,
                           interact, debug, path=pythonpath,
                           python_args=python_args,
                           ipython_shell=ipython_shell,
                           ipython_kernel=ipython_kernel,
                           arguments=args, stand_alone=sa_settings,
                           pythonstartup=pythonstartup,
                           pythonexecutable=pythonexecutable,
                           umd_enabled=umd_enabled, umd_namelist=umd_namelist,
                           umd_verbose=umd_verbose, ets_backend=ets_backend,
                           monitor_enabled=monitor_enabled,
                           mpl_patch_enabled=mpl_patch_enabled,
                           mpl_backend=mpl_backend,
                           qt_api=qt_api, pyqt_api=pyqt_api,
                           install_qt_inputhook=install_qt_inputhook,
                           ignore_sip_setapi_errors=ignore_sip_setapi_errors,
                           merge_output_channels=merge_output_channels,
                           colorize_sys_stderr=colorize_sys_stderr,
                           autorefresh_timeout=ar_timeout,
                           autorefresh_state=ar_state,
                           light_background=light_background,
                           menu_actions=self.menu_actions,
                           show_buttons_inside=False,
                           show_elapsed_time=show_elapsed_time)
            self.connect(shellwidget, SIGNAL('pdb(QString,int)'),
                         lambda fname, lineno, shell=shellwidget.shell:
                         self.pdb_has_stopped(fname, lineno, shell))
            self.register_widget_shortcuts("Console", shellwidget.shell)
        else:
            if os.name == 'posix':
                cmd = 'gnome-terminal'
                args = []
                if programs.is_program_installed(cmd):
                    if wdir:
                        args.extend(['--working-directory=%s' % wdir])
                    programs.run_program(cmd, args)
                    return
                cmd = 'konsole'
                if programs.is_program_installed(cmd):
                    if wdir:
                        args.extend(['--workdir', wdir])
                    programs.run_program(cmd, args)
                    return
            shellwidget = ExternalSystemShell(self, wdir, path=pythonpath,
                                          light_background=light_background,
                                          menu_actions=self.menu_actions,
                                          show_buttons_inside=False,
                                          show_elapsed_time=show_elapsed_time)
        
        # Code completion / calltips
        shellwidget.shell.setMaximumBlockCount(
                                            self.get_option('max_line_count') )
        shellwidget.shell.set_font( self.get_plugin_font() )
        shellwidget.shell.toggle_wrap_mode( self.get_option('wrap') )
        shellwidget.shell.set_calltips( self.get_option('calltips') )
        shellwidget.shell.set_codecompletion_auto(
                            self.get_option('codecompletion/auto') )
        shellwidget.shell.set_codecompletion_case(
                            self.get_option('codecompletion/case_sensitive') )
        shellwidget.shell.set_codecompletion_single(
                            self.get_option('codecompletion/show_single') )
        shellwidget.shell.set_codecompletion_enter(
                            self.get_option('codecompletion/enter_key') )
        if python and self.inspector is not None:
            shellwidget.shell.set_inspector(self.inspector)
            shellwidget.shell.set_inspector_enabled(
                                            self.get_option('object_inspector'))
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
            if self.main.editor is not None:
                self.connect(shellwidget, SIGNAL('open_file(QString,int)'),
                             self.open_file_in_spyder)
            if fname is None:
                if ipython_shell:
                    self.ipython_shell_count += 1
                    tab_name = "IPython %d" % self.ipython_shell_count
                    tab_icon1 = get_icon('ipython.png')
                    tab_icon2 = get_icon('ipython_t.png')
                elif ipython_kernel:
                    self.ipython_kernel_count += 1
                    tab_name = "IPyKernel %d" % self.ipython_kernel_count
                    tab_icon1 = get_icon('ipython.png')
                    tab_icon2 = get_icon('ipython_t.png')
                    kernel_name = "IPK%d" % self.ipython_kernel_count
                    self.connect(shellwidget,
                                 SIGNAL('create_ipython_frontend(QString)'),
                                 lambda args:
                                 self.main.new_ipython_frontend(
                                 args, kernel_widget=shellwidget,
                                 kernel_name=kernel_name))
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
                tab_name = _("Command Window")
            else:
                tab_name = _("Terminal")
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
        
    def open_file_in_spyder(self, fname, lineno):
        """Open file in Spyder's editor from remote process"""
        self.main.editor.activateWindow()
        self.main.editor.raise_()
        self.main.editor.load(fname, lineno)
        
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
        title = _('Console')
        if self.filenames:
            index = self.tabwidget.currentIndex()
            fname = self.filenames[index]
            if fname:
                title += ' - '+unicode(fname)
        return title
    
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
                            _("Open &interpreter"), None,
                            'python.png', _("Open a Python interpreter"),
                            triggered=self.open_interpreter)
        if os.name == 'nt':
            text = _("Open &command prompt")
            tip = _("Open a Windows command prompt")
        else:
            text = _("Open &terminal")
            tip = _("Open a terminal window inside Spyder")
        terminal_action = create_action(self, text, None, 'cmdprompt.png', tip,
                                        triggered=self.open_terminal)
        run_action = create_action(self,
                            _("&Run..."), None,
                            'run_small.png', _("Run a Python script"),
                            triggered=self.run_script)

        interact_menu_actions = [interpreter_action]
        tools_menu_actions = [terminal_action]
        self.menu_actions = [interpreter_action, terminal_action, run_action]
        
        ipython_kernel_action = create_action(self,
                            _("Start a new IPython kernel"), None,
                            'ipython.png', triggered=self.start_ipython_kernel)
        if programs.is_module_installed('IPython', '0.12'):
            self.menu_actions.insert(1, ipython_kernel_action)
            interact_menu_actions.append(ipython_kernel_action)
        
        ipython_action = create_action(self,
                            _("Open IPython interpreter"), None,
                            'ipython.png',
                            _("Open an IPython interpreter"),
                            triggered=self.open_ipython)
        if programs.is_module_installed('IPython', '0.1'):
            self.menu_actions.insert(1, ipython_action)
            interact_menu_actions.append(ipython_action)
        
        self.main.interact_menu_actions += interact_menu_actions
        self.main.tools_menu_actions += tools_menu_actions
        
        return self.menu_actions+interact_menu_actions+tools_menu_actions
    
    def register_plugin(self):
        """Register plugin in Spyder's main window"""
        if self.main.light:
            self.main.setCentralWidget(self)
            self.main.widgetlist.append(self)
        else:
            self.main.add_dockwidget(self)
            self.inspector = self.main.inspector
            if self.inspector is not None:
                self.inspector.set_external_console(self)
            self.historylog = self.main.historylog
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
            shellwidget.close()
        return True
    
    def refresh_plugin(self):
        """Refresh tabwidget"""
        shellwidget = None
        if self.tabwidget.count():
            shellwidget = self.tabwidget.currentWidget()
            editor = shellwidget.shell
            editor.setFocus()
            widgets = [shellwidget.create_time_label(), 5
                       ]+shellwidget.get_toolbar_buttons()+[5]
        else:
            editor = None
            widgets = []
        self.find_widget.set_editor(editor)
        self.tabwidget.set_corner_widgets({Qt.TopRightCorner: widgets})
        if shellwidget:
            shellwidget.update_time_label_visibility()
        self.emit(SIGNAL('update_plugin_title()'))
    
    def apply_plugin_settings(self, options):
        """Apply configuration file's plugin settings"""
        whitebg_n = 'light_background'
        ipybg_n = 'ipython_set_color'
        if (whitebg_n in options or ipybg_n in options) \
           and self.get_option(ipybg_n):
            ipython_n = 'ipython_options'
            args = self.get_option(ipython_n, "")
            if args:
                lbgo = "-colors LightBG"
                if self.get_option(whitebg_n):
                    # White background
                    if lbgo not in args:
                        self.set_option(ipython_n, args+" "+lbgo)
                else:
                    # Black background
                    self.set_option(ipython_n, args.replace(" "+lbgo, ""
                                    ).replace(lbgo+" ", "").replace(lbgo, ""))
            else:
                lbgo = "-colors LightBG"
                if self.get_option(whitebg_n):
                    self.set_option(ipython_n, lbgo)
        
        font = self.get_plugin_font()
        showtime = self.get_option('show_elapsed_time')
        icontext = self.get_option('show_icontext')
        calltips = self.get_option('calltips')
        inspector = self.get_option('object_inspector')
        wrap = self.get_option('wrap')
        compauto = self.get_option('codecompletion/auto')
        case_comp = self.get_option('codecompletion/case_sensitive')
        show_single = self.get_option('codecompletion/show_single')
        compenter = self.get_option('codecompletion/enter_key')
        mlc = self.get_option('max_line_count')
        for shellwidget in self.shellwidgets:
            shellwidget.shell.set_font(font)
            shellwidget.set_elapsed_time_visible(showtime)
            shellwidget.set_icontext_visible(icontext)
            shellwidget.shell.set_calltips(calltips)
            if isinstance(shellwidget.shell, ExternalPythonShell):
                shellwidget.shell.set_inspector_enabled(inspector)
            shellwidget.shell.toggle_wrap_mode(wrap)
            shellwidget.shell.set_codecompletion_auto(compauto)
            shellwidget.shell.set_codecompletion_case(case_comp)
            shellwidget.shell.set_codecompletion_single(show_single)
            shellwidget.shell.set_codecompletion_enter(compenter)
            shellwidget.shell.setMaximumBlockCount(mlc)
    
    #------ Public API ---------------------------------------------------------
    def open_interpreter_at_startup(self):
        """Open an interpreter at startup, IPython if module is available"""
        if self.get_option('open_ipython_at_startup', False):
            if programs.is_module_installed('IPython', '0.10'):
                # IPython v0.10.x is fully supported by Spyder, not v0.11+
                self.open_ipython()
            else:
                # If IPython v0.11+ is installed (or if IPython is not
                # installed at all), we must -at least the first time- force
                # the user to start with the standard Python interpreter which
                # has been enhanced to support most of the IPython features
                # needed within an advanced IDE as Spyder:
                # http://spyder-ide.blogspot.com/2011/09/new-enhanced-scientific-python.html
                # The main motivation here is to be sure that the novice user
                # will have an experience as close as possible to MATLAB with
                # a ready-to-use interpreter with standard scientific modules
                # preloaded and with non-blocking interactive plotting.
                self.set_option('open_ipython_at_startup', False)
                self.set_option('open_python_at_startup', True)
        if self.get_option('open_python_at_startup', True):
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
            path = programs.find_program(editor_name)
            if path is not None:
                default_options.append("-editor "+osp.basename(path))
                break
        return " ".join(default_options)
        
    def get_default_ipython_kernel_options(self):
        """Return default ipython kernel command line arguments"""
        default_options = ["python"]
        if programs.is_module_installed('matplotlib'):
            default_options.append("--pylab=inline")
        return " ".join(default_options)
        
    def open_ipython(self, wdir=None):
        """Open IPython"""
        if wdir is None:
            wdir = os.getcwdu()
        args = self.get_option('ipython_options', "")
        self.start(fname=None, wdir=unicode(wdir), args=args,
                   interact=True, debug=False, python=True, ipython_shell=True)

    def start_ipython_kernel(self, wdir=None):
        """Start new IPython kernel"""
        if wdir is None:
            wdir = os.getcwdu()
        args = self.get_option('ipython_kernel_options',
                               "python --pylab=inline")
        self.start(fname=None, wdir=unicode(wdir), args=args,
                   interact=True, debug=False, python=True,
                   ipython_kernel=True)

    def open_terminal(self, wdir=None):
        """Open terminal"""
        if wdir is None:
            wdir = os.getcwdu()
        self.start(fname=None, wdir=unicode(wdir), args='',
                   interact=True, debug=False, python=False)
        
    def run_script(self):
        """Run a Python script"""
        self.emit(SIGNAL('redirect_stdio(bool)'), False)
        filename, _selfilter = getopenfilename(self, _("Run Python script"),
                os.getcwdu(), _("Python scripts")+" (*.py ; *.pyw ; *.ipy)")
        self.emit(SIGNAL('redirect_stdio(bool)'), True)
        if filename:
            self.start(fname=filename, wdir=None, args='',
                       interact=False, debug=False)
        
    def set_umd_namelist(self):
        """Set UMD excluded modules name list"""
        arguments, valid = QInputDialog.getText(self, _('UMD'),
                                  _('UMD excluded modules:\n'
                                          '(example: guidata, guiqwt)'),
                                  QLineEdit.Normal,
                                  ", ".join(self.get_option('umd/namelist')))
        if valid:
            arguments = unicode(arguments)
            if arguments:
                namelist = arguments.replace(' ', '').split(',')
                fixed_namelist = [module_name for module_name in namelist
                                  if programs.is_module_installed(module_name)]
                invalid = ", ".join(set(namelist)-set(fixed_namelist))
                if invalid:
                    QMessageBox.warning(self, _('UMD'),
                                        _("The following modules are not "
                                          "installed on your machine:\n%s"
                                          ) % invalid, QMessageBox.Ok)
                QMessageBox.information(self, _('UMD'),
                                    _("Please note that these changes will "
                                      "be applied only to new Python/IPython "
                                      "interpreters"), QMessageBox.Ok)
            else:
                fixed_namelist = []
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
                self.start(qstr)
            elif shellwidget:
                shellwidget.shell.insert_text(qstr)
        elif source.hasUrls():
            pathlist = mimedata2url(source)
            if all([self.__is_python_script(qstr) for qstr in pathlist]):
                for fname in pathlist:
                    self.start(fname)
            elif shellwidget:
                shellwidget.shell.drop_pathlist(pathlist)
        event.acceptProposedAction()

