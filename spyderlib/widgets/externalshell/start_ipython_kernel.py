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
        
        # Inline backend configuration
        if backends[backend_o] == 'inline':
           # Figure format
           format_o = CONF.get('ipython_console',
                               'pylab/inline/figure_format', 0)
           formats = {0: 'png', 1: 'svg'}
           cfg.InlineBackend.figure_format = formats[format_o]
           
           # Resolution
           cfg.InlineBackend.rc = {'figure.figsize': (6.0, 4.0),
                                   'savefig.dpi': 72,
                                   'font.size': 10,
                                   'figure.subplot.bottom': .125
                                   }
           resolution_o = CONF.get('ipython_console', 
                                   'pylab/inline/resolution')
           cfg.InlineBackend.rc['savefig.dpi'] = resolution_o
           
           # Figure size
           width_o = float(CONF.get('ipython_console', 'pylab/inline/width'))
           height_o = float(CONF.get('ipython_console', 'pylab/inline/height'))
           cfg.InlineBackend.rc['figure.figsize'] = (width_o, height_o)
    
    # Run lines of code at startup
    run_lines_o = CONF.get('ipython_console', 'startup/run_lines')
    if run_lines_o:
        cfg.IPKernelApp.exec_lines = map(lambda x: x.strip(),
                                         run_lines_o.split(','))
    
    # Run a file at startup
    use_file_o = CONF.get('ipython_console', 'startup/use_run_file')
    run_file_o = CONF.get('ipython_console', 'startup/run_file')
    if use_file_o and run_file_o:
        cfg.IPKernelApp.file_to_run = run_file_o
    
    return cfg

def set_edit_magic(shell):
    """Use %edit to open files in Spyder"""
    from spyderlib.utils import programs
    
    if programs.is_module_installed('IPython', '0.12'):
        shell.magic_ed = shell.magic_edit
        shell.magic_edit = open_in_spyder
    elif programs.is_module_installed('IPython', '>0.12'):
        shell.magics_manager.magics['line']['ed'] = \
          shell.magics_manager.magics['line']['edit']
        shell.magics_manager.magics['line']['edit'] = open_in_spyder
    else:
        # Don't want to know how things were in previous versions
        pass
    
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
set_edit_magic(__ipythonshell__)

#  Issue 977 : Since kernel.initialize() has completed execution, 
# we can now allow the monitor to communicate the availablility of 
# the kernel to accept front end connections.
__ipythonkernel__ = ipk_temp
del ipk_temp

# Start the (infinite) kernel event loop.
__ipythonkernel__.start()
