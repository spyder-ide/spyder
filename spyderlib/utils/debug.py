# -*- coding: utf-8 -*-
#
# Copyright © 2009-2013 Pierre Raybaut.
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
    """Get a name of a caller in the format module.class.method
    
       `skip` specifies how many levels of stack to skip while getting caller
       name. skip=1 means "who calls me", skip=2 "who calls my caller" etc.
       
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
