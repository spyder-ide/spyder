# -*- coding: utf-8 -*-
#
# Copyright © 2009-2010 Pierre Raybaut
# Licensed under the terms of the MIT License
# (see spyderlib/__init__.py for details)

"""External Python Shell widget: execute Python script in a separate process"""

import sys
import os
import os.path as osp
import socket

from spyderlib.qt.QtGui import QApplication, QMessageBox, QSplitter, QMenu
from spyderlib.qt.QtCore import QProcess, SIGNAL, Qt
from spyderlib.qt.compat import getexistingdirectory

# Local imports
from spyderlib.utils.qthelpers import (get_icon, get_std_icon, add_actions,
                                       create_toolbutton, create_action,
                                       DialogManager)
from spyderlib.utils.environ import RemoteEnvDialog
from spyderlib.utils.programs import get_python_args
from spyderlib.utils.misc import get_python_executable
from spyderlib.baseconfig import (_, get_module_source_path, DEBUG,
                                  MAC_APP_NAME, running_in_mac_app)
from spyderlib.widgets.shell import PythonShellWidget
from spyderlib.widgets.externalshell.namespacebrowser import NamespaceBrowser
from spyderlib.utils.bsdsocket import communicate, write_packet
from spyderlib.widgets.externalshell.baseshell import (ExternalShellBase,
                                                   add_pathlist_to_PYTHONPATH)
from spyderlib.widgets.dicteditor import DictEditor
from spyderlib.py3compat import (is_text_string, to_text_string,
                                 to_binary_string)


class ExtPythonShellWidget(PythonShellWidget):
    def __init__(self, parent, history_filename, profile=False):
        PythonShellWidget.__init__(self, parent, history_filename, profile)
        self.path = []
    
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
            # Workaround for Issue 502
            # Emmiting wait_for_ready_read was making the console hang
            # in Mac OS X
            if sys.platform.startswith("darwin"):
                import time
                time.sleep(0.025)
            else:
                self.emit(SIGNAL("wait_for_ready_read()"))
            self.flush()

    #------ Code completion / Calltips
    def ask_monitor(self, command, settings=[]):
        sock = self.externalshell.introspection_socket
        if sock is None:
            return
        try:
            return communicate(sock, command, settings=settings)
        except socket.error:
            # Process was just closed            
            pass
        except MemoryError:
            # Happens when monitor is not ready on slow machines
            pass
            
    def get_dir(self, objtxt):
        """Return dir(object)"""
        return self.ask_monitor("__get_dir__('%s')" % objtxt)

    def get_globals_keys(self):
        """Return shell globals() keys"""
        return self.ask_monitor("get_globals_keys()")
    
    def get_cdlistdir(self):
        """Return shell current directory list dir"""
        return self.ask_monitor("getcdlistdir()")
            
    def iscallable(self, objtxt):
        """Is object callable?"""
        return self.ask_monitor("__iscallable__('%s')" % objtxt)
    
    def get_arglist(self, objtxt):
        """Get func/method argument list"""
        return self.ask_monitor("__get_arglist__('%s')" % objtxt)
            
    def get__doc__(self, objtxt):
        """Get object __doc__"""
        return self.ask_monitor("__get__doc____('%s')" % objtxt)
    
    def get_doc(self, objtxt):
        """Get object documentation dictionary"""
        return self.ask_monitor("__get_doc__('%s')" % objtxt)
    
    def get_source(self, objtxt):
        """Get object source"""
        return self.ask_monitor("__get_source__('%s')" % objtxt)
    
    def is_defined(self, objtxt, force_import=False):
        """Return True if object is defined"""
        return self.ask_monitor("isdefined('%s', force_import=%s)"
                                % (objtxt, force_import))
        
    def get_module_completion(self, objtxt):
        """Return module completion list associated to object name"""
        return self.ask_monitor("getmodcomplist('%s', %s)" % \
                                                           (objtxt, self.path))
    
    def get_cwd(self):
        """Return shell current working directory"""
        return self.ask_monitor("getcwd()")
    
    def set_cwd(self, dirname):
        """Set shell current working directory"""
        return self.ask_monitor("setcwd(r'%s')" % dirname)
        
    def get_env(self):
        """Return environment variables: os.environ"""
        return self.ask_monitor("getenv()")
        
    def set_env(self, env):
        """Set environment variables via os.environ"""
        return self.ask_monitor('setenv()', settings=[env])
        
    def get_syspath(self):
        """Return sys.path[:]"""
        return self.ask_monitor("getsyspath()")

    def set_spyder_breakpoints(self):
        """Set Spyder breakpoints into debugging session"""
        return self.ask_monitor("set_spyder_breakpoints()")
        

