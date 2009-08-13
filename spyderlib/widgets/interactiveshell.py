# -*- coding: utf-8 -*-
#
# Copyright © 2009 Pierre Raybaut
# Licensed under the terms of the MIT License
# (see spyderlib/__init__.py for details)

"""Interactive shell widget : QsciPythonShell + Interpreter"""

# pylint: disable-msg=C0103
# pylint: disable-msg=R0903
# pylint: disable-msg=R0911
# pylint: disable-msg=R0201


#----Builtins
import __builtin__
try:
    from IPython.deep_reload import reload
    __builtin__.dreload = reload
except ImportError:
    pass
from spyderlib.widgets.objecteditor import oedit
__builtin__.oedit = oedit


import sys, os, re, pydoc
from time import time
from subprocess import Popen, PIPE
import os.path as osp

STDOUT = sys.stdout

from PyQt4.QtGui import QMessageBox, QKeySequence, QApplication
from PyQt4.QtCore import SIGNAL, QString, QEventLoop, Qt

# Local import
from spyderlib.qthelpers import (translate, create_action, get_std_icon,
                                 add_actions, keyevent2tuple)
from spyderlib.interpreter import Interpreter
from spyderlib.dochelpers import getargtxt, getsource, getdoc
from spyderlib.encoding import transcode
from spyderlib.config import CONF, get_icon, get_conf_path
try:
    from PyQt4.Qsci import QsciScintilla
    from spyderlib.widgets.qscishell import QsciPythonShell
except ImportError, e:
    raise ImportError, str(e) + \
        "\nspyderlib's code editor features are based on QScintilla2\n" + \
        "(http://www.riverbankcomputing.co.uk/software/qscintilla)"


def guess_filename(filename):
    """Guess filename"""
    if osp.isfile(filename):
        return filename
    pathlist = sys.path
    pathlist[0] = os.getcwdu()
    if not filename.endswith('.py'):
        filename += '.py'
    for path in pathlist:
        fname = osp.join(path, filename)
        if osp.isfile(fname):
            return fname
        elif osp.isfile(fname+'.py'):
            return fname+'.py'
        elif osp.isfile(fname+'.pyw'):
            return fname+'.pyw'
    return filename

def create_banner(moreinfo, message=''):
    """Create shell banner"""
    if message:
        message = '\n' + message + '\n'
    return 'Python %s on %s\n' % (sys.version, sys.platform) + \
            moreinfo+'\n' + message + '\n'


#TODO: Outside QsciPythonShell: replace most of 'insert_text' occurences by 'write'

#TODO: Prepare code for IPython integration:
#    - implement the 'pop_completion' method like in qt_console_widget.py
#      (easy... just rename a few methods here and there)
#    - implement '_configure_scintilla', '_apply_style', ...


class IOHandler(object):
    """Handle stream output"""
    def __init__(self, write):
        self._write = write
    def write(self, cmd):
        self._write(cmd)
    def flush(self):
        pass


