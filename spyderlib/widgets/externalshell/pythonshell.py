# -*- coding: utf-8 -*-
#
# Copyright © 2009 Pierre Raybaut
# Licensed under the terms of the MIT License
# (see spyderlib/__init__.py for details)

"""External Python Shell widget: execute Python script in a separate process"""

import sys, os, os.path as osp, socket

# Debug
STDOUT = sys.stdout
STDERR = sys.stderr

from PyQt4.QtGui import QApplication, QMessageBox, QSplitter, QFileDialog
from PyQt4.QtCore import QProcess, SIGNAL, QString, Qt

# Local imports
from spyderlib.utils.qthelpers import (create_toolbutton, create_action,
                                       get_std_icon)
from spyderlib.utils.programs import split_clo
from spyderlib.config import get_icon
from spyderlib.widgets.shell import PythonShellWidget
from spyderlib.widgets.externalshell import startup
from spyderlib.widgets.externalshell.namespacebrowser import NamespaceBrowser
from spyderlib.widgets.externalshell.monitor import communicate, write_packet
from spyderlib.widgets.externalshell.baseshell import (ExternalShellBase,
                                                   add_pathlist_to_PYTHONPATH)


class ExtPythonShellWidget(PythonShellWidget):
    def __init__(self, parent, history_filename, debug=False, profile=False):
        PythonShellWidget.__init__(self, parent, history_filename,
                                   debug, profile)
    
    def set_externalshell(self, externalshell):
        # ExternalShellBase instance:
        self.externalshell = externalshell
        
    def clear_terminal(self):
        """Reimplement ShellBaseWidget method"""
        self.clear()
        self.emit(SIGNAL("execute(QString)"), "\n")

    def execute_lines(self, lines):
        """
        Execute a set of lines as multiple command
        lines: multiple lines of text to be executed as single commands
        """
        for line in lines.splitlines():
            stripped_line = line.strip()
            if stripped_line.startswith('#'):
                continue
            self.write(line+os.linesep, flush=True)
            self.execute_command(line)
            self.emit(SIGNAL("wait_for_ready_read()"))
            self.flush()

    #------ Code completion / Calltips
    def ask_monitor(self, command):
        sock = self.externalshell.introspection_socket
        if sock is None:
            return
        try:
            return communicate(sock, command)
        except socket.error:
            # Process was just closed            
            pass
            
    def get_dir(self, objtxt):
        """Return dir(object)"""
        return self.ask_monitor("__get_dir__('%s',globals())" % objtxt)

    def get_globals_keys(self):
        """Return shell globals() keys"""
        return self.ask_monitor("globals().keys()")
    
    def get_cdlistdir(self):
        """Return shell current directory list dir"""
        return self.ask_monitor("getcdlistdir()")
            
    def iscallable(self, objtxt):
        """Is object callable?"""
        return self.ask_monitor("__iscallable__('%s',globals())" % objtxt)
    
    def get_arglist(self, objtxt):
        """Get func/method argument list"""
        return self.ask_monitor("__get_arglist__('%s',globals())" % objtxt)
            
    def get__doc__(self, objtxt):
        """Get object __doc__"""
        return self.ask_monitor("__get__doc____('%s',globals())" % objtxt)
    
    def get_doc(self, objtxt):
        """Get object documentation"""
        return self.ask_monitor("__get_doc__('%s',globals())" % objtxt)
    
    def get_source(self, objtxt):
        """Get object source"""
        return self.ask_monitor("__get_source__('%s',globals())" % objtxt)
    
    def is_defined(self, objtxt, force_import=False):
        """Return True if object is defined"""
        return self.ask_monitor(
                        "isdefined('%s', force_import=%s, namespace=globals())"
                        % (objtxt, force_import))

    def get_completion(self, objtxt):
        """Return completion list associated to object name"""
        return self.ask_monitor("getcomplist('%s')" % objtxt)
    
    def get_cwd(self):
        """Return shell current working directory"""
        return self.ask_monitor("getcwd()")
    
    def set_cwd(self, dirname):
        """Set shell current working directory"""
        return self.ask_monitor("setcwd(r'%s')" % dirname)


