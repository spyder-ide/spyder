# -*- coding: utf-8 -*-
#
# Copyright © 2009-2010 Pierre Raybaut
# Licensed under the terms of the MIT License
# (see spyderlib/__init__.py for details)

"""Internal shell widget : PythonShellWidget + Interpreter"""

# pylint: disable=C0103
# pylint: disable=R0903
# pylint: disable=R0911
# pylint: disable=R0201

#FIXME: Internal shell MT: for i in range(100000): print i -> bug

#----Builtins
import __builtin__
try:
    from IPython.deep_reload import reload
    __builtin__.dreload = reload
except ImportError:
    pass
from spyderlib.widgets.objecteditor import oedit
__builtin__.oedit = oedit


import sys, os, threading
from time import time
from subprocess import Popen

STDOUT = sys.stdout

from spyderlib.qt.QtGui import QMessageBox
from spyderlib.qt.QtCore import SIGNAL, QObject

# Local import
from spyderlib.utils.qthelpers import create_action, get_std_icon
from spyderlib.interpreter import Interpreter
from spyderlib.utils.dochelpers import getargtxt, getsource, getdoc, getobjdir
#TODO: remove the CONF object and make it work anyway
# In fact, this 'CONF' object has nothing to do in package spyderlib.widgets
# which should not contain anything directly related to Spyder's main app
from spyderlib.baseconfig import get_conf_path, _
from spyderlib.config import CONF
from spyderlib.widgets.shell import PythonShellWidget


def create_banner(moreinfo, message=''):
    """Create shell banner"""
    if message:
        message = '\n' + message + '\n'
    return 'Python %s on %s\n' % (sys.version, sys.platform) + \
            moreinfo+'\n' + message + '\n'


class SysOutput(QObject):
    """Handle standard I/O queue"""
    def __init__(self):
        QObject.__init__(self)
        self.queue = []
        self.lock = threading.Lock()
        
    def write(self, val):
        self.lock.acquire()
        self.queue.append(val)
        self.lock.release()
        self.emit(SIGNAL("void data_avail()"))

    def empty_queue(self):
        self.lock.acquire()
        s = "".join(self.queue)
        self.queue = []
        self.lock.release()
        return s

class WidgetProxy(QObject):
    """Handle Shell widget refresh signal"""
    def __init__(self):
        QObject.__init__(self)
        
    def new_prompt(self, prompt):
        self.emit(SIGNAL("new_prompt(QString)"), prompt)
        
    def set_readonly(self, state):
        self.emit(SIGNAL("set_readonly(bool)"), state)
        
    def edit(self, filename, external_editor=False):
        self.emit(SIGNAL("edit(QString,bool)"), filename, external_editor)


