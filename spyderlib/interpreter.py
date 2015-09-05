# -*- coding: utf-8 -*-
#
# Copyright © 2009-2010 Pierre Raybaut
# Licensed under the terms of the MIT License
# (see spyderlib/__init__.py for details)

"""Shell Interpreter"""

from __future__ import print_function

import sys
import atexit
import threading
import ctypes
import os
import re
import os.path as osp
import pydoc
from subprocess import Popen, PIPE
from code import InteractiveConsole

# Local imports:
from spyderlib.utils.dochelpers import isdefined
from spyderlib.utils import encoding
from spyderlib.py3compat import is_text_string, getcwd
from spyderlib.utils.misc import remove_backslashes

# Force Python to search modules in the current directory first:
sys.path.insert(0, '')


def guess_filename(filename):
    """Guess filename"""
    if osp.isfile(filename):
        return filename
    if not filename.endswith('.py'):
        filename += '.py'
    for path in [getcwd()] + sys.path:
        fname = osp.join(path, filename)
        if osp.isfile(fname):
            return fname
        elif osp.isfile(fname+'.py'):
            return fname+'.py'
        elif osp.isfile(fname+'.pyw'):
            return fname+'.pyw'
    return filename

class Interpreter(InteractiveConsole, threading.Thread):
    """Interpreter, executed in a separate thread"""
    p1 = ">>> "
    p2 = "... "
    def __init__(self, namespace=None, exitfunc=None,
                 Output=None, WidgetProxy=None, debug=False):
        """
        namespace: locals send to InteractiveConsole object
        commands: list of commands executed at startup
        """
        InteractiveConsole.__init__(self, namespace)
        threading.Thread.__init__(self)
        
        self._id = None
        
        self.exit_flag = False
        self.debug = debug
        
        # Execution Status
        self.more = False
        
        if exitfunc is not None:
            atexit.register(exitfunc)
        
        self.namespace = self.locals
        self.namespace['__name__'] = '__main__'
        self.namespace['execfile'] = self.execfile
        self.namespace['runfile'] = self.runfile
        self.namespace['raw_input'] = self.raw_input_replacement
        self.namespace['help'] = self.help_replacement
                    
        # Capture all interactive input/output 
        self.initial_stdout = sys.stdout
        self.initial_stderr = sys.stderr
        self.initial_stdin = sys.stdin
        
        # Create communication pipes
        pr, pw = os.pipe()
        self.stdin_read = os.fdopen(pr, "r")
        self.stdin_write = os.fdopen(pw, "wb", 0)
        self.stdout_write = Output()
        self.stderr_write = Output()
        
        self.input_condition = threading.Condition()
        self.widget_proxy = WidgetProxy(self.input_condition)
        
        self.redirect_stds()
        

    #------ Standard input/output
    def redirect_stds(self):
        """Redirects stds"""
        if not self.debug:
            sys.stdout = self.stdout_write
            sys.stderr = self.stderr_write
            sys.stdin = self.stdin_read
        
    def restore_stds(self):
        """Restore stds"""
        if not self.debug:
            sys.stdout = self.initial_stdout
            sys.stderr = self.initial_stderr
            sys.stdin = self.initial_stdin

    def raw_input_replacement(self, prompt=''):
        """For raw_input builtin function emulation"""
        self.widget_proxy.wait_input(prompt)
        self.input_condition.acquire()
        while not self.widget_proxy.data_available():
            self.input_condition.wait()
        inp = self.widget_proxy.input_data
        self.input_condition.release()
        return inp
        
    def help_replacement(self, text=None, interactive=False):
        """For help builtin function emulation"""
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
            except (NameError, SyntaxError):
                print("no Python documentation found for '%r'" % text)
        self.write(os.linesep)
        self.widget_proxy.new_prompt("help> ")
        inp = self.raw_input_replacement()
        if inp.strip():
            self.help_replacement(inp, interactive=True)
        else:
            self.write("""
You are now leaving help and returning to the Python interpreter.
If you want to ask for help on a particular object directly from the
interpreter, you can type "help(object)".  Executing "help('string')"
has the same effect as typing a particular string at the help> prompt.
""")

    def run_command(self, cmd, new_prompt=True):
        """Run command in interpreter"""
        if cmd == 'exit()':
            self.exit_flag = True
            self.write('\n')
            return
        # -- Special commands type I
        #    (transformed into commands executed in the interpreter)
        # ? command
        special_pattern = r"^%s (?:r\')?(?:u\')?\"?\'?([a-zA-Z0-9_\.]+)"
        run_match = re.match(special_pattern % 'run', cmd)
        help_match = re.match(r'^([a-zA-Z0-9_\.]+)\?$', cmd)
        cd_match = re.match(r"^\!cd \"?\'?([a-zA-Z0-9_ \.]+)", cmd)
        if help_match:
            cmd = 'help(%s)' % help_match.group(1)
        # run command
        elif run_match:
            filename = guess_filename(run_match.groups()[0])
            cmd = "runfile('%s', args=None)" % remove_backslashes(filename)
        # !cd system command
        elif cd_match:
            cmd = 'import os; os.chdir(r"%s")' % cd_match.groups()[0].strip()
        # -- End of Special commands type I
            
        # -- Special commands type II
        #    (don't need code execution in interpreter)
        xedit_match = re.match(special_pattern % 'xedit', cmd)
        edit_match = re.match(special_pattern % 'edit', cmd)
        clear_match = re.match(r"^clear ([a-zA-Z0-9_, ]+)", cmd)
        # (external) edit command
        if xedit_match:
            filename = guess_filename(xedit_match.groups()[0])
            self.widget_proxy.edit(filename, external_editor=True)
        # local edit command
        elif edit_match:
            filename = guess_filename(edit_match.groups()[0])
            if osp.isfile(filename):
                self.widget_proxy.edit(filename)
            else:
                self.stderr_write.write(
                                "No such file or directory: %s\n" % filename)
        # remove reference (equivalent to MATLAB's clear command)
        elif clear_match:
            varnames = clear_match.groups()[0].replace(' ', '').split(',')
            for varname in varnames:
                try:
                    self.namespace.pop(varname)
                except KeyError:
                    pass
        # Execute command
        elif cmd.startswith('!'):
            # System ! command
            pipe = Popen(cmd[1:], shell=True,
                         stdin=PIPE, stderr=PIPE, stdout=PIPE)
            txt_out = encoding.transcode( pipe.stdout.read().decode() )
            txt_err = encoding.transcode( pipe.stderr.read().decode().rstrip() )
            if txt_err:
                self.stderr_write.write(txt_err)
            if txt_out:
                self.stdout_write.write(txt_out)
            self.stdout_write.write('\n')
            self.more = False
        # -- End of Special commands type II
        else:
            # Command executed in the interpreter
