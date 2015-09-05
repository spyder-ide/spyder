# -*- coding: utf-8 -*-
#
# Copyright © 2010 Pierre Raybaut
# Licensed under the terms of the MIT License
# (see spyderlib/__init__.py for details)

# pylint: disable=C0103
# pylint: disable=R0903
# pylint: disable=R0911
# pylint: disable=R0201

import sys
import os
import os.path as osp
from time import time, strftime, gmtime

from spyderlib.qt.QtGui import (QApplication, QWidget, QVBoxLayout,
                                QHBoxLayout, QMenu, QLabel, QInputDialog,
                                QLineEdit, QToolButton)
from spyderlib.qt.QtCore import (QProcess, SIGNAL, QByteArray, QTimer, Qt,
                                 QTextCodec)
LOCALE_CODEC = QTextCodec.codecForLocale()

# Local imports
from spyderlib.utils.qthelpers import (get_icon, create_toolbutton,
                                       create_action, add_actions)
from spyderlib.baseconfig import get_conf_path, _
from spyderlib.py3compat import is_text_string, to_text_string


def add_pathlist_to_PYTHONPATH(env, pathlist, drop_env=False):
    # PyQt API 1/2 compatibility-related tests:
    assert isinstance(env, list)
    assert all([is_text_string(path) for path in env])
    
    pypath = "PYTHONPATH"
    pathstr = os.pathsep.join(pathlist)
    if os.environ.get(pypath) is not None and not drop_env:
        for index, var in enumerate(env[:]):
            if var.startswith(pypath+'='):
                env[index] = var.replace(pypath+'=',
                                         pypath+'='+pathstr+os.pathsep)
        env.append('OLD_PYTHONPATH='+os.environ[pypath])
    else:
        env.append(pypath+'='+pathstr)
    

