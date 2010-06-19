# -*- coding: utf-8 -*-
#
# Copyright © 2009 Pierre Raybaut
# Licensed under the terms of the MIT License
# (see spyderlib/__init__.py for details)

"""
spyderlib.widgets.externalshell
===============================

External Shell widget: execute Python script/terminal in a separate process
"""

# pylint: disable-msg=C0103
# pylint: disable-msg=R0903
# pylint: disable-msg=R0911
# pylint: disable-msg=R0201

import sys, os, os.path as osp
from time import time, strftime, gmtime

# Debug
STDOUT = sys.stdout
STDERR = sys.stderr

from PyQt4.QtGui import (QApplication, QWidget, QVBoxLayout, QHBoxLayout, QMenu,
                         QLabel, QInputDialog, QLineEdit, QToolButton)
from PyQt4.QtCore import (QProcess, SIGNAL, QByteArray, QString, QTimer,
                          QStringList, Qt)

# Local imports
from spyderlib.utils.qthelpers import create_toolbutton, translate, add_actions
from spyderlib.config import get_icon, get_conf_path


def add_pathlist_to_PYTHONPATH(env, pathlist):
    assert isinstance(env, QStringList)
    pypath = "PYTHONPATH"
    pathstr = os.pathsep.join(pathlist)
    if os.environ.get(pypath) is not None:
        env.replaceInStrings(pypath+'=', pypath+'='+pathstr+os.pathsep,
                             Qt.CaseSensitive)
        env.append('OLD_PYTHONPATH='+os.environ[pypath])
    else:
        env.append(pypath+'='+pathstr)
    

#TODO: code refactoring/cleaning (together with systemshell.py and pythonshell.py)
class ExternalShellBase(QWidget):
    """External Shell widget: execute Python script in a separate process"""
    SHELL_CLASS = None
    def __init__(self, parent=None, wdir=None, history_filename=None,
                 show_icontext=True):
        QWidget.__init__(self, parent)
        
        self.run_button = None
        self.kill_button = None
        self.options_button = None
        self.icontext_action = None
        
        if wdir is None:
            wdir = osp.dirname(osp.abspath(self.fname))
        self.wdir = wdir if osp.isdir(wdir) else None
        self.arguments = ""
        
        self.shell = self.SHELL_CLASS(parent, get_conf_path(history_filename))
        self.connect(self.shell, SIGNAL("execute(QString)"),
                     self.send_to_process)
        self.connect(self.shell, SIGNAL("keyboard_interrupt()"),
                     self.keyboard_interrupt)
        # Redirecting some SIGNALs:
        self.connect(self.shell, SIGNAL('redirect_stdio(bool)'),
                     lambda state: self.emit(SIGNAL('redirect_stdio(bool)'),
                                             state))
        
        self.state_label = QLabel()
        self.time_label = QLabel()
                
        hlayout = QHBoxLayout()
        hlayout.addWidget(self.state_label)
        hlayout.addStretch(0)
        hlayout.addWidget(self.time_label)
        hlayout.addStretch(0)
        for button in self.get_toolbar_buttons():
            hlayout.addWidget(button)
        
        vlayout = QVBoxLayout()
        vlayout.addLayout(hlayout)
        vlayout.addWidget(self.get_shell_widget())
        self.setLayout(vlayout)
        self.resize(640, 480)
        if parent is None:
            self.setWindowIcon(self.get_icon())
            self.setWindowTitle(translate('ExternalShellBase', "Console"))

        self.t0 = None
        self.timer = QTimer(self)

        self.process = None
        
        self.is_closing = False
        
    def is_running(self):
        if self.process is not None:
            return self.process.state() == QProcess.Running
        
    def get_toolbar_buttons(self):
        if self.run_button is None:
            self.run_button = create_toolbutton(self, get_icon('run.png'),
                              translate('ExternalShellBase', "Run"),
                              tip=translate('ExternalShellBase',
                                            "Run again this program"),
                              triggered=self.start)
        if self.kill_button is None:
            self.kill_button = create_toolbutton(self, get_icon('kill.png'),
                              translate('ExternalShellBase', "Kill"),
                              tip=translate('ExternalShellBase',
                                            "Kills the current process, "
                                            "causing it to exit immediately"))
        buttons = [self.run_button, self.kill_button]
        if self.options_button is None:
            options = self.get_options_menu()
            if options:
                self.options_button = create_toolbutton(self,
                                            text=self.tr("Options"),
                                            icon=get_icon('tooloptions.png'))
                self.options_button.setPopupMode(QToolButton.InstantPopup)
                menu = QMenu(self)
                add_actions(menu, options)
                self.options_button.setMenu(menu)
        if self.options_button is not None:
            buttons.insert(1, self.options_button)
        return buttons
    
    def get_options_menu(self):
        return []
    
    def get_shell_widget(self):
        return self.shell
    
    def get_icon(self):
        raise NotImplementedError
        
    def show_time(self, end=False):
        elapsed_time = time()-self.t0
        if elapsed_time > 24*3600: # More than a day...!
            format = "%d %H:%M:%S"
        else:
            format = "%H:%M:%S"
        if end:
            color = "#AAAAAA"
        else:
            color = "#AA6655"
        text = "<span style=\'color: %s\'><b>%s" \
               "</b></span>" % (color, strftime(format, gmtime(elapsed_time)))
        self.time_label.setText(text)
        
    def closeEvent(self, event):
        if self.process is not None:
            self.is_closing = True
            self.process.kill()
        self.disconnect(self.timer, SIGNAL("timeout()"), self.show_time)
    
    def set_running_state(self, state=True):
        self.set_buttons_runnning_state(state)
        self.shell.setReadOnly(not state)
        if state:
            self.state_label.setText(translate('ExternalShellBase',
                   "<span style=\'color: #44AA44\'><b>Running...</b></span>"))
            self.t0 = time()
            self.connect(self.timer, SIGNAL("timeout()"), self.show_time)
            self.timer.start(1000)        
        else:
            self.state_label.setText(translate('ExternalShellBase',
                                               'Terminated.'))
            self.disconnect(self.timer, SIGNAL("timeout()"), self.show_time)

    def set_buttons_runnning_state(self, state):
        self.run_button.setEnabled(not state)
        self.kill_button.setEnabled(state)
    
    def start(self, ask_for_arguments=False):
        """Start shell"""
        if ask_for_arguments and not self.get_arguments():
            self.set_running_state(False)
            return
        self.create_process()

    def get_arguments(self):
        arguments, valid = QInputDialog.getText(self,
                                  translate('ExternalShellBase', 'Arguments'),
                                  translate('ExternalShellBase',
                                            'Command line arguments:'),
                                  QLineEdit.Normal, self.arguments)
        if valid:
            self.arguments = unicode(arguments)
        return valid
    
    def create_process(self):
        raise NotImplementedError
    
    def finished(self, exit_code, exit_status):
        self.shell.flush()
        self.emit(SIGNAL('finished()'))
        if self.is_closing:
            return
        self.set_running_state(False)
        self.show_time(end=True)
    
