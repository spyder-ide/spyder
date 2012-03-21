# -*- coding: utf-8 -*-
#
# Copyright © 2009-2010 Pierre Raybaut
# Licensed under the terms of the MIT License
# (see spyderlib/__init__.py for details)

"""Debug utilities"""

import inspect
import traceback
import time


def log_time(fd):
    timestr = "Logging time: %s" % time.ctime(time.time())
    print >>fd, "="*len(timestr)
    print >>fd, timestr
    print >>fd, "="*len(timestr)
    print >>fd, ""

def log_last_error(fname, context=None):
    """Log last error in filename *fname* -- *context*: string (optional)"""
    fd = open(fname, 'a')
    log_time(fd)
    if context:
        print >>fd, "Context"
        print >>fd, "-------"
        print >>fd, ""
        print >>fd, context
        print >>fd, ""
        print >>fd, "Traceback"
        print >>fd, "---------"
        print >>fd, ""
    traceback.print_exc(file=fd)
    print >>fd, ""
    print >>fd, ""

def log_dt(fname, context, t0):
    fd = open(fname, 'a')
    log_time(fd)
    print >>fd, "%s: %d ms" % (context, 10*round(1e2*(time.time()-t0)))
    print >>fd, ""
    print >>fd, ""

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
