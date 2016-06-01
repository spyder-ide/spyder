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

# Standard library imports
import atexit
import os
import os.path as osp
import sys

# Third party imports
from qtpy import PYQT5
from qtpy.compat import getopenfilename
from qtpy.QtCore import Qt, Signal, Slot
from qtpy.QtWidgets import (QButtonGroup, QGroupBox, QHBoxLayout, QInputDialog,
                            QLabel, QLineEdit, QMessageBox, QPushButton,
                            QTabWidget, QVBoxLayout, QWidget)

# Local imports
from spyderlib import dependencies
from spyderlib.config.base import _, running_in_mac_app, SCIENTIFIC_STARTUP
from spyderlib.config.main import CONF
from spyderlib.utils import encoding, programs
from spyderlib.utils import icon_manager as ima
from spyderlib.utils.misc import (get_error_match, get_python_executable,
                                  is_python_script, remove_backslashes)
from spyderlib.utils.qthelpers import create_action, mimedata2url
from spyderlib.plugins import PluginConfigPage, SpyderPluginWidget
from spyderlib.plugins.runconfig import get_run_configuration
from spyderlib.py3compat import to_text_string, is_text_string, getcwd
from spyderlib.widgets.externalshell.pythonshell import ExternalPythonShell
from spyderlib.widgets.externalshell.systemshell import ExternalSystemShell
from spyderlib.widgets.findreplace import FindReplace
from spyderlib.widgets.tabs import Tabs


MPL_REQVER = '>=1.0'
dependencies.add("matplotlib", _("Interactive data plotting in the consoles"),
                 required_version=MPL_REQVER, optional=True)


