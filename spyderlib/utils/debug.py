# -*- coding: utf-8 -*-
#
# Copyright © 2009-2010 Pierre Raybaut
# Licensed under the terms of the MIT License
# (see spyderlib/__init__.py for details)

"""Debug utilities"""

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
