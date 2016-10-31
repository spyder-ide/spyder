# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

# pylint: disable=C0103
# pylint: disable=R0903
# pylint: disable=R0911
# pylint: disable=R0201

# Standard library imports
from time import time, strftime, gmtime
import os.path as osp

# Third party imports
from qtpy.QtCore import (QByteArray, QProcess, Qt, QTextCodec, QTimer,
                         Signal, Slot, QMutex)
from qtpy.QtWidgets import (QHBoxLayout, QInputDialog, QLabel, QLineEdit,
                            QMenu, QToolButton, QVBoxLayout, QWidget)

# Local imports
from spyder.config.base import _, get_conf_path
from spyder.py3compat import to_text_string
from spyder.utils import icon_manager as ima
from spyder.utils.qthelpers import (add_actions, create_action,
                                    create_toolbutton)


LOCALE_CODEC = QTextCodec.codecForLocale()


#TODO: code refactoring/cleaning (together with systemshell.py and pythonshell.py)
class ExternalShellBase(QWidget):
    """External Shell widget: execute Python script in a separate process"""
    SHELL_CLASS = None
    redirect_stdio = Signal(bool)
    sig_finished = Signal()
    
    def __init__(self, parent=None, fname=None, wdir=None,
                 history_filename=None, show_icontext=True,
                 light_background=True, menu_actions=None,
                 show_buttons_inside=True, show_elapsed_time=True):
        QWidget.__init__(self, parent)
        
        self.menu_actions = menu_actions
        self.write_lock = QMutex()
        self.buffer_lock = QMutex()
        self.buffer = []
        
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
        self.shell.execute.connect(self.send_to_process)
        self.shell.sig_keyboard_interrupt.connect(self.keyboard_interrupt)
        # Redirecting some SIGNALs:
        self.shell.redirect_stdio.connect(
                     lambda state: self.redirect_stdio.emit(state))
        
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

    @Slot(bool)
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
                                             icon=ima.icon('run'),
                                             tip=_("Run again this program"),
                                             triggered=self.start_shell)
        if self.kill_button is None:
            self.kill_button = create_toolbutton(self, text=_("Kill"),
                                     icon=ima.icon('kill'),
                                     tip=_("Kills the current process, "
                                           "causing it to exit immediately"))
        buttons = [self.run_button]
        if self.options_button is None:
            options = self.get_options_menu()
            if options:
                self.options_button = create_toolbutton(self, text=_('Options'),
                                            icon=ima.icon('tooloptions'))
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

        try:
            self.timer.timeout.disconnect(self.show_time)
        except (RuntimeError, TypeError):
            pass
    
    def set_running_state(self, state=True):
        self.set_buttons_runnning_state(state)
        self.shell.setReadOnly(not state)
        if state:
            if self.state_label is not None:
                self.state_label.setText(_(
                   "<span style=\'color: #44AA44\'><b>Running...</b></span>"))
            self.t0 = time()
            self.timer.timeout.connect(self.show_time)
            self.timer.start(1000)        
        else:
            if self.state_label is not None:
                self.state_label.setText(_('Terminated.'))
            try:
                self.timer.timeout.disconnect(self.show_time)
            except (RuntimeError, TypeError):
                pass

    def set_buttons_runnning_state(self, state):
        self.run_button.setVisible(not state)
        self.kill_button.setVisible(state)

    @Slot(bool)
    def start_shell(self, ask_for_arguments=False):
        """Start shell"""
        if ask_for_arguments and not self.get_arguments():
            self.set_running_state(False)
            return
        try:
            self.terminate_button.clicked.disconnect(self.process.terminate)
            self.kill_button.clicked.disconnect(self.process.terminate)
        except (AttributeError, RuntimeError, TypeError):
            pass
        self.create_process()

    @Slot()
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
        self.sig_finished.emit()
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
        # if we are already writing something else,
        # store the present message in a buffer
        if not self.write_lock.tryLock():
            self.buffer_lock.lock()
            self.buffer.append(self.get_stdout())
            self.buffer_lock.unlock()

            if not self.write_lock.tryLock():
                return

        self.shell.write(self.get_stdout(), flush=True)

        while True:
            self.buffer_lock.lock()
            messages = self.buffer
            self.buffer = []

            if not messages:
                self.write_lock.unlock()
                self.buffer_lock.unlock()
                return

            self.buffer_lock.unlock()
            self.shell.write("\n".join(messages), flush=True)

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
