# -*- coding: utf-8 -*-
#
# Copyright © 2009-2012 Pierre Raybaut
# Licensed under the terms of the MIT License
# (see spyderlib/__init__.py for details)

"""Startup file used by ExternalPythonShell exclusively for IPython kernels
(see spyderlib/widgets/externalshell/pythonshell.py)"""

import sys
import os.path as osp

def kernel_config():
    """Create a config object with IPython kernel options"""
    from IPython.config.loader import Config
    from spyderlib.config import CONF
    
    cfg = Config()
    
    # Until we implement Issue 1052:
    # http://code.google.com/p/spyderlib/issues/detail?id=1052
    cfg.InteractiveShell.xmode = 'Plain'
    
    # Pylab activation option
    pylab_o = CONF.get('ipython_console', 'pylab')
    
    # Automatically load Pylab and Numpy
    autoload_pylab_o = CONF.get('ipython_console', 'pylab/autoload')
    cfg.IPKernelApp.pylab_import_all = pylab_o and autoload_pylab_o
    
    # Pylab backend configuration
    if pylab_o:
        backend_o = CONF.get('ipython_console', 'pylab/backend', 0)
        backends = {0: 'inline', 1: 'auto', 2: 'qt', 3: 'osx', 4: 'gtk',
                    5: 'wx', 6: 'tk'}
        cfg.IPKernelApp.pylab = backends[backend_o]
    
    # Run lines of code at startup
    run_lines_o = CONF.get('ipython_console', 'kernel/run_lines')
    if run_lines_o:
        cfg.IPKernelApp.exec_lines = map(lambda x: x.strip(),
                                         run_lines_o.split(','))
    
    # Run a file at startup
    select_file_o = CONF.get('ipython_console', 'kernel/select_run_file')
    run_file_o = CONF.get('ipython_console', 'kernel/run_file')
    if select_file_o and run_file_o:
        cfg.IPKernelApp.file_to_run = run_file_o
    
    return cfg

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
ipk_temp.config = kernel_config()
ipk_temp.initialize()
__ipythonshell__ = ipk_temp.shell

#  Issue 977 : Since kernel.initialize() has completed execution, 
# we can now allow the monitor to communicate the availablility of 
# the kernel to accept front end connections.
__ipythonkernel__ = ipk_temp
del ipk_temp

# Start the (infinite) kernel event loop.
__ipythonkernel__.start()
