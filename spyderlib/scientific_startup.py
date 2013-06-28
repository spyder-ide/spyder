# -*- coding: utf-8 -*-
#
# Copyright © 2011 Pierre Raybaut
# Licensed under the terms of the MIT License
# (see spyderlib/__init__.py for details)

"""
Scientific Python startup script

Requires NumPy, SciPy and Matplotlib
"""

# Need a temporary print function that is Python version agnostic.
import sys

def exec_print(string="", end_space=False):
    if sys.version[0] == '2':
        if end_space:
            exec("print '" + string + "',")
        else:
            exec("print '" + string + "'")
    else:
        if end_space:
            exec("print('" + string + "', end=' ')")
        else:
            exec("print('" + string + "')")

# Pollute the namespace but also provide MATLAB-like experience:
from pylab import *  #analysis:ignore

# Enable Matplotlib's interactive mode:
ion()

# Import modules following official guidelines:
import numpy as np
import scipy as sp
import matplotlib as mpl
import matplotlib.pyplot as plt  #analysis:ignore

exec_print("")
exec_print("Imported NumPy %s, SciPy %s, Matplotlib %s" %\
      (np.__version__, sp.__version__, mpl.__version__), end_space=True)

import os
if os.environ.get('QT_API') != 'pyside':
    try:
        import guiqwt
        import guiqwt.pyplot as plt_
        import guidata
        plt_.ion()
        exec_print("+ guidata %s, guiqwt %s" % (guidata.__version__,
                                           guiqwt.__version__))
    except ImportError:
        exec_print()
else:
    exec_print()

def setscientific():
    """Set 'scientific' in __builtin__"""
    import __builtin__
    from site import _Printer
    infos = """\
This is a standard Python interpreter with preloaded tools for scientific 
computing and visualization:

>>> import numpy as np  # NumPy (multidimensional arrays, linear algebra, ...)
>>> import scipy as sp  # SciPy (signal and image processing library)

>>> import matplotlib as mpl         # Matplotlib (2D/3D plotting library)
>>> import matplotlib.pyplot as plt  # Matplotlib's pyplot: MATLAB-like syntax
>>> from pylab import *              # Matplotlib's pylab interface
>>> ion()                            # Turned on Matplotlib's interactive mode
"""
    try:
        import guiqwt  #analysis:ignore
        infos += """
>>> import guidata  # GUI generation for easy dataset editing and display

>>> import guiqwt                 # Efficient 2D data-plotting features
>>> import guiqwt.pyplot as plt_  # guiqwt's pyplot: MATLAB-like syntax
>>> plt_.ion()                    # Turned on guiqwt's interactive mode
"""
    except ImportError:
        pass
    infos += """
Within Spyder, this interpreter also provides:
    * special commands (e.g. %ls, %pwd, %clear)
    * system commands, i.e. all commands starting with '!' are subprocessed
      (e.g. !dir on Windows or !ls on Linux, and so on)
"""
    __builtin__.scientific = _Printer("scientific", infos)

setscientific()
exec_print('Type "scientific" for more details.')

# Clean up the workspace
del setscientific, exec_print
