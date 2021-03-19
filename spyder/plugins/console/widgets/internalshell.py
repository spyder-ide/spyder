# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""Internal shell widget : PythonShellWidget + Interpreter"""

# pylint: disable=C0103
# pylint: disable=R0903
# pylint: disable=R0911
# pylint: disable=R0201

#FIXME: Internal shell MT: for i in range(100000): print i -> bug

# Standard library imports
from time import time
import os
import threading

# Third party imports
from qtpy.QtCore import QEventLoop, QObject, Signal, Slot
from qtpy.QtWidgets import QMessageBox
from spyder_kernels.utils.dochelpers import (getargtxt, getdoc, getobjdir,
                                             getsource)

# Local imports
from spyder import get_versions
from spyder.api.translations import get_translation
from spyder.plugins.console.utils.interpreter import Interpreter
from spyder.py3compat import (builtins, to_binary_string,
                              to_text_string)
from spyder.utils.icon_manager import ima
from spyder.utils import programs
from spyder.utils.misc import get_error_match, getcwd_or_home
from spyder.utils.qthelpers import create_action
from spyder.plugins.console.widgets.shell import PythonShellWidget
from spyder.plugins.variableexplorer.widgets.objecteditor import oedit
from spyder.config.base import get_conf_path, get_debug_level


# Localization
_ = get_translation('spyder')
builtins.oedit = oedit


def create_banner(message):
    """Create internal shell banner"""
    if message is None:
        versions = get_versions()
        return 'Python %s %dbits [%s]'\
               % (versions['python'], versions['bitness'], versions['system'])
    else:
        return message


class SysOutput(QObject):
    """Handle standard I/O queue"""
    data_avail = Signal()

    def __init__(self):
        QObject.__init__(self)
        self.queue = []
        self.lock = threading.Lock()

    def write(self, val):
        self.lock.acquire()
        self.queue.append(val)
        self.lock.release()
        self.data_avail.emit()

    def empty_queue(self):
        self.lock.acquire()
        s = "".join(self.queue)
        self.queue = []
        self.lock.release()
        return s

    # We need to add this method to fix spyder-ide/spyder#1789.
    def flush(self):
        pass

    # This is needed to fix spyder-ide/spyder#2984.
    @property
    def closed(self):
        return False

class WidgetProxyData(object):
    pass

class WidgetProxy(QObject):
    """Handle Shell widget refresh signal"""

    sig_new_prompt = Signal(str)
    sig_set_readonly = Signal(bool)
    sig_edit = Signal(str, bool)
    sig_wait_input = Signal(str)

    def __init__(self, input_condition):
        QObject.__init__(self)

        # External editor
        self._gotoline = None
        self._path = None
        self.input_data = None
        self.input_condition = input_condition

    def new_prompt(self, prompt):
        self.sig_new_prompt.emit(prompt)

    def set_readonly(self, state):
        self.sig_set_readonly.emit(state)

    def edit(self, filename, external_editor=False):
        self.sig_edit.emit(filename, external_editor)

    def data_available(self):
        """Return True if input data is available"""
        return self.input_data is not WidgetProxyData

    def wait_input(self, prompt=''):
        self.input_data = WidgetProxyData
        self.sig_wait_input.emit(prompt)

    def end_input(self, cmd):
        self.input_condition.acquire()
        self.input_data = cmd
        self.input_condition.notify()
        self.input_condition.release()


