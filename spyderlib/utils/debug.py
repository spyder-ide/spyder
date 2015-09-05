# -*- coding: utf-8 -*-
#
# Copyright © 2009-2013 Pierre Raybaut
# Copyright © 2012-2013 anatoly techtonik
#
# Licensed under the terms of the MIT License
# (see spyderlib/__init__.py for details)

"""
Debug utilities that are independent of Spyder code.

See spyderlib.baseconfig for other helpers.
"""

from __future__ import print_function

import inspect
import traceback
import time


def log_time(fd):
    timestr = "Logging time: %s" % time.ctime(time.time())
    print("="*len(timestr), file=fd)
    print(timestr, file=fd)
    print("="*len(timestr), file=fd)
    print("", file=fd)

def log_last_error(fname, context=None):
    """Log last error in filename *fname* -- *context*: string (optional)"""
    fd = open(fname, 'a')
    log_time(fd)
    if context:
        print("Context", file=fd)
        print("-------", file=fd)
        print("", file=fd)
        print(context, file=fd)
        print("", file=fd)
        print("Traceback", file=fd)
        print("---------", file=fd)
        print("", file=fd)
    traceback.print_exc(file=fd)
    print("", file=fd)
    print("", file=fd)

def log_dt(fname, context, t0):
    fd = open(fname, 'a')
    log_time(fd)
    print("%s: %d ms" % (context, 10*round(1e2*(time.time()-t0))), file=fd)
    print("", file=fd)
    print("", file=fd)

def caller_name(skip=2):
    """
    Get name of a caller in the format module.class.method

    `skip` specifies how many levels of call stack to skip for caller's name.
    skip=1 means "who calls me", skip=2 "who calls my caller" etc.
       
    An empty string is returned if skipped levels exceed stack height
    """
    stack = inspect.stack()
    start = 0 + skip
    if len(stack) < start + 1:
      return ''
    parentframe = stack[start][0]    
    
    name = []
    module = inspect.getmodule(parentframe)
    # `modname` can be None when frame is executed directly in console
    # TODO(techtonik): consider using __main__
    if module:
        name.append(module.__name__)
    # detect classname
    if 'self' in parentframe.f_locals:
        # I don't know any way to detect call from the object method
        # XXX: there seems to be no way to detect static method call - it will
        #      be just a function call
        name.append(parentframe.f_locals['self'].__class__.__name__)
    codename = parentframe.f_code.co_name
    if codename != '<module>':  # top level usually
        name.append( codename ) # function or a method
    del parentframe
    return ".".join(name)

def get_class_that_defined(method):
    for cls in inspect.getmro(method.im_class):
        if method.__name__ in cls.__dict__:
            return cls.__name__

def log_methods_calls(fname, some_class, prefix=None):
    """
    Hack `some_class` to log all method calls into `fname` file.
    If `prefix` format is not set, each log entry is prefixed with:
      --[ asked / called / defined ] --
        asked   - name of `some_class`
        called  - name of class for which a method is called
        defined - name of class where method is defined
    
    Must be used carefully, because it monkeypatches __getattribute__ call.
    
    Example:  log_methods_calls('log.log', ShellBaseWidget)
    """
    # test if file is writable
    open(fname, 'a').close()
    FILENAME = fname
    CLASS = some_class

    PREFIX = "--[ %(asked)s / %(called)s / %(defined)s ]--"
    if prefix != None:
        PREFIX = prefix
    MAXWIDTH = {'o_O': 10}  # hack with editable closure dict, to align names
               
    def format_prefix(method, methodobj):
        """
        --[ ShellBase / Internal / BaseEdit ]------- get_position
        """
        classnames = {
            'asked': CLASS.__name__,
            'called': methodobj.__class__.__name__,
            'defined': get_class_that_defined(method)
        }
        line = PREFIX % classnames
        MAXWIDTH['o_O'] = max(len(line), MAXWIDTH['o_O'])
        return line.ljust(MAXWIDTH['o_O'], '-')
       
    import types
    def __getattribute__(self, name):
        attr = object.__getattribute__(self, name)
        if type(attr) is not types.MethodType:
            return attr
        else:
            def newfunc(*args, **kwargs):
                log = open(FILENAME, 'a')
                prefix = format_prefix(attr, self)
                log.write('%s %s\n' % (prefix, name))
                log.close()
                result = attr(*args, **kwargs)
                return result
            return newfunc
 
    some_class.__getattribute__ = __getattribute__
    