#            self.widget_proxy.set_readonly(True)
            self.more = self.push(cmd)
#            self.widget_proxy.set_readonly(False)
        
        if new_prompt:
            self.widget_proxy.new_prompt(self.p2 if self.more else self.p1)
        if not self.more:
            self.resetbuffer()
        
    def run(self):
        """Wait for input and run it"""
        while not self.exit_flag:
            self.run_line()
            
    def run_line(self):
        line = self.stdin_read.readline()
        if self.exit_flag:
            return
        # Remove last character which is always '\n':
        self.run_command(line[:-1])
        
    def get_thread_id(self):
        """Return thread id"""
        if self._id is None:
            for thread_id, obj in list(threading._active.items()):
                if obj is self:
                    self._id = thread_id
        return self._id
        
    def raise_keyboard_interrupt(self):
        if self.isAlive():
            ctypes.pythonapi.PyThreadState_SetAsyncExc(self.get_thread_id(),
                                           ctypes.py_object(KeyboardInterrupt))
            return True
        else:
            return False
            
            
    def closing(self):
        """Actions to be done before restarting this interpreter"""
        pass
        
    def execfile(self, filename):
        """Exec filename"""
        source = open(filename, 'r').read()
        try:
            try:
                name = filename.encode('ascii')
            except UnicodeEncodeError:
                name = '<executed_script>'
            code = compile(source, name, "exec")
        except (OverflowError, SyntaxError):
            InteractiveConsole.showsyntaxerror(self, filename)
        else:
            self.runcode(code)
        
    def runfile(self, filename, args=None):
        """
        Run filename
        args: command line arguments (string)
        """
        if args is not None and not is_text_string(args):
            raise TypeError("expected a character buffer object")
        self.namespace['__file__'] = filename
        sys.argv = [filename]
        if args is not None:
            for arg in args.split():
                sys.argv.append(arg)
        self.execfile(filename)
        sys.argv = ['']
        self.namespace.pop('__file__')
        
    def eval(self, text):
        """
        Evaluate text and return (obj, valid)
        where *obj* is the object represented by *text*
        and *valid* is True if object evaluation did not raise any exception
        """
        assert is_text_string(text)
        try:
            return eval(text, self.locals), True
        except:
            return None, False
        
    def is_defined(self, objtxt, force_import=False):
        """Return True if object is defined"""
        return isdefined(objtxt, force_import=force_import,
                         namespace=self.locals)
        
    #===========================================================================
    # InteractiveConsole API
    #===========================================================================
    def push(self, line):
        """
        Push a line of source text to the interpreter
        
        The line should not have a trailing newline; it may have internal 
        newlines. The line is appended to a buffer and the interpreter’s 
        runsource() method is called with the concatenated contents of the 
        buffer as source. If this indicates that the command was executed 
        or invalid, the buffer is reset; otherwise, the command is incomplete, 
        and the buffer is left as it was after the line was appended. 
        The return value is True if more input is required, False if the line 
        was dealt with in some way (this is the same as runsource()).
        """
        return InteractiveConsole.push(self, "#coding=utf-8\n" + line)
        
    def resetbuffer(self):
        """Remove any unhandled source text from the input buffer"""
        InteractiveConsole.resetbuffer(self)
        