class InternalShell(PythonShellWidget):
    """Shell base widget: link between PythonShellWidget and Interpreter"""

    # --- Signals

    # This signal is emitted when the buffer is flushed
    sig_refreshed = Signal()

    # Request to show a status message on the main window
    sig_show_status_requested = Signal(str)

    # This signal emits a parsed error traceback text so we can then
    # request opening the file that traceback comes from in the Editor.
    sig_go_to_error_requested = Signal(str)

    # TODO: I think this is not being used now?
    sig_focus_changed = Signal()

    def __init__(self, parent=None, namespace=None, commands=[], message=None,
                 max_line_count=300, exitfunc=None, profile=False,
                 multithreaded=True):
        super().__init__(parent, get_conf_path('history_internal.py'),
                         profile=profile)

        self.multithreaded = multithreaded
        self.setMaximumBlockCount(max_line_count)

        # Allow raw_input support:
        self.input_loop = None
        self.input_mode = False

        # KeyboardInterrupt support
        self.interrupted = False  # used only for not-multithreaded mode
        self.sig_keyboard_interrupt.connect(self.keyboard_interrupt)

        # Code completion / calltips
        # keyboard events management
        self.eventqueue = []

        # Init interpreter
        self.exitfunc = exitfunc
        self.commands = commands
        self.message = message
        self.interpreter = None

        # Clear status bar
        self.sig_show_status_requested.emit('')

        # Embedded shell -- requires the monitor (which installs the
        # 'open_in_spyder' function in builtins)
        if hasattr(builtins, 'open_in_spyder'):
            self.sig_go_to_error_requested.connect(
                self.open_with_external_spyder)

    #------ Interpreter
    def start_interpreter(self, namespace):
        """Start Python interpreter."""
        self.clear()

        if self.interpreter is not None:
            self.interpreter.closing()

        self.interpreter = Interpreter(namespace, self.exitfunc,
                                       SysOutput, WidgetProxy,
                                       get_debug_level())
        self.interpreter.stdout_write.data_avail.connect(self.stdout_avail)
        self.interpreter.stderr_write.data_avail.connect(self.stderr_avail)
        self.interpreter.widget_proxy.sig_set_readonly.connect(self.setReadOnly)
        self.interpreter.widget_proxy.sig_new_prompt.connect(self.new_prompt)
        self.interpreter.widget_proxy.sig_edit.connect(self.edit_script)
        self.interpreter.widget_proxy.sig_wait_input.connect(self.wait_input)

        if self.multithreaded:
            self.interpreter.start()

        # Interpreter banner
        banner = create_banner(self.message)
        self.write(banner, prompt=True)

        # Initial commands
        for cmd in self.commands:
            self.run_command(cmd, history=False, new_prompt=False)

        # First prompt
        self.new_prompt(self.interpreter.p1)
        self.sig_refreshed.emit()

        return self.interpreter

    def exit_interpreter(self):
        """Exit interpreter"""
        self.interpreter.exit_flag = True
        if self.multithreaded:
            self.interpreter.stdin_write.write(to_binary_string('\n'))
        self.interpreter.restore_stds()

    def edit_script(self, filename, external_editor):
        filename = to_text_string(filename)
        if external_editor:
            self.external_editor(filename)
        else:
            self.parent().edit_script(filename)

    def stdout_avail(self):
        """Data is available in stdout, let's empty the queue and write it!"""
        data = self.interpreter.stdout_write.empty_queue()
        if data:
            self.write(data)

    def stderr_avail(self):
        """Data is available in stderr, let's empty the queue and write it!"""
        data = self.interpreter.stderr_write.empty_queue()
        if data:
            self.write(data, error=True)
            self.flush(error=True)


    #------Raw input support
    def wait_input(self, prompt=''):
        """Wait for input (raw_input support)"""
        self.new_prompt(prompt)
        self.setFocus()
        self.input_mode = True
        self.input_loop = QEventLoop()
        self.input_loop.exec_()
        self.input_loop = None

    def end_input(self, cmd):
        """End of wait_input mode"""
        self.input_mode = False
        self.input_loop.exit()
        self.interpreter.widget_proxy.end_input(cmd)


    #----- Menus, actions, ...
    def setup_context_menu(self):
        """Reimplement PythonShellWidget method"""
        PythonShellWidget.setup_context_menu(self)
        self.help_action = create_action(self, _("Help..."),
                           icon=ima.icon('DialogHelpButton'),
                           triggered=self.help)
        self.menu.addAction(self.help_action)

    @Slot()
    def help(self):
        """Help on Spyder console"""
        QMessageBox.about(self, _("Help"),
                          """<b>%s</b>
                          <p><i>%s</i><br>    edit foobar.py
                          <p><i>%s</i><br>    xedit foobar.py
                          <p><i>%s</i><br>    run foobar.py
                          <p><i>%s</i><br>    clear x, y
                          <p><i>%s</i><br>    !ls
                          <p><i>%s</i><br>    object?
                          <p><i>%s</i><br>    result = oedit(object)
                          """ % (_('Shell special commands:'),
                                 _('Internal editor:'),
                                 _('External editor:'),
                                 _('Run script:'),
                                 _('Remove references:'),
                                 _('System commands:'),
                                 _('Python help:'),
                                 _('GUI-based editor:')))


    #------ External editing
    def open_with_external_spyder(self, text):
        """Load file in external Spyder's editor, if available
        This method is used only for embedded consoles
        (could also be useful if we ever implement the magic %edit command)"""
        match = get_error_match(to_text_string(text))
        if match:
            fname, lnb = match.groups()
            builtins.open_in_spyder(fname, int(lnb))

    def set_external_editor(self, path, gotoline):
        """Set external editor path and gotoline option."""
        self._path = path
        self._gotoline = gotoline

    def external_editor(self, filename, goto=-1):
        """
        Edit in an external editor.

        Recommended: SciTE (e.g. to go to line where an error did occur).
        """
        editor_path = self._path
        goto_option = self._gotoline

        if os.path.isfile(editor_path):
            try:
                args = [filename]
                if goto > 0 and goto_option:
                    args.append('%s%d'.format(goto_option, goto))

                programs.run_program(editor_path, args)
            except OSError:
                self.write_error("External editor was not found:"
                                 " %s\n" % editor_path)

    #------ I/O
    def flush(self, error=False, prompt=False):
        """Reimplement ShellBaseWidget method"""
        PythonShellWidget.flush(self, error=error, prompt=prompt)
        if self.interrupted:
            self.interrupted = False
            raise KeyboardInterrupt


    #------ Clear terminal
    def clear_terminal(self):
        """Reimplement ShellBaseWidget method"""
        self.clear()
        self.new_prompt(self.interpreter.p2 if self.interpreter.more else self.interpreter.p1)


    #------ Keyboard events
    def on_enter(self, command):
        """on_enter"""
        if self.profile:
            # Simple profiling test
            t0 = time()
            for _ in range(10):
                self.execute_command(command)
            self.insert_text(u"\n<Δt>=%dms\n" % (1e2*(time()-t0)))
            self.new_prompt(self.interpreter.p1)
        else:
            self.execute_command(command)
        self.__flush_eventqueue()

    def keyPressEvent(self, event):
        """
        Reimplement Qt Method
        Enhanced keypress event handler
        """
        if self.preprocess_keyevent(event):
            # Event was accepted in self.preprocess_keyevent
            return
        self.postprocess_keyevent(event)

    def __flush_eventqueue(self):
        """Flush keyboard event queue"""
        while self.eventqueue:
            past_event = self.eventqueue.pop(0)
            self.postprocess_keyevent(past_event)

    #------ Command execution
    def keyboard_interrupt(self):
        """Simulate keyboard interrupt"""
        if self.multithreaded:
            self.interpreter.raise_keyboard_interrupt()
        else:
            if self.interpreter.more:
                self.write_error("\nKeyboardInterrupt\n")
                self.interpreter.more = False
                self.new_prompt(self.interpreter.p1)
                self.interpreter.resetbuffer()
            else:
                self.interrupted = True

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
            self.execute_command(line+"\n")
            self.flush()

    def execute_command(self, cmd):
        """
        Execute a command
        cmd: one-line command only, with '\n' at the end
        """
        if self.input_mode:
            self.end_input(cmd)
            return
        if cmd.endswith('\n'):
            cmd = cmd[:-1]
        # cls command
        if cmd == 'cls':
            self.clear_terminal()
            return
        self.run_command(cmd)

    def run_command(self, cmd, history=True, new_prompt=True):
        """Run command in interpreter"""
        if not cmd:
            cmd = ''
        else:
            if history:
                self.add_to_history(cmd)
        if not self.multithreaded:
            if 'input' not in cmd:
                self.interpreter.stdin_write.write(
                                                to_binary_string(cmd + '\n'))
                self.interpreter.run_line()
                self.sig_refreshed.emit()
            else:
                self.write(_('In order to use commands like "raw_input" '
                             'or "input" run Spyder with the multithread '
                             'option (--multithread) from a system terminal'),
                           error=True)
        else:
            self.interpreter.stdin_write.write(to_binary_string(cmd + '\n'))


    #------ Code completion / Calltips
    def _eval(self, text):
        """Is text a valid object?"""
        return self.interpreter.eval(text)

    def get_dir(self, objtxt):
        """Return dir(object)"""
        obj, valid = self._eval(objtxt)
        if valid:
            return getobjdir(obj)

    def get_globals_keys(self):
        """Return shell globals() keys"""
        return list(self.interpreter.namespace.keys())

    def get_cdlistdir(self):
        """Return shell current directory list dir"""
        return os.listdir(getcwd_or_home())

    def iscallable(self, objtxt):
        """Is object callable?"""
        obj, valid = self._eval(objtxt)
        if valid:
            return callable(obj)

    def get_arglist(self, objtxt):
        """Get func/method argument list"""
        obj, valid = self._eval(objtxt)
        if valid:
            return getargtxt(obj)

    def get__doc__(self, objtxt):
        """Get object __doc__"""
        obj, valid = self._eval(objtxt)
        if valid:
            return obj.__doc__

    def get_doc(self, objtxt):
        """Get object documentation dictionary"""
        obj, valid = self._eval(objtxt)
        if valid:
            return getdoc(obj)

    def get_source(self, objtxt):
        """Get object source"""
        obj, valid = self._eval(objtxt)
        if valid:
            return getsource(obj)

    def is_defined(self, objtxt, force_import=False):
        """Return True if object is defined"""
        return self.interpreter.is_defined(objtxt, force_import)