class ExternalPythonShell(ExternalShellBase):
    """External Shell widget: execute Python script in a separate process"""
    SHELL_CLASS = ExtPythonShellWidget
    def __init__(self, parent=None, fname=None, wdir=None,
                 interact=False, debug=False, path=[], python_args='',
                 ipykernel=False, arguments='', stand_alone=None,
                 umr_enabled=True, umr_namelist=[], umr_verbose=True,
                 pythonstartup=None, pythonexecutable=None,
                 monitor_enabled=True, mpl_backend=None, ets_backend='qt4',
                 qt_api=None, pyqt_api=0,
                 ignore_sip_setapi_errors=False, merge_output_channels=False,
                 colorize_sys_stderr=False, autorefresh_timeout=3000,
                 autorefresh_state=True, light_background=True,
                 menu_actions=None, show_buttons_inside=True,
                 show_elapsed_time=True):

        assert qt_api in (None, 'pyqt', 'pyside')

        self.namespacebrowser = None # namespace browser widget!
        
        self.dialog_manager = DialogManager()
        
        self.stand_alone = stand_alone # stand alone settings (None: plugin)
        self.interact = interact
        self.is_ipykernel = ipykernel
        self.pythonstartup = pythonstartup
        self.pythonexecutable = pythonexecutable
        self.monitor_enabled = monitor_enabled
        self.mpl_backend = mpl_backend
        self.ets_backend = ets_backend
        self.qt_api = qt_api
        self.pyqt_api = pyqt_api
        self.ignore_sip_setapi_errors = ignore_sip_setapi_errors
        self.merge_output_channels = merge_output_channels
        self.colorize_sys_stderr = colorize_sys_stderr
        self.umr_enabled = umr_enabled
        self.umr_namelist = umr_namelist
        self.umr_verbose = umr_verbose
        self.autorefresh_timeout = autorefresh_timeout
        self.autorefresh_state = autorefresh_state
                
        self.namespacebrowser_button = None
        self.cwd_button = None
        self.env_button = None
        self.syspath_button = None
        self.terminate_button = None

        self.notification_thread = None
        
        ExternalShellBase.__init__(self, parent=parent, fname=fname, wdir=wdir,
                                   history_filename='history.py',
                                   light_background=light_background,
                                   menu_actions=menu_actions,
                                   show_buttons_inside=show_buttons_inside,
                                   show_elapsed_time=show_elapsed_time)

        if self.pythonexecutable is None:
            self.pythonexecutable = get_python_executable()

        self.python_args = None
        if python_args:
            assert is_text_string(python_args)
            self.python_args = python_args
        
        assert is_text_string(arguments)
        self.arguments = arguments
        
        self.connection_file = None

        if self.is_ipykernel:
            self.interact = False
            # Running our custom startup script for IPython kernels:
            # (see spyderlib/widgets/externalshell/start_ipython_kernel.py)
            self.fname = get_module_source_path(
                'spyderlib.widgets.externalshell', 'start_ipython_kernel.py')
        
        self.shell.set_externalshell(self)

        self.toggle_globals_explorer(False)
        self.interact_action.setChecked(self.interact)
        self.debug_action.setChecked(debug)
        
        self.introspection_socket = None
        self.is_interpreter = fname is None
        
        if self.is_interpreter:
            self.terminate_button.hide()
        
        # Additional python path list
        self.path = path
        self.shell.path = path
        
    def set_introspection_socket(self, introspection_socket):
        self.introspection_socket = introspection_socket
        if self.namespacebrowser is not None:
            settings = self.namespacebrowser.get_view_settings()
            communicate(introspection_socket,
                        'set_remote_view_settings()', settings=[settings])
        
    def set_autorefresh_timeout(self, interval):
        if self.introspection_socket is not None:
            try:
                communicate(self.introspection_socket,
                            "set_monitor_timeout(%d)" % interval)
            except socket.error:
                pass
        
    def closeEvent(self, event):
        self.quit_monitor()
        ExternalShellBase.closeEvent(self, event)
        
    def get_toolbar_buttons(self):
        ExternalShellBase.get_toolbar_buttons(self)
        if self.namespacebrowser_button is None \
           and self.stand_alone is not None:
            self.namespacebrowser_button = create_toolbutton(self,
                  text=_("Variables"), icon=get_icon('dictedit.png'),
                  tip=_("Show/hide global variables explorer"),
                  toggled=self.toggle_globals_explorer, text_beside_icon=True)
        if self.terminate_button is None:
            self.terminate_button = create_toolbutton(self,
                  text=_("Terminate"), icon=get_icon('stop.png'),
                  tip=_("Attempts to stop the process. The process\n"
                        "may not exit as a result of clicking this\n"
                        "button (it is given the chance to prompt\n"
                        "the user for any unsaved files, etc)."))
        buttons = []
        if self.namespacebrowser_button is not None:
            buttons.append(self.namespacebrowser_button)
        buttons += [self.run_button, self.terminate_button, self.kill_button,
                    self.options_button]
        return buttons

    def get_options_menu(self):
        ExternalShellBase.get_options_menu(self)
        self.interact_action = create_action(self, _("Interact"))
        self.interact_action.setCheckable(True)
        self.debug_action = create_action(self, _("Debug"))
        self.debug_action.setCheckable(True)
        self.args_action = create_action(self, _("Arguments..."),
                                         triggered=self.get_arguments)
        run_settings_menu = QMenu(_("Run settings"), self)
        add_actions(run_settings_menu,
                    (self.interact_action, self.debug_action, self.args_action))
        self.cwd_button = create_action(self, _("Working directory"),
                                icon=get_std_icon('DirOpenIcon'),
                                tip=_("Set current working directory"),
                                triggered=self.set_current_working_directory)
        self.env_button = create_action(self, _("Environment variables"),
                                        icon=get_icon('environ.png'),
                                        triggered=self.show_env)
        self.syspath_button = create_action(self,
                                            _("Show sys.path contents"),
                                            icon=get_icon('syspath.png'),
                                            triggered=self.show_syspath)
        actions = [run_settings_menu, self.show_time_action, None,
                   self.cwd_button, self.env_button, self.syspath_button]
        if self.menu_actions is not None:
            actions += [None]+self.menu_actions
        return actions

    def is_interpreter(self):
        """Return True if shellwidget is a Python interpreter"""
        return self.is_interpreter
        
    def get_shell_widget(self):
        if self.stand_alone is None:
            return self.shell
        else:
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
    
    def get_icon(self):
        return get_icon('python.png')

    def set_buttons_runnning_state(self, state):
        ExternalShellBase.set_buttons_runnning_state(self, state)
        self.interact_action.setEnabled(not state and not self.is_interpreter)
        self.debug_action.setEnabled(not state and not self.is_interpreter)
        self.args_action.setEnabled(not state and not self.is_interpreter)
        if state:
            if self.arguments:
                argstr = _("Arguments: %s") % self.arguments
            else:
                argstr = _("No argument")
        else:
            argstr = _("Arguments...")
        self.args_action.setText(argstr)
        self.terminate_button.setVisible(not self.is_interpreter and state)
        if not state:
            self.toggle_globals_explorer(False)
        for btn in (self.cwd_button, self.env_button, self.syspath_button):
            btn.setEnabled(state and self.monitor_enabled)
        if self.namespacebrowser_button is not None:
            self.namespacebrowser_button.setEnabled(state)
    
    def set_namespacebrowser(self, namespacebrowser):
        """
        Set namespace browser *widget*
        Note: this method is not used in stand alone mode
        """
        self.namespacebrowser = namespacebrowser
        self.configure_namespacebrowser()
        
    def configure_namespacebrowser(self):
        """Connect the namespace browser to the notification thread"""
        if self.notification_thread is not None:
            self.connect(self.notification_thread,
                         SIGNAL('refresh_namespace_browser()'),
                         self.namespacebrowser.refresh_table)
            signal = self.notification_thread.sig_process_remote_view
            signal.connect(lambda data:
                           self.namespacebrowser.process_remote_view(data))
    
    def create_process(self):
        self.shell.clear()
            
        self.process = QProcess(self)
        if self.merge_output_channels:
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
        if DEBUG >= 3:
            p_args += ['-v']
        p_args += get_python_args(self.fname, self.python_args,
                                  self.interact_action.isChecked(),
                                  self.debug_action.isChecked(),
                                  self.arguments)
        
        env = [to_text_string(_path)
               for _path in self.process.systemEnvironment()]
        if self.pythonstartup:
            env.append('PYTHONSTARTUP=%s' % self.pythonstartup)
        
        # Set standard input/output encoding for Python consoles
        # (IPython handles it on its own)
        # See http://stackoverflow.com/q/26312400/438386, specifically
        # the comments of Martijn Pieters
        if not self.is_ipykernel:
            env.append('PYTHONIOENCODING=UTF-8')
        
        # Monitor
        if self.monitor_enabled:
            env.append('SPYDER_SHELL_ID=%s' % id(self))
            env.append('SPYDER_AR_TIMEOUT=%d' % self.autorefresh_timeout)
            env.append('SPYDER_AR_STATE=%r' % self.autorefresh_state)
            from spyderlib.widgets.externalshell import introspection
            introspection_server = introspection.start_introspection_server()
            introspection_server.register(self)
            notification_server = introspection.start_notification_server()
            self.notification_thread = notification_server.register(self)
            self.connect(self.notification_thread, SIGNAL('pdb(QString,int)'),
                         lambda fname, lineno:
                         self.emit(SIGNAL('pdb(QString,int)'), fname, lineno))
            self.connect(self.notification_thread,
                         SIGNAL('new_ipython_kernel(QString)'),
                         lambda args:
                         self.emit(SIGNAL('create_ipython_client(QString)'),
                         args))
            self.connect(self.notification_thread,
                         SIGNAL('open_file(QString,int)'),
                         lambda fname, lineno:
                         self.emit(SIGNAL('open_file(QString,int)'),
                                   fname, lineno))
            if self.namespacebrowser is not None:
                self.configure_namespacebrowser()
            env.append('SPYDER_I_PORT=%d' % introspection_server.port)
            env.append('SPYDER_N_PORT=%d' % notification_server.port)
        
        # External modules options
        env.append('ETS_TOOLKIT=%s' % self.ets_backend)
        if self.mpl_backend:
            env.append('MATPLOTLIB_BACKEND=%s' % self.mpl_backend)
        if self.qt_api:
            env.append('QT_API=%s' % self.qt_api)
        env.append('COLORIZE_SYS_STDERR=%s' % self.colorize_sys_stderr)
