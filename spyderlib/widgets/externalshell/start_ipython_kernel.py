# -*- coding: utf-8 -*-
#
# Copyright © 2009-2012 Pierre Raybaut
# Licensed under the terms of the MIT License
# (see spyderlib/__init__.py for details)

"""Startup file used by ExternalPythonShell exclusively for IPython kernels
(see spyderlib/widgets/externalshell/pythonshell.py)"""

import sys
import os.path as osp

def configure_kernel(kernel):
    from spyderlib.config import CONF
    from spyderlib.utils import programs
    
    # Pylab activation option
    pylab_o = CONF.get('ipython_console', 'pylab', 0)
    
    # Pylab backend configuration
    if pylab_o and programs.is_module_installed("matplotlib"):
        backend_o = CONF.get('ipython_console', 'pylab/backend', 0)
        backends = {0: 'inline', 1: 'auto', 2: 'qt', 3: 'osx', 4: 'gtk',
                    5: 'wx', 6: 'tk'}
        kernel.config.IPKernelApp.pylab = backends[backend_o]

# Remove this module's path from sys.path:
try:
    sys.path.remove(osp.dirname(__file__))
except ValueError:
    pass

locals().pop('__file__')
__doc__ = ''
__name__ = '__main__'

# Add current directory to sys.path (like for any standard Python interpreter
# executed in interactive mode):
sys.path.insert(0, '')

# IPython >=v0.12 Kernel

# Fire up the kernel instance.
from IPython.zmq.ipkernel import IPKernelApp
ipk_temp = IPKernelApp.instance()
configure_kernel(ipk_temp)
ipk_temp.initialize()
__ipythonshell__ = ipk_temp.shell

# Issue 977: Since kernel.initialize() has completed execution, 
# we can now allow the monitor to communicate the availablility of 
# the kernel to accept front end connections.
__ipythonkernel__ = ipk_temp
del ipk_temp

# Start the (infinite) kernel event loop.
__ipythonkernel__.start()