class ExternalPythonShell(ExternalShellBase):
    """External Shell widget: execute Python script in a separate process"""
    SHELL_CLASS = ExtPythonShellWidget
    def __init__(self, parent=None, fname=None, wdir=None, commands=[],
                 interact=False, debug=False, path=[], python_args='',
                 ipython=False, arguments='', stand_alone=None,
                 umd_enabled=True, umd_namelist=[], umd_verbose=True,
                 monitor_enabled=True, mpl_patch_enabled=True,
                 mpl_backend='Qt4Agg', ets_backend='qt4',
                 autorefresh_timeout=3000, autorefresh_state=True,
                 light_background=True):
        self.namespacebrowser = None # namespace browser widget!
        
        self.breakpoints_cb = None
        
        startup_file = startup.__file__
        if 'library.zip' in startup_file:
            # py2exe distribution
            from spyderlib.config import DATA_DEV_PATH
            startup_file = osp.join(DATA_DEV_PATH, "widgets", "externalshell",
                                    "startup.py")
        self.fname = startup_file if fname is None else fname
        
        self.stand_alone = stand_alone # stand alone settings (None: plugin)
        
        self.monitor_enabled = monitor_enabled
        self.mpl_patch_enabled = mpl_patch_enabled
        self.mpl_backend = mpl_backend
        self.ets_backend = ets_backend
        self.umd_enabled = umd_enabled
        self.umd_namelist = umd_namelist
        self.umd_verbose = umd_verbose
        self.autorefresh_timeout = autorefresh_timeout
        self.autorefresh_state = autorefresh_state
        
        self.namespacebrowser_button = None
        self.cwd_button = None
        self.terminate_button = None
        
        ExternalShellBase.__init__(self, parent, wdir,
                                   history_filename='.history.py',
                                   light_background=light_background)
        
        self.python_args = None
        if python_args:
            assert isinstance(python_args, basestring)
            self.python_args = python_args
        
        assert isinstance(arguments, basestring)
        self.arguments = arguments
        
        self.ipython = ipython
        if self.ipython:
            interact = False
        
        self.shell.set_externalshell(self)

        self.toggle_globals_explorer(False)
        self.interact_action.setChecked(interact)
        self.debug_action.setChecked(debug)
        
        self.introspection_socket = None
        self.interpreter = fname is None
        
        if self.interpreter:
            self.terminate_button.hide()
        
        self.commands = ["import sys", "sys.path.insert(0, '')"] + commands
        
        # Additional python path list
        self.path = path
        
    def set_introspection_socket(self, introspection_socket):
        self.introspection_socket = introspection_socket
        
    def set_breakpoints_cb(self, callback):
        self.breakpoints_cb = callback
        
    def save_all_breakpoints(self):
        """Save all opened files breakpoints in Spyder configuration file
        -- used by the patched pdb"""
        if self.breakpoints_cb is not None:
            return self.breakpoints_cb()
        
    def set_autorefresh_timeout(self, interval):
        communicate(self.introspection_socket,
                    "set_monitor_timeout(%d)" % interval)
        
    def closeEvent(self, event):
        self.quit_monitor()
        ExternalShellBase.closeEvent(self, event)
        
    def get_toolbar_buttons(self):
        ExternalShellBase.get_toolbar_buttons(self)
        if self.namespacebrowser_button is None \
           and self.stand_alone is not None:
            self.namespacebrowser_button = create_toolbutton(self,
                          get_icon('dictedit.png'), self.tr("Variables"),
                          tip=self.tr("Show/hide global variables explorer"),
                          toggled=self.toggle_globals_explorer,
                          text_beside_icon=True)
        if self.cwd_button is None:
            self.cwd_button = create_toolbutton(self,
                      get_std_icon('DirOpenIcon'), self.tr("Working directory"),
                      tip=self.tr("Set current working directory"),
                      triggered=self.set_current_working_directory)
        if self.terminate_button is None:
            self.terminate_button = create_toolbutton(self,
                          get_icon('terminate.png'), self.tr("Terminate"),
                          tip=self.tr("Attempts to terminate the process.\n"
                                      "The process may not exit as a result of "
                                      "clicking this button\n"
                                      "(it is given the chance to prompt "
                                      "the user for any unsaved files, etc)."))        
        buttons = [self.cwd_button]
        if self.namespacebrowser_button is not None:
            buttons.append(self.namespacebrowser_button)
        buttons += [self.run_button, self.options_button,
                    self.terminate_button, self.kill_button]
        return buttons

    def get_options_menu(self):
        self.interact_action = create_action(self, self.tr("Interact"))
        self.interact_action.setCheckable(True)
        self.debug_action = create_action(self, self.tr("Debug"))
        self.debug_action.setCheckable(True)
        self.args_action = create_action(self, self.tr("Arguments..."),
                                         triggered=self.get_arguments)
        return [self.interact_action, self.debug_action, self.args_action]

    def is_interpreter(self):
        """Return True if shellwidget is a Python/IPython interpreter"""
        return self.interpreter
        
    def set_namespacebrowser(self, namespacebrowser):
        """Set namespace browser *widget*"""
        self.namespacebrowser = namespacebrowser
        
    def get_shell_widget(self):
        if self.stand_alone is not None:
            self.namespacebrowser = NamespaceBrowser(self)
            settings = self.stand_alone
            self.namespacebrowser.set_shellwidget(self)
            self.namespacebrowser.setup(**settings)
            self.connect(self.namespacebrowser, SIGNAL('collapse()'),
                         lambda: self.toggle_globals_explorer(False))
            # Shell splitter
            self.splitter = splitter = QSplitter(Qt.Vertical, self)
            self.connect(self.splitter, SIGNAL('splitterMoved(int, int)'),
                         self.splitter_moved)
            splitter.addWidget(self.shell)
            splitter.setCollapsible(0, False)
            splitter.addWidget(self.namespacebrowser)
            splitter.setStretchFactor(0, 1)
            splitter.setStretchFactor(1, 0)
            splitter.setHandleWidth(5)
            splitter.setSizes([2, 1])
            return splitter
        else:
            return self.shell
    
    def get_icon(self):
        return get_icon('python.png')

    def set_buttons_runnning_state(self, state):
        ExternalShellBase.set_buttons_runnning_state(self, state)
        self.interact_action.setEnabled(not state and not self.interpreter)
        self.debug_action.setEnabled(not state and not self.interpreter)
        self.args_action.setEnabled(not state and
                                    (not self.interpreter or self.ipython))
        if state:
            if self.arguments:
                argstr = self.tr("Arguments: %1").arg(self.arguments)
            else:
                argstr = self.tr("No argument")
        else:
            argstr = self.tr("Arguments...")
        self.args_action.setText(argstr)
        self.terminate_button.setEnabled(state)
        if not state:
            self.toggle_globals_explorer(False)
        self.cwd_button.setEnabled(state)
        if self.namespacebrowser_button is not None:
            self.namespacebrowser_button.setEnabled(state)
    
    def create_process(self):
        self.shell.clear()
            
        self.process = QProcess(self)
        if self.ipython:
            self.process.setProcessChannelMode(QProcess.MergedChannels)
        else:
            self.process.setProcessChannelMode(QProcess.SeparateChannels)
        self.connect(self.shell, SIGNAL("wait_for_ready_read()"),
                     lambda: self.process.waitForReadyRead(250))
        
        # Working directory
        if self.wdir is not None:
            self.process.setWorkingDirectory(self.wdir)

        #-------------------------Python specific-------------------------------
        # Python arguments
        p_args = ['-u']
        if self.python_args is not None:
            p_args += self.python_args.split()
        if self.interact_action.isChecked():
            p_args.append('-i')
        if self.debug_action.isChecked():
            p_args.extend(['-m', 'pdb'])
        if os.name == 'nt' and self.debug_action.isChecked():
            # When calling pdb on Windows, one has to replace backslashes by
            # slashes to avoid confusion with escape characters (otherwise, 
            # for example, '\t' will be interpreted as a tabulation):
            p_args.append(osp.normpath(self.fname).replace(os.sep, '/'))
        else:
            p_args.append(self.fname)
        
        env = self.process.systemEnvironment()
        
        # Monitor
        if self.monitor_enabled:
            env.append('SPYDER_SHELL_ID=%s' % id(self))
            env.append('SPYDER_AR_TIMEOUT=%d' % self.autorefresh_timeout)
            env.append('SPYDER_AR_STATE=%r' % self.autorefresh_state)
            from spyderlib.widgets.externalshell import monitor
            introspection_server = monitor.start_introspection_server()
            introspection_server.register(self)
            notification_server = monitor.start_notification_server()
            self.notification_thread = notification_server.register(self)
            self.connect(self.notification_thread,
                         SIGNAL('refresh_namespace_browser()'),
                         self.namespacebrowser.refresh_table)
            self.connect(self.notification_thread, SIGNAL('pdb(QString,int)'),
                         lambda fname, lineno:
                         self.emit(SIGNAL('pdb(QString,int)'), fname, lineno))
            self.connect(self.notification_thread,
                         SIGNAL('process_remote_view(PyQt_PyObject)'),
                         self.namespacebrowser.process_remote_view)
            env.append('SPYDER_I_PORT=%d' % introspection_server.port)
            env.append('SPYDER_N_PORT=%d' % notification_server.port)
        
        # Python init commands (interpreter only)
        if self.commands and self.interpreter:
            env.append('PYTHONINITCOMMANDS=%s' % ';'.join(self.commands))
            self.process.setEnvironment(env)
        
        # External modules options
        env.append('ETS_TOOLKIT=%s' % self.ets_backend)
        env.append('MATPLOTLIB_PATCH=%r' % self.mpl_patch_enabled)
        env.append('MATPLOTLIB_BACKEND=%s' % self.mpl_backend)
        
        # User Module Deleter
        if self.interpreter:
            env.append('UMD_ENABLED=%r' % self.umd_enabled)
            env.append('UMD_NAMELIST=%s' % ','.join(self.umd_namelist))
            env.append('UMD_VERBOSE=%r' % self.umd_verbose)
        
        # IPython related configuration
        if self.ipython:
            env.append('IPYTHON=True')
            # Do not call msvcrt.getch in IPython.genutils.page_more:
            env.append('TERM=emacs')
            
        pathlist = []

        # Fix encoding with custom "sitecustomize.py"
        scpath = osp.dirname(osp.abspath(__file__))
        pathlist.append(scpath)
        
        # Adding Spyder path
        pathlist += self.path
        
        # Adding path list to PYTHONPATH environment variable
        add_pathlist_to_PYTHONPATH(env, pathlist)
        
        self.process.setEnvironment(env)
        #-------------------------Python specific-------------------------------
            
        if self.arguments:
            p_args.extend( split_clo(self.arguments) )
                        
        self.connect(self.process, SIGNAL("readyReadStandardOutput()"),
                     self.write_output)
        self.connect(self.process, SIGNAL("readyReadStandardError()"),
                     self.write_error)
        self.connect(self.process, SIGNAL("finished(int,QProcess::ExitStatus)"),
                     self.finished)

        self.connect(self.terminate_button, SIGNAL("clicked()"),
                     self.process.terminate)
        self.connect(self.kill_button, SIGNAL("clicked()"),
                     self.process.kill)
        
        #-------------------------Python specific-------------------------------
        executable = sys.executable
        if executable.endswith("spyder.exe"):
            # py2exe distribution
            executable = "python.exe"
        self.process.start(executable, p_args)
        #-------------------------Python specific-------------------------------
            
        running = self.process.waitForStarted()
        self.set_running_state(running)
        if not running:
            QMessageBox.critical(self, self.tr("Error"),
                                 self.tr("Process failed to start"))
        else:
            self.shell.setFocus()
            self.emit(SIGNAL('started()'))
            
        return self.process
    