class InteractiveShell(QsciPythonShell):
    """Shell base widget: link between QsciPythonShell and Interpreter"""
    p1 = ">>> "
    p2 = "... "
    def __init__(self, parent=None, namespace=None, commands=None, message="",
                 debug=False, exitfunc=None, profile=False):
        QsciPythonShell.__init__(self, parent, get_conf_path('.history_ic.py'),
                                 debug, profile)
        
        # Capture all interactive input/output 
        self.initial_stdout = sys.stdout
        self.initial_stderr = sys.stderr
        self.initial_stdin = sys.stdin
        self.stdout = self
        self.stderr = IOHandler(self.write_error)
        self.stdin = self
        self.redirect_stds()
        
        # KeyboardInterrupt support
        self.interrupted = False
        self.connect(self, SIGNAL("keyboard_interrupt()"),
                     self.keyboard_interrupt)
        
        # Code completion / calltips
        self.setAutoCompletionThreshold( \
            CONF.get('shell', 'autocompletion/threshold') )
        self.setAutoCompletionCaseSensitivity( \
            CONF.get('shell', 'autocompletion/case-sensitivity') )
        self.setAutoCompletionShowSingle( \
            CONF.get('shell', 'autocompletion/select-single') )
        if CONF.get('shell', 'autocompletion/from-document'):
            self.setAutoCompletionSource(QsciScintilla.AcsDocument)
        else:
            self.setAutoCompletionSource(QsciScintilla.AcsNone)
        
        # keyboard events management
        self.busy = False
        self.eventqueue = []
        
        # Execution Status
        self.more = False

        # Init interpreter
        self.exitfunc = exitfunc
        self.commands = commands
        self.message = message
        self.interpreter = None
        self.start_interpreter(namespace)
        
        # Clear status bar
        self.emit(SIGNAL("status(QString)"), QString())
                
                
    #------ Standard input/output
    def redirect_stds(self):
        """Redirects stds"""
        if not self.debug:
            sys.stdout = self.stdout
            sys.stderr = self.stderr
            sys.stdin  = self.stdin
        
    def restore_stds(self):
        """Restore stds"""
        if not self.debug:
            sys.stdout = self.initial_stdout
            sys.stderr = self.initial_stderr
            sys.stdin = self.initial_stdin
    
    
    #------ Interpreter
    def start_interpreter(self, namespace):
        """Start Python interpreter"""
        self.clear()
        
        self.restore_stds()
        self.interpreter = Interpreter(namespace, self.exitfunc,
                                       self.raw_input, self.help_replacement)
        self.redirect_stds()

        # interpreter banner
        banner = create_banner(self.tr('Type "copyright", "credits" or "license" for more information.'), self.message)
        self.setUndoRedoEnabled(False) #-disable undo/redo for a time being
        self.write(banner, prompt=True)

        # Initial commands
        for cmd in self.commands:
            self.run_command(cmd, history=False, new_prompt=False)
                
        # First prompt
        self.new_prompt(self.p1)
        self.setUndoRedoEnabled(True) #-enable undo/redo
        self.emit(SIGNAL("refresh()"))

        return self.interpreter


    #----- Menus, actions, ...
    def setup_context_menu(self):
        """Reimplement QsciPythonShell method"""
        QsciPythonShell.setup_context_menu(self)
        clear_line_action = create_action(self,
                           self.tr("Clear line"),
                           QKeySequence("Escape"),
                           icon=get_icon('eraser.png'),
                           tip=translate("InteractiveShell", "Clear line"),
                           triggered=self.clear_line)
        clear_action = create_action(self,
                           translate("InteractiveShell", "Clear shell"),
                           icon=get_icon('clear.png'),
                           tip=translate("InteractiveShell",
                                   "Clear shell contents ('cls' command)"),
                           triggered=self.clear_terminal)
        self.help_action = create_action(self,
                           translate("InteractiveShell", "Help..."),
                           icon=get_std_icon('DialogHelpButton'),
                           triggered=self.help)
        add_actions(self.menu, (clear_line_action, None, clear_action, None,
                                self.help_action))

    def help(self):
        """Help on Spyder console"""
        QMessageBox.about(self,
            translate("InteractiveShell", "Help"),
            self.tr("""<b>%1</b>
            <p><i>%2</i><br>    edit foobar.py
            <p><i>%3</i><br>    xedit foobar.py
            <p><i>%4</i><br>    run foobar.py
            <p><i>%5</i><br>    clear x, y
            <p><i>%6</i><br>    !ls
            <p><i>%7</i><br>    object?
            <p><i>%8</i><br>    result = oedit(object)
            """) \
            .arg(translate("InteractiveShell", 'Shell special commands:')) \
            .arg(translate("InteractiveShell", 'Internal editor:')) \
            .arg(translate("InteractiveShell", 'External editor:')) \
            .arg(translate("InteractiveShell", 'Run script:')) \
            .arg(translate("InteractiveShell", 'Remove references:')) \
            .arg(translate("InteractiveShell", 'System commands:')) \
            .arg(translate("InteractiveShell", 'Python help:')) \
            .arg(translate("InteractiveShell", 'GUI-based editor:')) )
                
                
    #------ External editing
    def external_editor(self, filename, goto=-1):
        """Edit in an external editor
        Recommended: SciTE (e.g. to go to line where an error did occur)"""
        editor_path = CONF.get('shell', 'external_editor/path')
        goto_option = CONF.get('shell', 'external_editor/gotoline')
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
    def raw_input(self, prompt):
        """Reimplementation of raw_input builtin"""
        self.new_prompt(prompt)
        self.setFocus()
        inp = self.wait_input()
        return inp
    
    def help_replacement(self, text=None, interactive=False):
        """For help() support (to be implemented...)"""
        if text is not None and not interactive:
            return pydoc.help(text)
        elif text is None:
            pyver = "%d.%d" % (sys.version_info[0], sys.version_info[1])
            self.write("""
Welcome to Python %s!  This is the online help utility.

If this is your first time using Python, you should definitely check out
the tutorial on the Internet at http://www.python.org/doc/tut/.

Enter the name of any module, keyword, or topic to get help on writing
Python programs and using Python modules.  To quit this help utility and
return to the interpreter, just type "quit".

To get a list of available modules, keywords, or topics, type "modules",
"keywords", or "topics".  Each module also comes with a one-line summary
of what it does; to list the modules whose summaries contain a given word
such as "spam", type "modules spam".
""" % pyver)
        else:
            text = text.strip()
            try:
                eval("pydoc.help(%s)" % text)
            except NameError, SyntaxError:
                print "no Python documentation found for '%r'" % text
        self.write(os.linesep)
        self.new_prompt("help>")
        inp = self.wait_input()
        if inp.strip():
            self.help_replacement(inp, interactive=True)
        else:
            self.write("""
You are now leaving help and returning to the Python interpreter.
If you want to ask for help on a particular object directly from the
interpreter, you can type "help(object)".  Executing "help('string')"
has the same effect as typing a particular string at the help> prompt.
""")
    
    def readline(self):
        inp = self.wait_input()
        return inp
        
    def wait_input(self):
        """Wait for input (raw_input)"""
        self.input_data = None # If shell is closed, None will be returned
        self.input_mode = True
        self.input_loop = QEventLoop()
        self.input_loop.exec_()
        self.input_loop = None
        return self.input_data
    
    def end_input(self, cmd):
        """End of wait_input mode"""
        self.input_data = cmd
        self.input_mode = False
        self.input_loop.exit()

    def flush(self, error=False, prompt=False):
        """Reimplement QsciPythonShell method"""
        QsciPythonShell.flush(self, error=error, prompt=prompt)
        if self.interrupted:
            self.interrupted = False
            raise KeyboardInterrupt


    #------ Clear terminal
    def clear_terminal(self):
        """Clear terminal window and write prompt"""
        self.clear()
        self.new_prompt(self.p2 if self.more else self.p1)


    #------ Paste
    def paste(self):
        """Reimplemented slot to handle multiline paste action"""
        lines = unicode(QApplication.clipboard().text())
        if len(lines.splitlines())>1:
            # Multiline paste
            self.removeSelectedText() # Remove selection, eventually
            cline, cindex = self.getCursorPosition()
            linetext = unicode(self.text(cline))
            lines = self.get_current_line_to_cursor()+lines+linetext[cindex:]
            self.clear_line()
            self.execute_lines(lines)
            cline2, _ = self.getCursorPosition()
            self.setCursorPosition(cline2,
               self.lineLength(cline2)-len(linetext[cindex:]) )
        else:
            # Standard paste
            QsciScintilla.paste(self)


    #------ Keyboard events
    def on_enter(self, command):
        """on_enter"""
        self.busy = True
        if self.profile:
            # Simple profiling test
            t0 = time()
            for _ in range(10):
                self.execute_command(command)
            self.insert_text(u"\n<Δt>=%dms\n" % (1e2*(time()-t0)))
            self.new_prompt(self.p1)
        else:
            self.execute_command(command)
        self.busy = False
        self.__flush_eventqueue()

    def keyPressEvent(self, event):
        """
        Re-implemented to handle the user input a key at a time.
        event: key event (QKeyEvent)
        """
        # To enable keyboard interrupt when busy:
        if event.key() == Qt.Key_C and event.modifiers() & Qt.ControlModifier:
            self.copy()
            event.accept()
            return
        
        if self.busy and (not self.input_mode):
            # Ignoring all events except KeyboardInterrupt (see above)
            # Keep however these events in self.eventqueue
            self.eventqueue.append(keyevent2tuple(event))
            event.accept()
        else:
            self.__flush_eventqueue() # Shouldn't be necessary
            self.process_keyevent(event)
        
    def __flush_eventqueue(self):
        """Flush keyboard event queue"""
        while self.eventqueue:
            past_event = self.eventqueue.pop(0)
            self.process_keyevent(past_event)
        
    #------ Command execution
    def keyboard_interrupt(self):
        """Simulate keyboard interrupt"""
        if self.busy:
            # Interrupt only if console is busy
            self.interrupted = True
        elif self.more:
            self.write_error("\nKeyboardInterrupt\n")
            self.more = False
            self.new_prompt(self.p1)
            self.interpreter.resetbuffer()

    def execute_lines(self, lines):
        """
        Execute a set of lines as multiple command
        lines: multiple lines of text to be executed as single commands
        """
        for line in lines.splitlines(True):
            if line.endswith("\r\n"):
                fullline = True
                cmd = line[:-2]
            elif line.endswith("\r") or line.endswith("\n"):
                fullline = True
                cmd = line[:-1]
            else:
                fullline = False
            self.write(line, flush=True)
            if fullline:
                self.execute_command(cmd+"\n")
        
    def execute_command(self, cmd):
        """
        Execute a command
        cmd: one-line command only, with '\n' at the end!
        """
        if self.input_mode:
            self.end_input(cmd)
            return
        # cls command
        if cmd == 'cls':
            self.clear_terminal()
            return
        assert cmd.endswith('\n')
        self.run_command(cmd[:-1])
       
    def run_command(self, cmd, history=True, new_prompt=True):
        """Run command in interpreter"""
        
        # Before running command
        self.emit(SIGNAL("status(QString)"), self.tr('Busy...'))
        self.emit( SIGNAL("executing_command(bool)"), True )
        
        if not cmd:
            cmd = ''
        else:
            if history:
                self.add_to_history(cmd)

        # -- Special commands type I
        #    (transformed into commands executed in the interpreter)
        # ? command
        special_pattern = r"^%s (?:r\')?(?:u\')?\"?\'?([a-zA-Z0-9_\.]+)"
        run_match = re.match(special_pattern % 'run', cmd)
        if cmd.endswith('?'):
            cmd = 'help(%s)' % cmd[:-1]
        # run command
        elif run_match:
            filename = guess_filename(run_match.groups()[0])
            cmd = 'execfile(r"%s")' % filename
        # -- End of Special commands type I
            
        # -- Special commands type II
        #    (don't need code execution in interpreter)
        xedit_match = re.match(special_pattern % 'xedit', cmd)
        edit_match = re.match(special_pattern % 'edit', cmd)
        clear_match = re.match(r"^clear ([a-zA-Z0-9_, ]+)", cmd)
        # (external) edit command
        if xedit_match:
            filename = guess_filename(xedit_match.groups()[0])
            self.external_editor(filename)
        # local edit command
        elif edit_match:
            filename = guess_filename(edit_match.groups()[0])
            if osp.isfile(filename):
                self.parent().edit_script(filename)
            else:
                self.write_error("No such file or directory: %s\n" % filename)
        # remove reference (equivalent to MATLAB's clear command)
        elif clear_match:
            varnames = clear_match.groups()[0].replace(' ', '').split(',')
            for varname in varnames:
                try:
                    self.interpreter.locals.pop(varname)
                except KeyError:
                    pass
        # Execute command
        elif cmd.startswith('!'):
            # System ! command
            pipe = Popen(cmd[1:], shell=True,
                         stdin=PIPE, stderr=PIPE, stdout=PIPE)
            txt_out = transcode( pipe.stdout.read() )
            txt_err = transcode( pipe.stderr.read().rstrip() )
            if txt_err:
                self.write_error(txt_err)
            if txt_out:
                self.write(txt_out)
            self.write('\n')
            self.more = False
        # -- End of Special commands type II
        else:
            # Command executed in the interpreter
            self.more = self.interpreter.push(cmd)
        
        self.emit(SIGNAL("refresh()"))
        if new_prompt:
            self.new_prompt(self.p2 if self.more else self.p1)
        if not self.more:
            self.interpreter.resetbuffer()
            
        # After running command
        self.emit(SIGNAL("executing_command(bool)"), False)
        self.emit(SIGNAL("status(QString)"), QString())
    
    
    #------ Code completion / Calltips
    def _eval(self, text):
        """Is text a valid object?"""
        return self.interpreter.eval(text)
                
    def get_dir(self, objtxt):
        """Return dir(object)"""
        obj, _valid = self._eval(objtxt)
        return dir(obj)
                
    def iscallable(self, objtxt):
        """Is object callable?"""
        obj, _valid = self._eval(objtxt)
        return callable(obj)
    
    def get_arglist(self, objtxt):
        """Get func/method argument list"""
        obj, _valid = self._eval(objtxt)
        return getargtxt(obj)
    
    def get__doc__(self, objtxt):
        """Get object __doc__"""
        obj, _valid = self._eval(objtxt)
        return obj.__doc__
    
    def get_doc(self, objtxt):
        """Get object documentation"""
        obj, _valid = self._eval(objtxt)
        return getdoc(obj)
    
    def get_source(self, objtxt):
        """Get object source"""
        obj, _valid = self._eval(objtxt)
        return getsource(obj)