#===============================================================================
#    Input/Output
#===============================================================================
    def transcode(self, bytes):
        return unicode( QString.fromLocal8Bit(bytes.data()) )
    
    def get_stdout(self):
        self.process.setReadChannel(QProcess.StandardOutput)
        bytes = QByteArray()
        while self.process.bytesAvailable():
            bytes += self.process.readAllStandardOutput()
        return self.transcode(bytes)
    
    def get_stderr(self):
        self.process.setReadChannel(QProcess.StandardError)
        bytes = QByteArray()
        while self.process.bytesAvailable():
            bytes += self.process.readAllStandardError()
        return self.transcode(bytes)
    
    def write_output(self):
        self.shell.write(self.get_stdout(), flush=True)
        QApplication.processEvents()
        
    def send_to_process(self, qstr):
        raise NotImplementedError
        
    def send_ctrl_to_process(self, letter):
        char = chr("abcdefghijklmnopqrstuvwxyz".index(letter) + 1)
        byte_array = QByteArray()
        byte_array.append(char)
        self.process.write(byte_array)
        self.process.waitForBytesWritten(-1)
        self.shell.write(QString(byte_array), flush=True)
        
    def keyboard_interrupt(self):
        raise NotImplementedError


def test():
    from spyderlib.utils.qthelpers import qapplication
    app = qapplication()
    from spyderlib.widgets.externalshell.pythonshell import ExternalPythonShell
    from spyderlib.widgets.externalshell.systemshell import ExternalSystemShell
    import spyderlib
#    shell = ExternalPythonShell(wdir=osp.dirname(spyderlib.__file__),
#                                ipython=True, stand_alone=True,
#                                arguments="-q4thread -pylab -colors LightBG")
    shell = ExternalPythonShell(wdir=osp.dirname(spyderlib.__file__),
                                interact=True, umd_enabled=True,
                                umd_namelist=['guidata', 'guiqwt'],
                                umd_verbose=True)
#    shell = ExternalSystemShell(wdir=osp.dirname(spyderlib.__file__))
    shell.shell.toggle_wrap_mode(True)
    shell.start(False)
    from PyQt4.QtGui import QFont
    font = QFont("Lucida console")
    font.setPointSize(10)
    shell.shell.set_font(font)
    shell.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    test()