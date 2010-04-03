# -*- coding: utf-8 -*-
#
# Copyright © 2009 Pierre Raybaut
# Licensed under the terms of the MIT License
# (see spyderlib/__init__.py for details)

"""External Python Shell widget: execute Python script in a separate process"""

import sys, os
import os.path as osp

# Debug
STDOUT = sys.stdout
STDERR = sys.stderr

from PyQt4.QtGui import QApplication, QMessageBox, QSplitter
from PyQt4.QtCore import QProcess, SIGNAL, QString, Qt

# Local imports
from spyderlib.utils.qthelpers import create_toolbutton, create_action
from spyderlib.config import CONF, get_icon
from spyderlib.widgets.shell import PythonShellWidget
from spyderlib.widgets.externalshell import startup
from spyderlib.widgets.externalshell.globalsexplorer import GlobalsExplorer
from spyderlib.widgets.externalshell.monitor import communicate
from spyderlib.widgets.externalshell import (ExternalShellBase,
                                             add_pathlist_to_PYTHONPATH)


class ExtPyQsciShell(PythonShellWidget):
    def __init__(self, parent, history_filename, debug=False, profile=False):
        PythonShellWidget.__init__(self, parent, history_filename,
                                   debug, profile)
        # Code completion / calltips
        getcfg = lambda option: CONF.get('external_shell', option)
        case_sensitive = getcfg('autocompletion/case-sensitivity')
        show_single = getcfg('autocompletion/select-single')
        from_document = getcfg('autocompletion/from-document')
        self.setup_code_completion(case_sensitive, show_single, from_document)
    
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
        sock = self.externalshell.monitor_socket
        if sock is None:
            return
        return communicate(sock, command, pickle_try=True)
            
    def get_dir(self, objtxt):
        """Return dir(object)"""
        return self.ask_monitor("getobjdir(%s)" % objtxt)
            
    def iscallable(self, objtxt):
        """Is object callable?"""
        return self.ask_monitor("callable(%s)" % objtxt)
    
    def get_arglist(self, objtxt):
        """Get func/method argument list"""
        return self.ask_monitor("getargtxt(%s)" % objtxt)
            
    def get__doc__(self, objtxt):
        """Get object __doc__"""
        return self.ask_monitor("%s.__doc__" % objtxt)
    
    def get_doc(self, objtxt):
        """Get object documentation"""
        return self.ask_monitor("getdoc(%s)" % objtxt)
    
    def get_source(self, objtxt):
        """Get object source"""
        return self.ask_monitor("getsource(%s)" % objtxt)
    
    def is_defined(self, objtxt, force_import=False):
        """Return True if object is defined"""
        return self.ask_monitor("isdefined('%s', force_import=%s)"
                                % (objtxt, force_import))


