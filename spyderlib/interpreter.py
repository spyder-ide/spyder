# -*- coding: utf-8 -*-
#
# Copyright © 2009 Pierre Raybaut
# Licensed under the terms of the MIT License
# (see spyderlib/__init__.py for details)

"""Shell Interpreter"""

import atexit, code


class Interpreter(code.InteractiveConsole):
    """Interpreter"""
    def __init__(self, namespace=None, exitfunc=None,
                 rawinputfunc=None, helpfunc=None):
        """
        namespace: locals send to InteractiveConsole object
        commands: list of commands executed at startup
        """
        code.InteractiveConsole.__init__(self, namespace)
        
        if exitfunc is not None:
            atexit.register(exitfunc)
        
        self.namespace = self.locals
        self.namespace['__name__'] = '__main__'
        if rawinputfunc is not None:
            self.namespace['raw_input'] = rawinputfunc
            self.namespace['input'] = lambda text='': eval(rawinputfunc(text))
        if helpfunc is not None:
            self.namespace['help'] = helpfunc
        
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
        
