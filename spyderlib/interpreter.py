# -*- coding: utf-8 -*-
#
# Copyright © 2009 Pierre Raybaut
# Licensed under the terms of the MIT License
# (see spyderlib/__init__.py for details)

"""Shell Interpreter"""

import __builtin__, sys, atexit
from code import InteractiveConsole

# Local imports:
from spyderlib.config import CONF


class RollbackImporter:
    """
    Rollback importer:
        PyUnit (Steve Purcell)
        http://pyunit.sourceforge.net
    """
    def __init__(self):
        "Creates an instance and installs as the global importer"
        self.previous_modules = sys.modules.copy()
        self.real_import = __builtin__.__import__
        __builtin__.__import__ = self._import
        self.new_modules = {}
        
    def _import(self, name, globals=None, locals=None, fromlist=[]):
        result = self.real_import(name, globals, locals, fromlist)
        self.new_modules[name] = 1
        return result
        
    def uninstall(self):
        for modname in self.new_modules.keys():
            if not self.previous_modules.has_key(modname):
                # Force reload when modname next imported
                del sys.modules[modname]
        __builtin__.__import__ = self.real_import
    

class Interpreter(InteractiveConsole):
    """Interpreter"""
    def __init__(self, namespace=None, exitfunc=None,
                 rawinputfunc=None, helpfunc=None):
        """
        namespace: locals send to InteractiveConsole object
        commands: list of commands executed at startup
        """
        InteractiveConsole.__init__(self, namespace)
        
        if exitfunc is not None:
            atexit.register(exitfunc)
        
        self.rollback_importer = None
        
        self.namespace = self.locals
        self.namespace['__name__'] = '__main__'
        self.namespace['execfile'] = self.execfile
        if rawinputfunc is not None:
            self.namespace['raw_input'] = rawinputfunc
            self.namespace['input'] = lambda text='': eval(rawinputfunc(text))
        if helpfunc is not None:
            self.namespace['help'] = helpfunc
        
    def _install_rollback_importer(self):
        if self.rollback_importer is not None:
            self.rollback_importer.uninstall()
        if CONF.get('shell', 'rollback_importer'):
            self.rollback_importer = RollbackImporter()
        else:
            self.rollback_importer = None
        
    def execfile(self, filename):
        """Exec filename"""
        source = open(filename, 'r').read()
        try:
            try:
                name = filename.encode('ascii')
            except UnicodeEncodeError:
                name = '<executed_script>'
            self._install_rollback_importer()
            code = compile(source, name, "exec")
        except (OverflowError, SyntaxError):
            InteractiveConsole.showsyntaxerror(self, filename)
        else:
            self.runcode(code)
        
    def eval(self, text):
        """
        Evaluate text and return (obj, valid)
        where *obj* is the object represented by *text*
        and *valid* is True if object evaluation did not raise any exception
        """
        assert isinstance(text, (str, unicode))
        try:
            return eval(text, self.locals), True
        except:
            return None, False
        
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
        return InteractiveConsole.push(self, line)
        
    def resetbuffer(self):
        """Remove any unhandled source text from the input buffer"""
        InteractiveConsole.resetbuffer(self)
        