#TODO: code refactoring/cleaning (together with systemshell.py and pythonshell.py)
class ExternalShellBase(QWidget):
    """External Shell widget: execute Python script in a separate process"""
    SHELL_CLASS = None
    def __init__(self, parent=None, fname=None, wdir=None,
                 history_filename=None, show_icontext=True,
                 light_background=True, menu_actions=None,
                 show_buttons_inside=True, show_elapsed_time=True):
        QWidget.__init__(self, parent)
        
        self.menu_actions = menu_actions
        
        self.run_button = None
        self.kill_button = None
        self.options_button = None
        self.icontext_action = None

        self.show_elapsed_time = show_elapsed_time
        
        self.fname = fname
        if wdir is None:
            wdir = osp.dirname(osp.abspath(fname))
        self.wdir = wdir if osp.isdir(wdir) else None
        self.arguments = ""
        
        self.shell = self.SHELL_CLASS(parent, get_conf_path(history_filename))
        self.shell.set_light_background(light_background)
        self.connect(self.shell, SIGNAL("execute(QString)"),
                     self.send_to_process)
        self.connect(self.shell, SIGNAL("keyboard_interrupt()"),
                     self.keyboard_interrupt)
        # Redirecting some SIGNALs:
        self.connect(self.shell, SIGNAL('redirect_stdio(bool)'),
                     lambda state: self.emit(SIGNAL('redirect_stdio(bool)'),
                                             state))
        
        self.state_label = None
        self.time_label = None
                
        vlayout = QVBoxLayout()
        toolbar_buttons = self.get_toolbar_buttons()
        if show_buttons_inside:
            self.state_label = QLabel()
            hlayout = QHBoxLayout()
            hlayout.addWidget(self.state_label)
            hlayout.addStretch(0)
            hlayout.addWidget(self.create_time_label())
            hlayout.addStretch(0)
            for button in toolbar_buttons:
                hlayout.addWidget(button)
            vlayout.addLayout(hlayout)
        else:
            vlayout.setContentsMargins(0, 0, 0, 0)
        vlayout.addWidget(self.get_shell_widget())
        self.setLayout(vlayout)
        self.resize(640, 480)
        if parent is None:
            self.setWindowIcon(self.get_icon())
            self.setWindowTitle(_("Console"))

        self.t0 = None
        self.timer = QTimer(self)

        self.process = None
        
        self.is_closing = False

        if show_buttons_inside:
            self.update_time_label_visibility()
        
    def set_elapsed_time_visible(self, state):
        self.show_elapsed_time = state
        if self.time_label is not None:
            self.time_label.setVisible(state)
            
    def create_time_label(self):
        """Create elapsed time label widget (if necessary) and return it"""
        if self.time_label is None:
            self.time_label = QLabel()
        return self.time_label
    
    def update_time_label_visibility(self):
        self.time_label.setVisible(self.show_elapsed_time)
        
    def is_running(self):
        if self.process is not None:
            return self.process.state() == QProcess.Running
        
    def get_toolbar_buttons(self):
        if self.run_button is None:
            self.run_button = create_toolbutton(self, text=_("Run"),
                                             icon=get_icon('run.png'),
                                             tip=_("Run again this program"),
                                             triggered=self.start_shell)
        if self.kill_button is None:
            self.kill_button = create_toolbutton(self, text=_("Kill"),
                                     icon=get_icon('kill.png'),
                                     tip=_("Kills the current process, "
                                           "causing it to exit immediately"))
        buttons = [self.run_button]
        if self.options_button is None:
            options = self.get_options_menu()
            if options:
                self.options_button = create_toolbutton(self, text=_("Options"),
                                            icon=get_icon('tooloptions.png'))
                self.options_button.setPopupMode(QToolButton.InstantPopup)
                menu = QMenu(self)
                add_actions(menu, options)
                self.options_button.setMenu(menu)
        if self.options_button is not None:
            buttons.append(self.options_button)
        buttons.append(self.kill_button)
        return buttons
            
    def set_icontext_visible(self, state):
        """Set icon text visibility"""
        for widget in self.get_toolbar_buttons():
            if state:
                widget.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
            else:
                widget.setToolButtonStyle(Qt.ToolButtonIconOnly)
    
    def get_options_menu(self):
        self.show_time_action = create_action(self, _("Show elapsed time"),
                                          toggled=self.set_elapsed_time_visible)
        self.show_time_action.setChecked(self.show_elapsed_time)
        actions = [self.show_time_action]
        if self.menu_actions is not None:
            actions += [None]+self.menu_actions
        return actions
    
    def get_shell_widget(self):
        return self.shell
    
    def get_icon(self):
        raise NotImplementedError
        
    def show_time(self, end=False):
        if self.time_label is None:
            return
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
            self.process.waitForFinished(100)
        self.disconnect(self.timer, SIGNAL("timeout()"), self.show_time)
    
    def set_running_state(self, state=True):
        self.set_buttons_runnning_state(state)
        self.shell.setReadOnly(not state)
        if state:
            if self.state_label is not None:
                self.state_label.setText(_(
                   "<span style=\'color: #44AA44\'><b>Running...</b></span>"))
            self.t0 = time()
            self.connect(self.timer, SIGNAL("timeout()"), self.show_time)
            self.timer.start(1000)        
        else:
            if self.state_label is not None:
                self.state_label.setText(_('Terminated.'))
            self.disconnect(self.timer, SIGNAL("timeout()"), self.show_time)

    def set_buttons_runnning_state(self, state):
        self.run_button.setVisible(not state and not self.is_ipykernel)
        self.kill_button.setVisible(state)
    
    def start_shell(self, ask_for_arguments=False):
        """Start shell"""
        if ask_for_arguments and not self.get_arguments():
            self.set_running_state(False)
            return
        try:
            self.disconnect(self.terminate_button, SIGNAL("clicked()"),
                            self.process.terminate)
            self.disconnect(self.kill_button, SIGNAL("clicked()"),
                            self.process.terminate)
        except:
            pass
        self.create_process()

    def get_arguments(self):
        arguments, valid = QInputDialog.getText(self, _('Arguments'),
                                                _('Command line arguments:'),
                                                QLineEdit.Normal,
                                                self.arguments)
        if valid:
            self.arguments = to_text_string(arguments)
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
    def transcode(self, qba):
        try:
            return to_text_string(qba.data(), 'utf8')
        except UnicodeDecodeError:
            return qba.data()
    
    def get_stdout(self):
        self.process.setReadChannel(QProcess.StandardOutput)
        qba = QByteArray()
        while self.process.bytesAvailable():
            qba += self.process.readAllStandardOutput()
        return self.transcode(qba)
    
    def get_stderr(self):
        self.process.setReadChannel(QProcess.StandardError)
        qba = QByteArray()
        while self.process.bytesAvailable():
            qba += self.process.readAllStandardError()
        return self.transcode(qba)
    
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
        self.shell.write(LOCALE_CODEC.toUnicode(byte_array), flush=True)
        
    def keyboard_interrupt(self):
        raise NotImplementedError


def test():
    from spyderlib.utils.qthelpers import qapplication
    app = qapplication()
    from spyderlib.widgets.externalshell.pythonshell import ExternalPythonShell
    from spyderlib.widgets.externalshell.systemshell import ExternalSystemShell
    import spyderlib
    from spyderlib.plugins.variableexplorer import VariableExplorer
    settings = VariableExplorer.get_settings()
    shell = ExternalPythonShell(wdir=osp.dirname(spyderlib.__file__),
                                ipykernel=True, stand_alone=settings,
                                arguments="-q4thread -pylab -colors LightBG",
                                light_background=False)
#    shell = ExternalPythonShell(wdir=osp.dirname(spyderlib.__file__),
#                                interact=True, umr_enabled=True,
#                                stand_alone=settings,
#                                umr_namelist=['guidata', 'guiqwt'],
#                                umr_verbose=True, light_background=False)
#    shell = ExternalSystemShell(wdir=osp.dirname(spyderlib.__file__),
#                                light_background=False)
    shell.shell.toggle_wrap_mode(True)
    shell.start_shell(False)
    from spyderlib.qt.QtGui import QFont
    font = QFont("Lucida console")
    font.setPointSize(10)
    shell.shell.set_font(font)
    shell.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    test()