class ExternalPythonShell(ExternalShellBase):
    """External Shell widget: execute Python script in a separate process"""
    SHELL_CLASS = ExtPyQsciShell
    def __init__(self, parent=None, fname=None, wdir=None, commands=[],
                 interact=False, debug=False, path=[]):
        self.fname = startup.__file__ if fname is None else fname
        
        self.globalsexplorer_button = None
        self.terminate_button = None
        
        ExternalShellBase.__init__(self, parent, wdir,
                                   history_filename='.history_ec.py')
        
        self.shell.set_externalshell(self)

        self.toggle_globals_explorer(False)
        self.interact_action.setChecked(interact)
        self.debug_action.setChecked(debug)
        
        self.monitor_socket = None
        self.interpreter = fname is None
        
        if self.interpreter:
            self.options_button.hide()
            self.terminate_button.hide()
        
        self.commands = ["import sys", "sys.path.insert(0, '')"] + commands
        
        # Additional python path list
        self.path = path
        
    def get_toolbar_buttons(self):
        ExternalShellBase.get_toolbar_buttons(self)
        if self.globalsexplorer_button is None:
            self.globalsexplorer_button = create_toolbutton(self,
                          get_icon('dictedit.png'), self.tr("Variables"),
                          tip=self.tr("Show/hide global variables explorer"),
                          toggled=self.toggle_globals_explorer)
        if self.terminate_button is None:
            self.terminate_button = create_toolbutton(self,
                          get_icon('terminate.png'), self.tr("Terminate"),
                          tip=self.tr("Attempts to terminate the process.\n"
                                      "The process may not exit as a result of "
                                      "clicking this button\n"
                                      "(it is given the chance to prompt "
                                      "the user for any unsaved files, etc)."))        
        return [self.globalsexplorer_button, self.run_button,
                self.options_button, self.terminate_button, self.kill_button]

    def get_options_menu(self):
        self.interact_action = create_action(self, self.tr("Interact"))
        self.interact_action.setCheckable(True)
        self.debug_action = create_action(self, self.tr("Debug"))
        self.debug_action.setCheckable(True)
        self.args_action = create_action(self, self.tr("Arguments..."),
                                         triggered=self.get_arguments)
        return [self.interact_action, self.debug_action, self.args_action]
        
    def get_shell_widget(self):
        # Globals explorer
        self.globalsexplorer = GlobalsExplorer(self)
        self.connect(self.globalsexplorer, SIGNAL('collapse()'),
                     lambda: self.toggle_globals_explorer(False))
        
        # Shell splitter
        self.splitter = splitter = QSplitter(Qt.Vertical, self)
        self.connect(self.splitter, SIGNAL('splitterMoved(int, int)'),
                     self.splitter_moved)
        splitter.addWidget(self.shell)
        splitter.setCollapsible(0, False)
        splitter.addWidget(self.globalsexplorer)
        splitter.setStretchFactor(0, 2)
        splitter.setStretchFactor(1, 1)
        return splitter
    
    def get_icon(self):
        return get_icon('python.png')

    def set_buttons_runnning_state(self, state):
        ExternalShellBase.set_buttons_runnning_state(self, state)
        for act in (self.interact_action, self.debug_action, self.args_action):
            act.setEnabled(not state)
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
        self.globalsexplorer_button.setEnabled(state)
    
    def create_process(self):
        self.shell.clear()
            
        self.process = QProcess(self)
        self.process.setProcessChannelMode(QProcess.MergedChannels)
        self.connect(self.shell, SIGNAL("wait_for_ready_read()"),
                     lambda: self.process.waitForReadyRead(250))
        
        # Working directory
        if self.wdir is not None:
            self.process.setWorkingDirectory(self.wdir)

        #-------------------------Python specific-------------------------------
        # Python arguments
        p_args = ['-u']
        if self.interact_action.isChecked():
            p_args.append('-i')
        if self.debug_action.isChecked():
            p_args.extend(['-m', 'pdb'])
        p_args.append(self.fname)
        
        env = self.process.systemEnvironment()
        
        # Monitor
        env.append('SHELL_ID=%s' % id(self))
        from spyderlib.widgets.externalshell.monitor import start_server
        server, port = start_server()
        self.notification_thread = server.register(str(id(self)), self)
        self.connect(self.notification_thread, SIGNAL('refresh()'),
                     self.globalsexplorer.refresh_table)
        env.append('SPYDER_PORT=%d' % port)
        
        # Python init commands (interpreter only)
        if self.commands and self.interpreter:
            env.append('PYTHONINITCOMMANDS=%s' % ';'.join(self.commands))
            self.process.setEnvironment(env)
            
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
            p_args.extend( self.arguments.split(' ') )
                        
        self.connect(self.process, SIGNAL("readyReadStandardOutput()"),
                     self.write_output)
        self.connect(self.process, SIGNAL("finished(int,QProcess::ExitStatus)"),
                     self.finished)

        self.connect(self.terminate_button, SIGNAL("clicked()"),
                     self.process.terminate)
        self.connect(self.kill_button, SIGNAL("clicked()"),
                     self.process.kill)
        
        #-------------------------Python specific-------------------------------
        self.process.start(sys.executable, p_args)
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
    def _write_error(self, text, findstr):
        pos = text.find(findstr)
        if pos != -1:
            self.shell.write(text[:pos])
            if text.endswith(">>> "):
                self.shell.write_error(text[pos:-5])
                self.shell.write(text[-5:], flush=True)
            else:
                self.shell.write_error(text[pos:], flush=True)
            return True
        return False
    
    def write_output(self):
        text = self.get_stdout()
        if not self._write_error(text, 'Traceback (most recent call last):') \
           and not self._write_error(text, 'File "<stdin>", line 1'):
            self.shell.write(text)
        QApplication.processEvents()
        
    def send_to_process(self, qstr):
        if not isinstance(qstr, QString):
            qstr = QString(qstr)
        if not qstr.endsWith('\n'):
            qstr.append('\n')
        self.process.write(qstr.toLocal8Bit())
        self.process.waitForBytesWritten(-1)
        
    def keyboard_interrupt(self):
        communicate(self.monitor_socket, "thread.interrupt_main()")
            
#===============================================================================
#    Globals explorer
#===============================================================================
    def toggle_globals_explorer(self, state):
        self.splitter.setSizes([1, 1 if state else 0])
        self.globalsexplorer_button.setChecked(state)
        if state:
            self.globalsexplorer.refresh_table()
        
    def splitter_moved(self, pos, index):
        self.globalsexplorer_button.setChecked( self.splitter.sizes()[1] )