#        # Socket-based alternative (see input hook in sitecustomize.py):
#        if self.install_qt_inputhook:
#            from PyQt4.QtNetwork import QLocalServer
#            self.local_server = QLocalServer()
#            self.local_server.listen(str(id(self)))
        if self.pyqt_api:
            env.append('PYQT_API=%d' % self.pyqt_api)
        env.append('IGNORE_SIP_SETAPI_ERRORS=%s'
                   % self.ignore_sip_setapi_errors)
        
        # User Module Deleter
        if self.is_interpreter:
            env.append('UMR_ENABLED=%r' % self.umr_enabled)
            env.append('UMR_NAMELIST=%s' % ','.join(self.umr_namelist))
            env.append('UMR_VERBOSE=%r' % self.umr_verbose)
            env.append('MATPLOTLIB_ION=True')
        else:
            if self.interact:
                env.append('MATPLOTLIB_ION=True')
            else:
                env.append('MATPLOTLIB_ION=False')

        # IPython kernel
        env.append('IPYTHON_KERNEL=%r' % self.is_ipykernel)

        # Add sitecustomize path to path list 
        pathlist = []
        scpath = osp.dirname(osp.abspath(__file__))
        pathlist.append(scpath)
        
        # Adding Spyder path
        pathlist += self.path
        
        # Adding path list to PYTHONPATH environment variable
        add_pathlist_to_PYTHONPATH(env, pathlist)

        #-------------------------Python specific-------------------------------
                        
        self.connect(self.process, SIGNAL("readyReadStandardOutput()"),
                     self.write_output)
        self.connect(self.process, SIGNAL("readyReadStandardError()"),
                     self.write_error)
        self.connect(self.process, SIGNAL("finished(int,QProcess::ExitStatus)"),
                     self.finished)
                     
        self.connect(self, SIGNAL('finished()'), self.dialog_manager.close_all)

        self.connect(self.terminate_button, SIGNAL("clicked()"),
                     self.process.terminate)
        self.connect(self.kill_button, SIGNAL("clicked()"),
                     self.process.kill)
        
        #-------------------------Python specific-------------------------------
        # Fixes for our Mac app:
        # 1. PYTHONPATH and PYTHONHOME are set while bootstrapping the app,
        #    but their values are messing sys.path for external interpreters
        #    (e.g. EPD) so we need to remove them from the environment.
        # 2. Set PYTHONPATH again but without grabbing entries defined in the
        #    environment (Fixes Issue 1321)
        # 3. Remove PYTHONOPTIMIZE from env so that we can have assert
        #    statements working with our interpreters (See Issue 1281)
        if running_in_mac_app():
            env.append('SPYDER_INTERPRETER=%s' % self.pythonexecutable)
            if MAC_APP_NAME not in self.pythonexecutable:
                env = [p for p in env if not (p.startswith('PYTHONPATH') or \
                                              p.startswith('PYTHONHOME'))] # 1.

                add_pathlist_to_PYTHONPATH(env, pathlist, drop_env=True)   # 2.
            env = [p for p in env if not p.startswith('PYTHONOPTIMIZE')]   # 3.

        self.process.setEnvironment(env)
        self.process.start(self.pythonexecutable, p_args)
        #-------------------------Python specific-------------------------------
            
        running = self.process.waitForStarted(3000)
        self.set_running_state(running)
        if not running:
            if self.is_ipykernel:
                self.emit(SIGNAL("ipython_kernel_start_error(QString)"),
                          _("The kernel failed to start!! That's all we know... "
                            "Please close this console and open a new one."))
            else:
                QMessageBox.critical(self, _("Error"),
                                     _("A Python console failed to start!"))
        else:
            self.shell.setFocus()
            self.emit(SIGNAL('started()'))
        return self.process

    def finished(self, exit_code, exit_status):
        """Reimplement ExternalShellBase method"""
        if self.is_ipykernel and exit_code == 1:
            self.emit(SIGNAL("ipython_kernel_start_error(QString)"),
                      self.shell.get_text_with_eol())
        ExternalShellBase.finished(self, exit_code, exit_status)
        self.introspection_socket = None

    