#===============================================================================
#    Input/Output
#===============================================================================
    def write_error(self):
        #---This is apparently necessary only on Windows (not sure though):
        #   emptying standard output buffer before writing error output
        self.process.setReadChannel(QProcess.StandardOutput)
        if self.process.waitForReadyRead(1):
            self.write_output()
            
        self.shell.write_error(self.get_stderr())
        QApplication.processEvents()
        
    def send_to_process(self, qstr):
        if not isinstance(qstr, QString):
            qstr = QString(qstr)
        if not qstr.endsWith('\n'):
            qstr.append('\n')
        self.process.write(qstr.toLocal8Bit())
        self.process.waitForBytesWritten(-1)
        
        # Eventually write prompt faster (when hitting Enter continuously)
        # -- necessary/working on Windows only:
        if os.name == 'nt':
            self.write_error()
        
    def keyboard_interrupt(self):
        if self.introspection_socket is not None:
            communicate(self.introspection_socket, "thread.interrupt_main()")
        
    def quit_monitor(self):
        if self.introspection_socket is not None:
            try:
                write_packet(self.introspection_socket, "thread.exit()")
            except socket.error:
                pass
            
#===============================================================================
#    Globals explorer
#===============================================================================
    def toggle_globals_explorer(self, state):
        if self.stand_alone is not None:
            self.splitter.setSizes([1, 1 if state else 0])
            self.namespacebrowser_button.setChecked(state)
            if state:
                self.namespacebrowser.refresh_table()
        
    def splitter_moved(self, pos, index):
        self.namespacebrowser_button.setChecked( self.splitter.sizes()[1] )

#===============================================================================
#    Current working directory
#===============================================================================
    def set_current_working_directory(self):
        cwd = self.shell.get_cwd()
        self.emit(SIGNAL('redirect_stdio(bool)'), False)
        directory = QFileDialog.getExistingDirectory(self,
                                             self.tr("Select directory"), cwd)
        if not directory.isEmpty():
            self.shell.set_cwd(unicode(directory))
        self.emit(SIGNAL('redirect_stdio(bool)'), True)