class InternalShell(PythonShellWidget):
    """Shell base widget: link between PythonShellWidget and Interpreter"""
    def __init__(self, parent=None, namespace=None, commands=[], message="",
                 max_line_count=300, font=None, debug=False, exitfunc=None,
                 profile=False, multithreaded=True, light_background=True):
        PythonShellWidget.__init__(self, parent,
                                   get_conf_path('.history_internal.py'),
                                   debug, profile)
        
        self.set_light_background(light_background)
        
        self.multithreaded = multithreaded
        
        self.setMaximumBlockCount(max_line_count)
        
        if font is not None:
            self.set_font(font)
        
        # KeyboardInterrupt support
        self.interrupted = False # used only for not-multithreaded mode
        self.connect(self, SIGNAL("keyboard_interrupt()"),
                     self.keyboard_interrupt)
        
        # Code completion / calltips
        getcfg = lambda option: CONF.get('internal_console', option)
        case_sensitive = getcfg('codecompletion/case_sensitive')
        show_single = getcfg('codecompletion/show_single')
        self.set_codecompletion_case(case_sensitive)
        self.set_codecompletion_single(show_single)
        
        # keyboard events management
        self.eventqueue = []

        # Init interpreter
        self.exitfunc = exitfunc
        self.commands = commands
        self.message = message
        self.interpreter = None
        self.start_interpreter(namespace)
        
        # Clear status bar
        self.emit(SIGNAL("status(QString)"), '')
                
                
    #------ Interpreter
    def start_interpreter(self, namespace):
        """Start Python interpreter"""
        self.clear()
        
        if self.interpreter is not None:
            self.interpreter.closing()
        self.interpreter = Interpreter(namespace, self.exitfunc,
                                       SysOutput, WidgetProxy, self.debug)
        self.connect(self.interpreter.stdout_write,
                     SIGNAL("void data_avail()"), self.stdout_avail)
        self.connect(self.interpreter.stderr_write,
                     SIGNAL("void data_avail()"), self.stderr_avail)
        self.connect(self.interpreter.widget_proxy,
                     SIGNAL("set_readonly(bool)"), self.setReadOnly)
        self.connect(self.interpreter.widget_proxy,
                     SIGNAL("new_prompt(QString)"), self.new_prompt)
        self.connect(self.interpreter.widget_proxy,
                     SIGNAL("edit(QString,bool)"), self.edit_script)
        if self.multithreaded:
            self.interpreter.start()
        
        # interpreter banner
        banner = create_banner(_('Type "copyright", "credits" or "license" for more information.'), self.message)
        self.write(banner, prompt=True)

        # Initial commands
        for cmd in self.commands:
            self.run_command(cmd, history=False, new_prompt=False)
                
        # First prompt
        self.new_prompt(self.interpreter.p1)
        self.emit(SIGNAL("refresh()"))

        return self.interpreter

    def exit_interpreter(self):
        """Exit interpreter"""
        self.interpreter.exit_flag = True
        if self.multithreaded:
            self.interpreter.stdin_write.write('\n')
        self.interpreter.restore_stds()
        
    def edit_script(self, filename, external_editor):
        filename = unicode(filename)
        if external_editor:
            self.external_editor(filename)
        else:
            self.parent().edit_script(filename)            
                                    
    def stdout_avail(self):
        """Data is available in stdout, let's empty the queue and write it!"""
        data = self.interpreter.stdout_write.empty_queue()
        if data:
            self.write(data)
            self.repaint()
        
    def stderr_avail(self):
        """Data is available in stderr, let's empty the queue and write it!"""
        data = self.interpreter.stderr_write.empty_queue()
        if data:
            self.write(data, error=True)
            self.flush(error=True)
            self.repaint()


    #----- Menus, actions, ...
    def setup_context_menu(self):
        """Reimplement PythonShellWidget method"""
        PythonShellWidget.setup_context_menu(self)
        self.help_action = create_action(self, _("Help..."),
                           icon=get_std_icon('DialogHelpButton'),
                           triggered=self.help)
        self.menu.addAction(self.help_action)

    def help(self):
        """Help on Spyder console"""
        QMessageBox.about(self, _("Help"),
            _("""<b>%s</b>
            <p><i>%s</i><br>    edit foobar.py
            <p><i>%s</i><br>    xedit foobar.py
            <p><i>%s</i><br>    run foobar.py
            <p><i>%s</i><br>    clear x, y
            <p><i>%s</i><br>    !ls
            <p><i>%s</i><br>    object?
            <p><i>%s</i><br>    result = oedit(object)
            """
            ) % ('Shell special commands:', 'Internal editor:',
                 'External editor:', 'Run script:', 'Remove references:',
                 'System commands:', 'Python help:', 'GUI-based editor:') )
                
                
    #------ External editing
    def external_editor(self, filename, goto=-1):
        """Edit in an external editor
        Recommended: SciTE (e.g. to go to line where an error did occur)"""
        editor_path = CONF.get('internal_console', 'external_editor/path')
        goto_option = CONF.get('internal_console', 'external_editor/gotoline')
        try:
            if goto > 0 and goto_option:
                Popen(r'%s "%s" %s%d' % (editor_path, filename,
                                         goto_option, goto))
            else:
                Popen(r'%s "%s"' % (editor_path, filename))
        except OSError:
            self.write_error("External editor was not found:"
                             " %s\n" % editor_path)


    #------ I/O
    def flush(self, error=False, prompt=False):
        """Reimplement PythonShellWidget method"""
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
        self.interpreter.stdin_write.write(cmd + '\n')
        if not self.multithreaded:
            self.interpreter.run_line()
            self.emit(SIGNAL("refresh()"))
    
    
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
        return self.interpreter.namespace.keys()
        
    def get_cdlistdir(self):
        """Return shell current directory list dir"""
        return os.listdir(os.getcwdu())
                
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
        """Get object documentation"""
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