#===============================================================================
#    Input/Output
#===============================================================================
    def write_error(self):
        if os.name == 'nt':
            #---This is apparently necessary only on Windows (not sure though):
            #   emptying standard output buffer before writing error output
            self.process.setReadChannel(QProcess.StandardOutput)
            if self.process.waitForReadyRead(1):
                self.write_output()
        self.shell.write_error(self.get_stderr())
        QApplication.processEvents()
        
    def send_to_process(self, text):
        if not self.is_running():
            return
            
        if not is_text_string(text):
            text = to_text_string(text)
        if self.mpl_backend == 'Qt4Agg' and os.name == 'nt' and \
          self.introspection_socket is not None:
            communicate(self.introspection_socket,
                        "toggle_inputhook_flag(True)")
#            # Socket-based alternative (see input hook in sitecustomize.py):
#            while self.local_server.hasPendingConnections():
#                self.local_server.nextPendingConnection().write('go!')
        if any([text == cmd for cmd in ['%ls', '%pwd', '%scientific']]) or \
          any([text.startswith(cmd) for cmd in ['%cd ', '%clear ']]):
            text = 'evalsc(r"%s")\n' % text
        if not text.endswith('\n'):
            text += '\n'
        self.process.write(to_binary_string(text, 'utf8'))
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
            if state and self.namespacebrowser is not None:
                self.namespacebrowser.refresh_table()
        
    def splitter_moved(self, pos, index):
        self.namespacebrowser_button.setChecked( self.splitter.sizes()[1] )

#===============================================================================
#    Misc.
#===============================================================================
    def set_current_working_directory(self):
        """Set current working directory"""
        cwd = self.shell.get_cwd()
        self.emit(SIGNAL('redirect_stdio(bool)'), False)
        directory = getexistingdirectory(self, _("Select directory"), cwd)
        if directory:
            self.shell.set_cwd(directory)
        self.emit(SIGNAL('redirect_stdio(bool)'), True)

    def show_env(self):
        """Show environment variables"""
        get_func = self.shell.get_env
        set_func = self.shell.set_env
        self.dialog_manager.show(RemoteEnvDialog(get_func, set_func))
        
    def show_syspath(self):
        """Show sys.path contents"""
        editor = DictEditor()
        editor.setup(self.shell.get_syspath(), title="sys.path", readonly=True,
                     width=600, icon='syspath.png')
        self.dialog_manager.show(editor)
