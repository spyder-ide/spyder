# -*- coding: utf-8 -*-
#
# Copyright © 2009-2012 Pierre Raybaut
# Licensed under the terms of the MIT License
# (see spyderlib/__init__.py for details)

"""Startup file used by ExternalPythonShell exclusively for IPython kernels
(see spyderlib/widgets/externalshell/pythonshell.py)"""

import sys
import os.path as osp

# TODO: Move to Jupyter imports in 3.1
try:
    import warnings
    from IPython.utils.shimmodule import ShimWarning
    warnings.simplefilter('ignore', ShimWarning)
except:
    pass


def sympy_config(mpl_backend):
    """Sympy configuration"""
    if mpl_backend is not None:
        lines = """
from sympy.interactive import init_session
init_session()
%matplotlib {0}
""".format(mpl_backend)
    else:
        lines = """
from sympy.interactive import init_session
init_session()
"""

    return lines


def kernel_config():
    """Create a config object with IPython kernel options"""
    from IPython.config.loader import Config, load_pyconfig_files
    from IPython.core.application import get_ipython_dir
    from spyderlib.config import CONF
    from spyderlib.utils.programs import is_module_installed
    
    # ---- IPython config ----
    try:
        profile_path = osp.join(get_ipython_dir(), 'profile_default')
        ip_cfg = load_pyconfig_files(['ipython_config.py',
                                      'ipython_qtconsole_config.py'],
                                      profile_path)
    except:
        ip_cfg = Config()
    
    # ---- Spyder config ----
    spy_cfg = Config()
    
    # Until we implement Issue 1052
    spy_cfg.InteractiveShell.xmode = 'Plain'
    
    # Run lines of code at startup
    run_lines_o = CONF.get('ipython_console', 'startup/run_lines')
    if run_lines_o:
        spy_cfg.IPKernelApp.exec_lines = [x.strip() for x in run_lines_o.split(',')]
    else:
        spy_cfg.IPKernelApp.exec_lines = []
    
    # Pylab configuration
    mpl_backend = None
    mpl_installed = is_module_installed('matplotlib')
    pylab_o = CONF.get('ipython_console', 'pylab')

    if mpl_installed and pylab_o:
        # Get matplotlib backend
        backend_o = CONF.get('ipython_console', 'pylab/backend', 0)
        backends = {0: 'inline', 1: 'auto', 2: 'qt', 3: 'osx', 4: 'gtk',
                    5: 'wx', 6: 'tk'}
        mpl_backend = backends[backend_o]

        # Automatically load Pylab and Numpy, or only set Matplotlib
        # backend
        autoload_pylab_o = CONF.get('ipython_console', 'pylab/autoload')
        if autoload_pylab_o:
            spy_cfg.IPKernelApp.exec_lines.append(
                                              "%pylab {0}".format(mpl_backend))
        else:
            spy_cfg.IPKernelApp.exec_lines.append(
                                         "%matplotlib {0}".format(mpl_backend))

        # Inline backend configuration
        if backends[backend_o] == 'inline':
           # Figure format
           format_o = CONF.get('ipython_console',
                               'pylab/inline/figure_format', 0)
           formats = {0: 'png', 1: 'svg'}
           spy_cfg.InlineBackend.figure_format = formats[format_o]
           
           # Resolution
           spy_cfg.InlineBackend.rc = {'figure.figsize': (6.0, 4.0),
                                   'savefig.dpi': 72,
                                   'font.size': 10,
                                   'figure.subplot.bottom': .125,
                                   'figure.facecolor': 'white',
                                   'figure.edgecolor': 'white'
                                   }
           resolution_o = CONF.get('ipython_console', 
                                   'pylab/inline/resolution')
           spy_cfg.InlineBackend.rc['savefig.dpi'] = resolution_o
           
           # Figure size
           width_o = float(CONF.get('ipython_console', 'pylab/inline/width'))
           height_o = float(CONF.get('ipython_console', 'pylab/inline/height'))
           spy_cfg.InlineBackend.rc['figure.figsize'] = (width_o, height_o)
    
    # Run a file at startup
    use_file_o = CONF.get('ipython_console', 'startup/use_run_file')
    run_file_o = CONF.get('ipython_console', 'startup/run_file')
    if use_file_o and run_file_o:
        spy_cfg.IPKernelApp.file_to_run = run_file_o
    
    # Autocall
    autocall_o = CONF.get('ipython_console', 'autocall')
    spy_cfg.ZMQInteractiveShell.autocall = autocall_o
    
    # To handle the banner by ourselves in IPython 3+
    spy_cfg.ZMQInteractiveShell.banner1 = ''
    
    # Greedy completer
    greedy_o = CONF.get('ipython_console', 'greedy_completer')
    spy_cfg.IPCompleter.greedy = greedy_o
    
    # Sympy loading
    sympy_o = CONF.get('ipython_console', 'symbolic_math')
    if sympy_o:
        lines = sympy_config(mpl_backend)
        spy_cfg.IPKernelApp.exec_lines.append(lines)

    # Merge IPython and Spyder configs. Spyder prefs will have prevalence
    # over IPython ones
    ip_cfg._merge(spy_cfg)
    return ip_cfg


def change_edit_magic(shell):
    """Use %edit to open files in Spyder"""
    try:
        shell.magics_manager.magics['line']['ed'] = \
          shell.magics_manager.magics['line']['edit']
        shell.magics_manager.magics['line']['edit'] = open_in_spyder  #analysis:ignore
    except:
        pass

def varexp(line):
    """
    Spyder's variable explorer magic
    
    Used to generate plots, histograms and images of the variables displayed
    on it.
    """
    ip = get_ipython()       #analysis:ignore
    funcname, name = line.split()
    import spyderlib.pyplot
    __fig__ = spyderlib.pyplot.figure();
    __items__ = getattr(spyderlib.pyplot, funcname[2:])(ip.user_ns[name])
    spyderlib.pyplot.show()
    del __fig__, __items__

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

# Fire up the kernel instance.
from IPython.kernel.zmq.kernelapp import IPKernelApp
ipk_temp = IPKernelApp.instance()
ipk_temp.config = kernel_config()
ipk_temp.initialize()

# Grabbing the kernel's shell to share its namespace with our
# Variable Explorer
__ipythonshell__ = ipk_temp.shell

# Issue 977 : Since kernel.initialize() has completed execution, 
# we can now allow the monitor to communicate the availablility of 
# the kernel to accept front end connections.
__ipythonkernel__ = ipk_temp
del ipk_temp

# Change %edit to open files inside Spyder
# NOTE: Leave this and other magic modifications *after* setting
# __ipythonkernel__ to not have problems while starting kernels
change_edit_magic(__ipythonshell__)
__ipythonshell__.register_magic_function(varexp)

# Start the (infinite) kernel event loop.
__ipythonkernel__.start()
