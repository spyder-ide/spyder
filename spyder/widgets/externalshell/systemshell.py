# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""External System Shell widget: execute terminal in a separate process"""

# Standard library imports
import os
import sys

# Third party imports
from qtpy.QtCore import QProcess, QProcessEnvironment, QTextCodec, Signal
from qtpy.QtWidgets import QMessageBox

# Local imports
from spyder.config.base import _
from spyder.py3compat import is_text_string, to_text_string
from spyder.utils import icon_manager as ima
from spyder.utils.misc import add_pathlist_to_PYTHONPATH
from spyder.widgets.externalshell.baseshell import ExternalShellBase
from spyder.widgets.shell import TerminalWidget


LOCALE_CODEC = QTextCodec.codecForLocale()
CP850_CODEC = QTextCodec.codecForName('cp850')


class ExternalSystemShell(ExternalShellBase):
    """External Shell widget: execute Python script in a separate process"""
    SHELL_CLASS = TerminalWidget
    started = Signal()
    
    def __init__(self, parent=None, wdir=None, path=[], light_background=True,
                 menu_actions=None, show_buttons_inside=True,
                 show_elapsed_time=True):
        ExternalShellBase.__init__(self, parent=parent, fname=None, wdir=wdir,
                                   history_filename='.history',
                                   light_background=light_background,
                                   menu_actions=menu_actions,
                                   show_buttons_inside=show_buttons_inside,
                                   show_elapsed_time=show_elapsed_time)

        # Additional python path list
        self.path = path

        # For compatibility with the other shells that can live in the external
        # console
        self.connection_file = None

    def get_icon(self):
        return ima.icon('cmdprompt')

    def finish_process(self):
        while not self.process.waitForFinished(100):
            self.process.kill();

    def create_process(self):
        self.shell.clear()

        self.process = QProcess(self)
        self.process.setProcessChannelMode(QProcess.MergedChannels)

        # PYTHONPATH (in case we use Python in this terminal, e.g. py2exe)
        env = [to_text_string(_path)
               for _path in self.process.systemEnvironment()]

        processEnvironment = QProcessEnvironment()
        for envItem in env:
            envName, separator, envValue = envItem.partition('=')
            processEnvironment.insert(envName, envValue)

        add_pathlist_to_PYTHONPATH(env, self.path)
        self.process.setProcessEnvironment(processEnvironment)                   

        
        # Working directory
        if self.wdir is not None:
            self.process.setWorkingDirectory(self.wdir)
            
        # Shell arguments
        if os.name == 'nt':
            p_args = ['/Q']
        else:
            p_args = ['-i']
            
        if self.arguments:
            p_args.extend( shell_split(self.arguments) )
        
        self.process.readyReadStandardOutput.connect(self.write_output)
        self.process.finished.connect(self.finished)
        self.kill_button.clicked.connect(self.process.kill)
        
        if os.name == 'nt':
            self.process.start('cmd.exe', p_args)
        else:
            # Using bash:
            self.process.start('bash', p_args)
            self.send_to_process('PS1="\\u@\\h:\\w> "\n')
            
        running = self.process.waitForStarted()
        self.set_running_state(running)
        if not running:
            QMessageBox.critical(self, _("Error"),
                                 _("Process failed to start"))
        else:
            self.shell.setFocus()
            self.started.emit()
            
        return self.process
    
#===============================================================================
#    Input/Output
#===============================================================================
    def transcode(self, qba):
        if os.name == 'nt':
            return to_text_string( CP850_CODEC.toUnicode(qba.data()) )
        else:
            return ExternalShellBase.transcode(self, qba)
    
    def send_to_process(self, text):
        if not is_text_string(text):
            text = to_text_string(text)
        if text[:-1] in ["clear", "cls", "CLS"]:
            self.shell.clear()
            self.send_to_process(os.linesep)
            return
        if not text.endswith('\n'):
            text += '\n'
        if os.name == 'nt':
            self.process.write(text.encode('cp850'))
        else:
            self.process.write(LOCALE_CODEC.fromUnicode(text))
        self.process.waitForBytesWritten(-1)
        
    def keyboard_interrupt(self):
        # This does not work on Windows:
        # (unfortunately there is no easy way to send a Ctrl+C to cmd.exe)
        self.send_ctrl_to_process('c')

#        # The following code will soon be removed:
#        # (last attempt to send a Ctrl+C on Windows)
#        if os.name == 'nt':
#            pid = int(self.process.pid())
#            import ctypes, win32api, win32con
#            class _PROCESS_INFORMATION(ctypes.Structure):
#                _fields_ = [("hProcess", ctypes.c_int),
#                            ("hThread", ctypes.c_int),
#                            ("dwProcessID", ctypes.c_int),
#                            ("dwThreadID", ctypes.c_int)]
#            x = ctypes.cast( ctypes.c_void_p(pid),
#                             ctypes.POINTER(_PROCESS_INFORMATION) )
#            win32api.GenerateConsoleCtrlEvent(win32con.CTRL_C_EVENT,
#                                              x.dwProcessID)
#        else:
#            self.send_ctrl_to_process('c')


#==============================================================================
# Tests
#==============================================================================
def test():
    import os.path as osp
    from spyder.utils.qthelpers import qapplication
    app = qapplication(test_time=5)
    shell = ExternalSystemShell(wdir=osp.dirname(__file__),
                                light_background=False)

    app.aboutToQuit.connect(shell.finish_process)

    from qtpy.QtGui import QFont
    font = QFont()
    font.setPointSize(10)
    shell.shell.set_font(font)

    shell.shell.toggle_wrap_mode(True)
    shell.start_shell(False)
    shell.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    test()