class ExternalConsoleConfigPage(PluginConfigPage):

    def __init__(self, plugin, parent):
        PluginConfigPage.__init__(self, plugin, parent)
        self.get_name = lambda: _("Console")
        self.cus_exec_radio = None
        self.pyexec_edit = None

    def initialize(self):
        PluginConfigPage.initialize(self)
        self.pyexec_edit.textChanged.connect(self.python_executable_changed)
        self.cus_exec_radio.toggled.connect(self.python_executable_switched)

    def setup_page(self):
        interface_group = QGroupBox(_("Interface"))
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
                     "but this has the effect of speeding up display."))
        colorize_sys_stderr_box = newcb(
               _("Colorize standard error channel using ANSI escape codes"),
               'colorize_sys_stderr',
               tip=_("This method is the only way to have colorized standard\n"
                     "error channel when the output channels have been "
                     "merged."))
        merge_channels_box.toggled.connect(colorize_sys_stderr_box.setEnabled)
        merge_channels_box.toggled.connect(colorize_sys_stderr_box.setChecked)
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
        bg_layout = QVBoxLayout()
        bg_layout.addWidget(bg_label)
        bg_layout.addWidget(lightbg_box)
        bg_group.setLayout(bg_layout)

        # Advanced settings
        source_group = QGroupBox(_("Source code"))
        completion_box = newcb(_("Automatic code completion"),
                               'codecompletion/auto')
        case_comp_box = newcb(_("Case sensitive code completion"),
                              'codecompletion/case_sensitive')
        comp_enter_box = newcb(_("Enter key selects completion"),
                               'codecompletion/enter_key')
        calltips_box = newcb(_("Display balloon tips"), 'calltips')
        
        source_layout = QVBoxLayout()
        source_layout.addWidget(completion_box)
        source_layout.addWidget(case_comp_box)
        source_layout.addWidget(comp_enter_box)
        source_layout.addWidget(calltips_box)
        source_group.setLayout(source_layout)

        # UMR Group
        umr_group = QGroupBox(_("User Module Reloader (UMR)"))
        umr_label = QLabel(_("UMR forces Python to reload modules which were "
                             "imported when executing a \nscript in the "
                             "external console with the 'runfile' function."))
        umr_enabled_box = newcb(_("Enable UMR"), 'umr/enabled',
                                msg_if_enabled=True, msg_warning=_(
                        "This option will enable the User Module Reloader (UMR) "
                        "in Python/IPython consoles. UMR forces Python to "
                        "reload deeply modules during import when running a "
                        "Python script using the Spyder's builtin function "
                        "<b>runfile</b>."
                        "<br><br><b>1.</b> UMR may require to restart the "
                        "console in which it will be called "
                        "(otherwise only newly imported modules will be "
                        "reloaded when executing scripts)."
                        "<br><br><b>2.</b> If errors occur when re-running a "
                        "PyQt-based program, please check that the Qt objects "
                        "are properly destroyed (e.g. you may have to use the "
                        "attribute <b>Qt.WA_DeleteOnClose</b> on your main "
                        "window, using the <b>setAttribute</b> method)"),
                                )
        umr_verbose_box = newcb(_("Show reloaded modules list"),
                                'umr/verbose', msg_info=_(
                                "Please note that these changes will "
                                "be applied only to new consoles"))
        umr_namelist_btn = QPushButton(
                            _("Set UMR excluded (not reloaded) modules"))
        umr_namelist_btn.clicked.connect(self.plugin.set_umr_namelist)
        
        umr_layout = QVBoxLayout()
        umr_layout.addWidget(umr_label)
        umr_layout.addWidget(umr_enabled_box)
        umr_layout.addWidget(umr_verbose_box)
        umr_layout.addWidget(umr_namelist_btn)
        umr_group.setLayout(umr_layout)
        
        # Python executable Group
        pyexec_group = QGroupBox(_("Python executable"))
        pyexec_bg = QButtonGroup(pyexec_group)
        pyexec_label = QLabel(_("Select the Python interpreter executable "
                                "binary in which Spyder will run scripts:"))
        def_exec_radio = self.create_radiobutton(
                                _("Default (i.e. the same as Spyder's)"),
                                'pythonexecutable/default', 
                                button_group=pyexec_bg)
        self.cus_exec_radio = self.create_radiobutton(
                                _("Use the following Python interpreter:"),
                                'pythonexecutable/custom',
                                button_group=pyexec_bg)
        if os.name == 'nt':
            filters = _("Executables")+" (*.exe)"
        else:
            filters = None
        pyexec_file = self.create_browsefile('', 'pythonexecutable',
                                             filters=filters)
        for le in self.lineedits:
            if self.lineedits[le][0] == 'pythonexecutable':
                self.pyexec_edit = le
        def_exec_radio.toggled.connect(pyexec_file.setDisabled)
        self.cus_exec_radio.toggled.connect(pyexec_file.setEnabled)
        pyexec_layout = QVBoxLayout()
        pyexec_layout.addWidget(pyexec_label)
        pyexec_layout.addWidget(def_exec_radio)
        pyexec_layout.addWidget(self.cus_exec_radio)
        pyexec_layout.addWidget(pyexec_file)
        pyexec_group.setLayout(pyexec_layout)
        
        # PYTHONSTARTUP replacement
        pystartup_group = QGroupBox(_("PYTHONSTARTUP replacement"))
        pystartup_bg = QButtonGroup(pystartup_group)
        pystartup_label = QLabel(_("This option will override the "
                                   "PYTHONSTARTUP environment variable which\n"
                                   "defines the script to be executed during "
                                   "the Python console startup."))
        def_startup_radio = self.create_radiobutton(
                                        _("Default PYTHONSTARTUP script"),
                                        'pythonstartup/default',
                                        button_group=pystartup_bg)
        cus_startup_radio = self.create_radiobutton(
                                        _("Use the following startup script:"),
                                        'pythonstartup/custom',
                                        button_group=pystartup_bg)
        pystartup_file = self.create_browsefile('', 'pythonstartup', '',
                                                filters=_("Python scripts")+\
                                                " (*.py)")
        def_startup_radio.toggled.connect(pystartup_file.setDisabled)
        cus_startup_radio.toggled.connect(pystartup_file.setEnabled)
        
        pystartup_layout = QVBoxLayout()
        pystartup_layout.addWidget(pystartup_label)
        pystartup_layout.addWidget(def_startup_radio)
        pystartup_layout.addWidget(cus_startup_radio)
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
        for obj in (completion_box, case_comp_box, comp_enter_box,
                    calltips_box):
            monitor_box.toggled.connect(obj.setEnabled)
            obj.setEnabled(self.get_option('monitor/enabled'))
        
        monitor_layout = QVBoxLayout()
        monitor_layout.addWidget(monitor_label)
        monitor_layout.addWidget(monitor_box)
        monitor_group.setLayout(monitor_layout)
        
        # Qt Group
        opts = [
            (_("Default library"), 'default'),
            ('PyQt5', 'pyqt5'),
            ('PyQt4', 'pyqt'),
            ('PySide', 'pyside'),
        ]
        qt_group = QGroupBox(_("Qt-Python Bindings"))
        qt_setapi_box = self.create_combobox(
                         _("Library:") + "   ", opts,
                         'qt/api', default='default',
                         tip=_("This option will act on<br> "
                               "libraries such as Matplotlib, guidata "
                               "or ETS"))

        qt_layout = QVBoxLayout()
        qt_layout.addWidget(qt_setapi_box)
        qt_group.setLayout(qt_layout)

        # Matplotlib Group
        mpl_group = QGroupBox(_("Graphics"))
        mpl_label = QLabel(_("Decide which backend to use to display graphics. "
                              "If unsure, please select the <b>Automatic</b> "
                              "backend.<br><br>"
                              "<b>Note:</b> We support a very limited number "
                              "of backends in our Python consoles. If you "
                              "prefer to work with a different one, please use "
                              "an IPython console."))
        mpl_label.setWordWrap(True)

        backends = [("Automatic", 0), ("None", 1)]
        if not os.name == 'nt' and programs.is_module_installed('_tkinter'):
            backends.append( ("Tkinter", 2) )
        backends = tuple(backends)

        mpl_backend_box = self.create_combobox( _("Backend:")+"   ", backends,
                                       'matplotlib/backend/value',
                                       tip=_("This option will be applied the "
                                             "next time a console is opened."))

        mpl_installed = programs.is_module_installed('matplotlib')
        mpl_layout = QVBoxLayout()
        mpl_layout.addWidget(mpl_label)
        mpl_layout.addWidget(mpl_backend_box)
        mpl_group.setLayout(mpl_layout)
        mpl_group.setEnabled(mpl_installed)

        # ETS Group
        ets_group = QGroupBox(_("Enthought Tool Suite"))
        ets_label = QLabel(_("Enthought Tool Suite (ETS) supports "
                             "PyQt4 (qt4) and wxPython (wx) graphical "
                             "user interfaces."))
        ets_label.setWordWrap(True)
        ets_edit = self.create_lineedit(_("ETS_TOOLKIT:"), 'ets_backend',
                                        alignment=Qt.Horizontal)

        ets_layout = QVBoxLayout()
        ets_layout.addWidget(ets_label)
        ets_layout.addWidget(ets_edit)
        ets_group.setLayout(ets_layout)

        if self.get_option('pythonexecutable/default'):
            interpreter = get_python_executable()
        else:
            interpreter = self.get_option('pythonexecutable')
        ets_group.setEnabled(programs.is_module_installed(
                                                    "enthought.etsconfig.api",
                                                    interpreter=interpreter))

        tabs = QTabWidget()
        tabs.addTab(self.create_tab(interface_group, display_group,
                                    bg_group),
                    _("Display"))
        tabs.addTab(self.create_tab(monitor_group, source_group),
                    _("Introspection"))
        tabs.addTab(self.create_tab(pyexec_group, pystartup_group, umr_group),
                    _("Advanced settings"))
        tabs.addTab(self.create_tab(qt_group, mpl_group, ets_group),
                    _("External modules"))
        
        vlayout = QVBoxLayout()
        vlayout.addWidget(tabs)
        self.setLayout(vlayout)

    def python_executable_changed(self, pyexec):
        """Custom Python executable value has been changed"""
        if not self.cus_exec_radio.isChecked():
            return
        if not is_text_string(pyexec):
            pyexec = to_text_string(pyexec.toUtf8(), 'utf-8')
        self.warn_python_compatibility(pyexec)

    def python_executable_switched(self, custom):
        """Python executable default/custom radio button has been toggled"""
        def_pyexec = get_python_executable()
        cust_pyexec = self.pyexec_edit.text()
        if not is_text_string(cust_pyexec):
            cust_pyexec = to_text_string(cust_pyexec.toUtf8(), 'utf-8')
        if def_pyexec != cust_pyexec:
            if custom:
                self.warn_python_compatibility(cust_pyexec)

    def warn_python_compatibility(self, pyexec):
        if not osp.isfile(pyexec):
            return
        spyder_version = sys.version_info[0]
        try:
            args = ["-c", "import sys; print(sys.version_info[0])"]
            proc = programs.run_program(pyexec, args)
            console_version = int(proc.communicate()[0])
        except IOError:
            console_version = spyder_version
        if spyder_version != console_version:
            QMessageBox.warning(self, _('Warning'),
                _("You selected a <b>Python %d</b> interpreter for the console "
                  "but Spyder is running on <b>Python %d</b>!.<br><br>"
                  "Although this is possible, we recommend you to install and "
                  "run Spyder directly with your selected interpreter, to avoid "
                  "seeing false warnings and errors due to the incompatible "
                  "syntax between these two Python versions."
                  ) % (console_version, spyder_version), QMessageBox.Ok)


class ExternalConsole(SpyderPluginWidget):
    """
    Console widget
    """
    CONF_SECTION = 'console'
    CONFIGWIDGET_CLASS = ExternalConsoleConfigPage
    DISABLE_ACTIONS_WHEN_HIDDEN = False

    edit_goto = Signal((str, int, str), (str, int, str, bool))
    focus_changed = Signal()
    redirect_stdio = Signal(bool)
    
    def __init__(self, parent, light_mode):
        if PYQT5:
            SpyderPluginWidget.__init__(self, parent, main = parent)
        else:
            SpyderPluginWidget.__init__(self, parent)
        self.light_mode = light_mode
        self.tabwidget = None
        self.menu_actions = None

        self.help = None # Help plugin
        self.historylog = None # History log plugin
        self.variableexplorer = None # Variable explorer plugin

        self.python_count = 0
        self.terminal_count = 0

        # Python executable selection (initializing default values as well)
        executable = self.get_option('pythonexecutable',
                                     get_python_executable())
        if self.get_option('pythonexecutable/default'):
            executable = get_python_executable()
        
        # Python startup file selection
        if not osp.isfile(self.get_option('pythonstartup', '')):
            self.set_option('pythonstartup', SCIENTIFIC_STARTUP)
        # default/custom settings are mutually exclusive:
        self.set_option('pythonstartup/custom',
                        not self.get_option('pythonstartup/default'))
        
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
            # Don't set document mode to true on OSX because it generates
            # a crash when the console is detached from the main window
            # Fixes Issue 561
            self.tabwidget.setDocumentMode(True)
        self.tabwidget.currentChanged.connect(self.refresh_plugin)
        self.tabwidget.move_data.connect(self.move_tab)
        self.main.sig_pythonpath_changed.connect(self.set_path)
                     
        self.tabwidget.set_close_function(self.close_console)

        if sys.platform == 'darwin':
            tab_container = QWidget()
            tab_container.setObjectName('tab-container')
            tab_layout = QHBoxLayout(tab_container)
            tab_layout.setContentsMargins(0, 0, 0, 0)
            tab_layout.addWidget(self.tabwidget)
            layout.addWidget(tab_container)
        else:
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
        self.update_plugin_title.emit()

    def get_shell_index_from_id(self, shell_id):
        """Return shellwidget index from id"""
        for index, shell in enumerate(self.shellwidgets):
            if id(shell) == shell_id:
                return index
        
    def close_console(self, index=None, from_ipyclient=False):
        """Close console tab from index or widget (or close current tab)"""
        # Get tab index
        if not self.tabwidget.count():
            return
        if index is None:
            index = self.tabwidget.currentIndex()
        
        # Detect what widget we are trying to close
        for i, s in enumerate(self.shellwidgets):
            if index == i:
                shellwidget = s
        
        # If the tab is an IPython kernel, try to detect if it has a client
        # connected to it
        if shellwidget.is_ipykernel:
            ipyclients = self.main.ipyconsole.get_clients()
            if ipyclients:
                for ic in ipyclients:
                    if ic.kernel_widget_id == id(shellwidget):
                        connected_ipyclient = True
                        break
                else:
                    connected_ipyclient = False
            else:
                connected_ipyclient = False
        
        # Closing logic
        if not shellwidget.is_ipykernel or from_ipyclient or \
          not connected_ipyclient:
            self.tabwidget.widget(index).close()
            self.tabwidget.removeTab(index)
            self.filenames.pop(index)
            self.shellwidgets.pop(index)
            self.icons.pop(index)
            self.update_plugin_title.emit()
        else:
            QMessageBox.question(self, _('Trying to kill a kernel?'),
                _("You can't close this kernel because it has one or more "
                  "consoles connected to it.<br><br>"
                  "You need to close them instead or you can kill the kernel "
                  "using the second button from right to left."),
                  QMessageBox.Ok)
                                 
        
    def set_variableexplorer(self, variableexplorer):
        """Set variable explorer plugin"""
        self.variableexplorer = variableexplorer
    
    def set_path(self):
        """Set consoles PYTHONPATH if changed by the user"""
        from spyderlib.widgets.externalshell import pythonshell
        for sw in self.shellwidgets:
            if isinstance(sw, pythonshell.ExternalPythonShell):
                if sw.is_interpreter and sw.is_running():
                    sw.path = self.main.get_spyder_pythonpath()
                    sw.shell.path = sw.path
        
    def __find_python_shell(self, interpreter_only=False):
        current_index = self.tabwidget.currentIndex()
        if current_index == -1:
            return
        from spyderlib.widgets.externalshell import pythonshell
        for index in [current_index]+list(range(self.tabwidget.count())):
            shellwidget = self.tabwidget.widget(index)
            if isinstance(shellwidget, pythonshell.ExternalPythonShell):
                if interpreter_only and not shellwidget.is_interpreter:
                    continue
                elif not shellwidget.is_running():
                    continue
                else:
                    self.tabwidget.setCurrentIndex(index)
                    return shellwidget

    def get_current_shell(self):
        """
        Called by Help to retrieve the current shell instance
        """
        shellwidget = self.__find_python_shell()
        return shellwidget.shell

    def get_running_python_shell(self):
        """
        Called by Help to retrieve a running Python shell instance
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
        
    def run_script_in_current_shell(self, filename, wdir, args, debug, 
                  post_mortem):
        """Run script in current shell, if any"""
        norm = lambda text: remove_backslashes(to_text_string(text))
        line = "%s('%s'" % ('debugfile' if debug else 'runfile',
                            norm(filename))
        if args:
            line += ", args='%s'" % norm(args)
        if wdir:
            line += ", wdir='%s'" % norm(wdir)
        if post_mortem:
            line += ', post_mortem=True'
        line += ")"
        if not self.execute_python_code(line, interpreter_only=True):
            QMessageBox.warning(self, _('Warning'),
                _("No Python console is currently selected to run <b>%s</b>."
                  "<br><br>Please select or open a new Python console "
                  "and try again."
                  ) % osp.basename(norm(filename)), QMessageBox.Ok)
        else:
            self.visibility_changed(True)
            self.raise_()            
            
    def set_current_shell_working_directory(self, directory):
        """Set current shell working directory"""
        shellwidget = self.__find_python_shell()
        if shellwidget is not None:
            directory = encoding.to_unicode_from_fs(directory)
            shellwidget.shell.set_cwd(directory)

    def execute_python_code(self, lines, interpreter_only=False):
        """Execute Python code in an already opened Python interpreter"""
        shellwidget = self.__find_python_shell(
                                        interpreter_only=interpreter_only)
        if (shellwidget is not None) and (not shellwidget.is_ipykernel):
            shellwidget.shell.execute_lines(to_text_string(lines))
            self.activateWindow()
            shellwidget.shell.setFocus()
            return True
        else:
            return False
            
    def pdb_has_stopped(self, fname, lineno, shellwidget):
        """Python debugger has just stopped at frame (fname, lineno)"""      
        # This is a unique form of the edit_goto signal that is intended to 
        # prevent keyboard input from accidentally entering the editor
        # during repeated, rapid entry of debugging commands.    
        self.edit_goto[str, int, str, bool].emit(fname, lineno, '', False)
        if shellwidget.is_ipykernel:
            # Focus client widget, not kernel
            ipw = self.main.ipyconsole.get_focus_widget()
            self.main.ipyconsole.activateWindow()
            ipw.setFocus()
        else:
            self.activateWindow()
            shellwidget.shell.setFocus()
    
    def set_spyder_breakpoints(self):
        """Set all Spyder breakpoints into all shells"""
        for shellwidget in self.shellwidgets:
            shellwidget.shell.set_spyder_breakpoints()    
    
    def start(self, fname, wdir=None, args='', interact=False, debug=False,
              python=True, ipykernel=False, ipyclient=None,
              give_ipyclient_focus=True, python_args='', post_mortem=True):
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
        ipykernel: True: IPython kernel
        ipyclient: True: Automatically create an IPython client
        python_args: additionnal Python interpreter command line options
                   (option "-u" is mandatory, see widgets.externalshell package)
        """
        # Note: fname is None <=> Python interpreter
        if fname is not None and not is_text_string(fname):
            fname = to_text_string(fname)
        if wdir is not None and not is_text_string(wdir):
            wdir = to_text_string(wdir)
        
        if fname is not None and fname in self.filenames:
            index = self.filenames.index(fname)
            if self.get_option('single_tab'):
                old_shell = self.shellwidgets[index]
                if old_shell.is_running():
                    runconfig = get_run_configuration(fname)
                    if runconfig is None or runconfig.show_kill_warning:
                        answer = QMessageBox.question(self, self.get_plugin_title(),
                            _("%s is already running in a separate process.\n"
                              "Do you want to kill the process before starting "
                              "a new one?") % osp.basename(fname),
                            QMessageBox.Yes | QMessageBox.Cancel)
                    else:
                        answer = QMessageBox.Yes

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
            if self.get_option('pythonexecutable/default'):
                pythonexecutable = get_python_executable()
                external_interpreter = False
            else:
                pythonexecutable = self.get_option('pythonexecutable')
                external_interpreter = True
            if self.get_option('pythonstartup/default') or ipykernel:
                pythonstartup = None
            else:
                pythonstartup = self.get_option('pythonstartup', None)
            monitor_enabled = self.get_option('monitor/enabled')
            mpl_backend = self.get_option('matplotlib/backend/value')
            ets_backend = self.get_option('ets_backend')
            qt_api = self.get_option('qt/api')
            if qt_api not in ('pyqt', 'pyside', 'pyqt5'):
                qt_api = None
            merge_output_channels = self.get_option('merge_output_channels')
            colorize_sys_stderr = self.get_option('colorize_sys_stderr')
            umr_enabled = self.get_option('umr/enabled')
            umr_namelist = self.get_option('umr/namelist')
            umr_verbose = self.get_option('umr/verbose')
            ar_timeout = CONF.get('variable_explorer', 'autorefresh/timeout')
            ar_state = CONF.get('variable_explorer', 'autorefresh')

            # CRUCIAL NOTE FOR IPYTHON KERNELS:
            # autorefresh needs to be on so that our monitor
            # can find __ipythonkernel__ in the globals namespace
            # *after* the kernel has been started.
            # Without the ns refresh provided by autorefresh, a
            # client is *never* started (although the kernel is)
            # Fix Issue 1595
            if not ar_state and ipykernel:
                ar_state = True

            if self.light_mode:
                from spyderlib.plugins.variableexplorer import VariableExplorer
                sa_settings = VariableExplorer.get_settings()
            else:
                sa_settings = None
            shellwidget = ExternalPythonShell(self, fname, wdir,
                           interact, debug, post_mortem=post_mortem, 
                           path=pythonpath,
                           python_args=python_args,
                           ipykernel=ipykernel,
                           arguments=args, stand_alone=sa_settings,
                           pythonstartup=pythonstartup,
                           pythonexecutable=pythonexecutable,
                           external_interpreter=external_interpreter,
                           umr_enabled=umr_enabled, umr_namelist=umr_namelist,
                           umr_verbose=umr_verbose, ets_backend=ets_backend,
                           monitor_enabled=monitor_enabled,
                           mpl_backend=mpl_backend, qt_api=qt_api,
                           merge_output_channels=merge_output_channels,
                           colorize_sys_stderr=colorize_sys_stderr,
                           autorefresh_timeout=ar_timeout,
                           autorefresh_state=ar_state,
                           light_background=light_background,
                           menu_actions=self.menu_actions,
                           show_buttons_inside=False,
                           show_elapsed_time=show_elapsed_time)
            shellwidget.sig_pdb.connect(
                              lambda fname, lineno, shellwidget=shellwidget:
                              self.pdb_has_stopped(fname, lineno, shellwidget))
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
        shellwidget.shell.set_codecompletion_enter(
                            self.get_option('codecompletion/enter_key') )
        if python and self.help is not None:
            shellwidget.shell.set_help(self.help)
            shellwidget.shell.set_help_enabled(
                               CONF.get('help', 'connect/python_console'))
        if self.historylog is not None:
            self.historylog.add_history(shellwidget.shell.history_filename)
            shellwidget.shell.append_to_history.connect(
                                             self.historylog.append_to_history)
            shellwidget.shell.go_to_error.connect(self.go_to_error)
            shellwidget.shell.focus_changed.connect(        
                                             lambda: self.focus_changed.emit())
        if python:
            if self.main.editor is not None:
                shellwidget.open_file.connect(self.open_file_in_spyder)
            if fname is None:
                if ipykernel:
                    # Connect client to any possible error while starting the
                    # kernel
                    shellwidget.ipython_kernel_start_error.connect(
                              lambda error: ipyclient.show_kernel_error(error))
                    
                    # Detect if kernel and frontend match or not
                    # Don't apply this for our Mac app because it's
                    # failing, see Issue 2006
                    if self.get_option('pythonexecutable/custom') and \
                      not running_in_mac_app():
                        frontend_ver = programs.get_module_version('IPython')
                        old_vers = ['1', '2']
                        if any([frontend_ver.startswith(v) for v in old_vers]):
                            frontend_ver = '<3.0'
                        else:
                            frontend_ver = '>=3.0'
                        kernel_and_frontend_match = \
                          programs.is_module_installed('IPython',
                                                  version=frontend_ver,
                                                  interpreter=pythonexecutable)
                    else:
                        kernel_and_frontend_match = True

                    # Create a a kernel tab only if frontend and kernel
                    # versions match
                    if kernel_and_frontend_match:
                        tab_name = _("Kernel")
                        tab_icon1 = ima.icon('ipython_console')
                        tab_icon2 = ima.icon('ipython_console_t')
                        shellwidget.create_ipython_client.connect(
                                     lambda cf: self.register_ipyclient(cf,
                                              ipyclient,
                                              shellwidget,
                                              give_focus=give_ipyclient_focus))
                    else:
                        shellwidget.ipython_kernel_start_error.emit(
                          _("Either:"
                            "<ol>"
                            "<li>Your IPython frontend and kernel versions "
                            "are <b>incompatible</b> or</li>"
                            "<li>You <b>don't have</b> IPython installed in "
                            "your external interpreter.</li>"
                            "</ol>"
                            "In any case, we're sorry but we can't create a "
                            "console for you."))
                        shellwidget.deleteLater()
                        shellwidget = None
                        return
                else:
                    self.python_count += 1
                    tab_name = "Python %d" % self.python_count
                    tab_icon1 = ima.icon('python')
                    tab_icon2 = ima.icon('python_t')
            else:
                tab_name = osp.basename(fname)
                tab_icon1 = ima.icon('run')
                tab_icon2 = ima.icon('terminated')
        else:
            fname = id(shellwidget)
            if os.name == 'nt':
                tab_name = _("Command Window")
            else:
                tab_name = _("Terminal")
            self.terminal_count += 1
            tab_name += (" %d" % self.terminal_count)
            tab_icon1 = ima.icon('cmdprompt')
            tab_icon2 = ima.icon('cmdprompt_t')
        self.shellwidgets.insert(index, shellwidget)
        self.filenames.insert(index, fname)
        self.icons.insert(index, (tab_icon1, tab_icon2))
        if index is None:
            index = self.tabwidget.addTab(shellwidget, tab_name)
        else:
            self.tabwidget.insertTab(index, shellwidget, tab_name)
        
        shellwidget.started.connect(
                     lambda sid=id(shellwidget): self.process_started(sid))
        shellwidget.sig_finished.connect(
                     lambda sid=id(shellwidget): self.process_finished(sid))
        self.find_widget.set_editor(shellwidget.shell)
        self.tabwidget.setTabToolTip(index, fname if wdir is None else wdir)
        self.tabwidget.setCurrentIndex(index)
        if self.dockwidget and not self.ismaximized and not ipykernel:
            self.dockwidget.setVisible(True)
            self.dockwidget.raise_()
        
        shellwidget.set_icontext_visible(self.get_option('show_icontext'))
        
        # Start process and give focus to console
        shellwidget.start_shell()
        if not ipykernel:
            self.activateWindow()
            shellwidget.shell.setFocus()
    
    def set_ipykernel_attrs(self, connection_file, kernel_widget, name):
        """Add the pid of the kernel process to an IPython kernel tab"""
        # Set connection file
        kernel_widget.connection_file = connection_file
        
        # If we've reached this point then it's safe to assume IPython
        # is available, and this import should be valid.
        from IPython.core.application import get_ipython_dir
        # For each kernel we launch, setup to delete the associated
        # connection file at the time Spyder exits.
        def cleanup_connection_file(connection_file):
            connection_file = osp.join(get_ipython_dir(), 'profile_default',
                                       'security', connection_file)
            try:
                os.remove(connection_file)
            except OSError:
                pass
        atexit.register(cleanup_connection_file, connection_file)   
        
        # Set tab name according to client master name
        index = self.get_shell_index_from_id(id(kernel_widget))
        tab_name = _("Kernel %s") % name
        self.tabwidget.setTabText(index, tab_name)
    
    def register_ipyclient(self, connection_file, ipyclient, kernel_widget,
                           give_focus=True):
        """
        Register `ipyclient` to be connected to `kernel_widget`
        """
        # Check if our client already has a connection_file and kernel_widget_id
        # which means that we are asking for a kernel restart
        if ipyclient.connection_file is not None \
          and ipyclient.kernel_widget_id is not None:
            restart_kernel = True
        else:
            restart_kernel = False
        
        # Setting kernel widget attributes
        name = ipyclient.name.split('/')[0]
        self.set_ipykernel_attrs(connection_file, kernel_widget, name)
        
        # Creating the client
        ipyconsole = self.main.ipyconsole
        ipyclient.connection_file = connection_file
        ipyclient.kernel_widget_id = id(kernel_widget)
        ipyconsole.register_client(ipyclient, restart=restart_kernel,
                                   give_focus=give_focus)
        
    def open_file_in_spyder(self, fname, lineno):
        """Open file in Spyder's editor from remote process"""
        self.main.editor.activateWindow()
        self.main.editor.raise_()
        self.main.editor.load(fname, lineno)
        
    #------ Private API -------------------------------------------------------
    def process_started(self, shell_id):
        index = self.get_shell_index_from_id(shell_id)
        shell = self.shellwidgets[index]
        icon, _icon = self.icons[index]
        self.tabwidget.setTabIcon(index, icon)
        if self.help is not None:
            self.help.set_shell(shell.shell)
        if self.variableexplorer is not None:
            self.variableexplorer.add_shellwidget(shell)

    def process_finished(self, shell_id):
        index = self.get_shell_index_from_id(shell_id)
        if index is not None:
            # Not sure why it happens, but sometimes the shellwidget has 
            # already been removed, so that's not bad if we can't change
            # the tab icon...
            _icon, icon = self.icons[index]
            self.tabwidget.setTabIcon(index, icon)
        if self.variableexplorer is not None:
            self.variableexplorer.remove_shellwidget(shell_id)
        
    #------ SpyderPluginWidget API --------------------------------------------
    def get_plugin_title(self):
        """Return widget title"""
        title = _('Console')
        if self.filenames:
            index = self.tabwidget.currentIndex()
            fname = self.filenames[index]
            if fname:
                title += ' - ' + to_text_string(fname)
        return title
    
    def get_plugin_icon(self):
        """Return widget icon"""
        return ima.icon('console')
    
    def get_focus_widget(self):
        """
        Return the widget to give focus to when
        this plugin's dockwidget is raised on top-level
        """
        return self.tabwidget.currentWidget()
        
    def get_plugin_actions(self):
        """Return a list of actions related to plugin"""
        interpreter_action = create_action(self,
                            _("Open a &Python console"), None,
                            ima.icon('python'),
                            triggered=self.open_interpreter)
        if os.name == 'nt':
            text = _("Open &command prompt")
            tip = _("Open a Windows command prompt")
        else:
            text = _("Open a &terminal")
            tip = _("Open a terminal window")
        terminal_action = create_action(self, text, None, None, tip,
                                        triggered=self.open_terminal)
        run_action = create_action(self,
                            _("&Run..."), None,
                            ima.icon('run_small'), _("Run a Python script"),
                            triggered=self.run_script)

        consoles_menu_actions = [interpreter_action]
        tools_menu_actions = [terminal_action]
        self.menu_actions = [interpreter_action, terminal_action, run_action]

        self.main.consoles_menu_actions += consoles_menu_actions
        self.main.tools_menu_actions += tools_menu_actions

        return self.menu_actions+consoles_menu_actions+tools_menu_actions

    def register_plugin(self):
        """Register plugin in Spyder's main window"""
        self.main.add_dockwidget(self)
        self.help = self.main.help
        if self.help is not None:
            self.help.set_external_console(self)
        self.historylog = self.main.historylog
        self.edit_goto.connect(self.main.editor.load)
        self.edit_goto[str, int, str, bool].connect(
                        lambda fname, lineno, word, processevents:
                        self.main.editor.load(fname, lineno, word,
                                            processevents=processevents))
        self.main.editor.run_in_current_extconsole.connect(
                        self.run_script_in_current_shell)
        self.main.editor.breakpoints_saved.connect(
                        self.set_spyder_breakpoints)
        self.main.editor.open_dir.connect(
                        self.set_current_shell_working_directory)
        self.main.workingdirectory.set_current_console_wd.connect(
                        self.set_current_shell_working_directory)
        self.focus_changed.connect(
                        self.main.plugin_focus_changed)
        self.redirect_stdio.connect(
                        self.main.redirect_internalshell_stdio)
        expl = self.main.explorer
        if expl is not None:
            expl.open_terminal.connect(self.open_terminal)
            expl.open_interpreter.connect(self.open_interpreter)
        pexpl = self.main.projectexplorer
        if pexpl is not None:
            pexpl.open_terminal.connect(self.open_terminal)
            pexpl.open_interpreter.connect(self.open_interpreter)

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
        self.main.last_console_plugin_focus_was_python = True
        self.update_plugin_title.emit()

    def update_font(self):
        """Update font from Preferences"""
        font = self.get_plugin_font()
        for shellwidget in self.shellwidgets:
            shellwidget.shell.set_font(font)
            completion_size = CONF.get('main', 'completion/size')
            comp_widget = shellwidget.shell.completion_widget
            comp_widget.setup_appearance(completion_size, font)

    def apply_plugin_settings(self, options):
        """Apply configuration file's plugin settings"""
        showtime_n = 'show_elapsed_time'
        showtime_o = self.get_option(showtime_n)
        icontext_n = 'show_icontext'
        icontext_o = self.get_option(icontext_n)
        calltips_n = 'calltips'
        calltips_o = self.get_option(calltips_n)
        help_n = 'connect_to_oi'
        help_o = CONF.get('help', 'connect/python_console')
        wrap_n = 'wrap'
        wrap_o = self.get_option(wrap_n)
        compauto_n = 'codecompletion/auto'
        compauto_o = self.get_option(compauto_n)
        case_comp_n = 'codecompletion/case_sensitive'
        case_comp_o = self.get_option(case_comp_n)
        compenter_n = 'codecompletion/enter_key'
        compenter_o = self.get_option(compenter_n)
        mlc_n = 'max_line_count'
        mlc_o = self.get_option(mlc_n)
        for shellwidget in self.shellwidgets:
            if showtime_n in options:
                shellwidget.set_elapsed_time_visible(showtime_o)
            if icontext_n in options:
                shellwidget.set_icontext_visible(icontext_o)
            if calltips_n in options:
                shellwidget.shell.set_calltips(calltips_o)
            if help_n in options:
                if isinstance(shellwidget, ExternalPythonShell):
                    shellwidget.shell.set_help_enabled(help_o)
            if wrap_n in options:
                shellwidget.shell.toggle_wrap_mode(wrap_o)
            if compauto_n in options:
                shellwidget.shell.set_codecompletion_auto(compauto_o)
            if case_comp_n in options:
                shellwidget.shell.set_codecompletion_case(case_comp_o)
            if compenter_n in options:
                shellwidget.shell.set_codecompletion_enter(compenter_o)
            if mlc_n in options:
                shellwidget.shell.setMaximumBlockCount(mlc_o)
    
    #------ SpyderPluginMixin API ---------------------------------------------
    def toggle_view(self, checked):
        """Toggle view"""
        if checked:
            self.dockwidget.show()
            self.dockwidget.raise_()
            # Start a console in case there are none shown
            from spyderlib.widgets.externalshell import pythonshell
            consoles = None
            for sw in self.shellwidgets:
                if isinstance(sw, pythonshell.ExternalPythonShell):
                    if not sw.is_ipykernel:
                        consoles = True
                        break
            if not consoles:
                self.open_interpreter()
        else:
            self.dockwidget.hide()

    #------ Public API ---------------------------------------------------------
    @Slot(bool)
    @Slot(str)
    def open_interpreter(self, wdir=None):
        """Open interpreter"""
        if not wdir:
            wdir = getcwd()
        self.visibility_changed(True)
        self.start(fname=None, wdir=to_text_string(wdir), args='',
                   interact=True, debug=False, python=True)

    def start_ipykernel(self, client, wdir=None, give_focus=True):
        """Start new IPython kernel"""
        if not self.get_option('monitor/enabled'):
            QMessageBox.warning(self, _('Open an IPython console'),
                _("The console monitor was disabled: the IPython kernel will "
                  "be started as expected, but an IPython console will have "
                  "to be connected manually to the kernel."), QMessageBox.Ok)
        
        if not wdir:
            wdir = getcwd()
        self.main.ipyconsole.visibility_changed(True)
        self.start(fname=None, wdir=to_text_string(wdir), args='',
                   interact=True, debug=False, python=True, ipykernel=True,
                   ipyclient=client, give_ipyclient_focus=give_focus)

    @Slot(bool)
    @Slot(str)
    def open_terminal(self, wdir=None):
        """Open terminal"""
        if not wdir:
            wdir = getcwd()
        self.start(fname=None, wdir=to_text_string(wdir), args='',
                   interact=True, debug=False, python=False)

    @Slot()
    def run_script(self):
        """Run a Python script"""
        self.redirect_stdio.emit(False)
        filename, _selfilter = getopenfilename(self, _("Run Python script"),
                getcwd(), _("Python scripts")+" (*.py ; *.pyw ; *.ipy)")
        self.redirect_stdio.emit(True)
        if filename:
            self.start(fname=filename, wdir=None, args='',
                       interact=False, debug=False)
        
    def set_umr_namelist(self):
        """Set UMR excluded modules name list"""
        arguments, valid = QInputDialog.getText(self, _('UMR'),
                                  _('UMR excluded modules:\n'
                                          '(example: guidata, guiqwt)'),
                                  QLineEdit.Normal,
                                  ", ".join(self.get_option('umr/namelist')))
        if valid:
            arguments = to_text_string(arguments)
            if arguments:
                namelist = arguments.replace(' ', '').split(',')
                fixed_namelist = [module_name for module_name in namelist
                                  if programs.is_module_installed(module_name)]
                invalid = ", ".join(set(namelist)-set(fixed_namelist))
                if invalid:
                    QMessageBox.warning(self, _('UMR'),
                                        _("The following modules are not "
                                          "installed on your machine:\n%s"
                                          ) % invalid, QMessageBox.Ok)
                QMessageBox.information(self, _('UMR'),
                                    _("Please note that these changes will "
                                      "be applied only to new Python/IPython "
                                      "consoles"), QMessageBox.Ok)
            else:
                fixed_namelist = []
            self.set_option('umr/namelist', fixed_namelist)
        
    def go_to_error(self, text):
        """Go to error if relevant"""
        match = get_error_match(to_text_string(text))
        if match:
            fname, lnb = match.groups()
            self.edit_goto.emit(osp.abspath(fname), int(lnb), '')
            
    #----Drag and drop
    def dragEnterEvent(self, event):
        """Reimplement Qt method
        Inform Qt about the types of data that the widget accepts"""
        source = event.mimeData()
        if source.hasUrls():
            if mimedata2url(source):
                pathlist = mimedata2url(source)
                shellwidget = self.tabwidget.currentWidget()
                if all([is_python_script(to_text_string(qstr))
                        for qstr in pathlist]):
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
            if is_python_script(to_text_string(qstr)):
                self.start(qstr)
            elif shellwidget:
                shellwidget.shell.insert_text(qstr)
        elif source.hasUrls():
            pathlist = mimedata2url(source)
            if all([is_python_script(to_text_string(qstr)) 
                    for qstr in pathlist]):
                for fname in pathlist:
                    self.start(fname)
            elif shellwidget:
                shellwidget.shell.drop_pathlist(pathlist)
        event.acceptProposedAction()
