# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""
Scientific Python startup script

Requires NumPy, SciPy and Matplotlib
"""

# Need a temporary print function that is Python version agnostic.
import sys
import os

def exec_print(string="", end_space=False):
    if sys.version[0] == '2':
        if end_space:
            exec("print '" + string + "',")  # spyder: test-skip
        else:
            exec("print '" + string + "'")  # spyder: test-skip
    else:
        if end_space:
            exec("print('" + string + "', end=' ')")  # spyder: test-skip
        else:
            exec("print('" + string + "')")  # spyder: test-skip


#==============================================================================
# Pollute the namespace but also provide MATLAB-like experience
#==============================================================================
try:
    from pylab import *  #analysis:ignore
    # Enable Matplotlib's interactive mode:
    ion()
except ImportError:
    pass

# Import modules following official guidelines:
try:
    import numpy as np
    __has_numpy = True
except ImportError:
    __has_numpy = False

try:
    import scipy as sp
    __has_scipy = True
except ImportError:
    __has_scipy = False

try:
    import matplotlib as mpl
    import matplotlib.pyplot as plt  #analysis:ignore
    __has_matplotlib = True
except ImportError:
    __has_matplotlib = False

__has_guiqwt = False
if os.environ.get('QT_API') != 'pyside':
    try:
        import guiqwt
        import guiqwt.pyplot as plt_
        import guidata
        plt_.ion()
        __has_guiqwt = True
    except (ImportError, AssertionError):
        pass

#==============================================================================
# Print what modules have been imported
#==============================================================================
__imports = []
if __has_numpy:
    __imports.append("NumPy {}".format(np.__version__))
if __has_scipy:
    __imports.append("SciPy {}".format(sp.__version__))
if __has_matplotlib:
    __imports.append("Matplotlib {}".format(mpl.__version__))
if __has_guiqwt:
    __imports.append("guidata {}".format(guidata.__version__))
    __imports.append("guiqwt {}".format(guiqwt.__version__))

exec_print()
if __imports:
    exec_print("Imported " + ", ".join(__imports))
exec_print()

#==============================================================================
# Add help about the "scientific" command
#==============================================================================
def setscientific():
    """Set 'scientific' in __builtin__"""
    infos = ""
    
    if __has_numpy:
        infos += """
This is a standard Python interpreter with preloaded tools for scientific 
computing and visualization. It tries to import the following modules:

>>> import numpy as np  # NumPy (multidimensional arrays, linear algebra, ...)"""

    if __has_scipy:
        infos += """
>>> import scipy as sp  # SciPy (signal and image processing library)"""

    if __has_matplotlib:
        infos += """
>>> import matplotlib as mpl         # Matplotlib (2D/3D plotting library)
>>> import matplotlib.pyplot as plt  # Matplotlib's pyplot: MATLAB-like syntax
>>> from pylab import *              # Matplotlib's pylab interface
>>> ion()                            # Turned on Matplotlib's interactive mode"""
    
    if __has_guiqwt:
        infos += """
>>> import guidata  # GUI generation for easy dataset editing and display

>>> import guiqwt                 # Efficient 2D data-plotting features
>>> import guiqwt.pyplot as plt_  # guiqwt's pyplot: MATLAB-like syntax
>>> plt_.ion()                    # Turned on guiqwt's interactive mode"""
    
    if __imports:
        infos += "\n"

    infos += """
Within Spyder, this interpreter also provides:
    * special commands (e.g. %ls, %cd, %pwd, %clear)
      - %ls:      List files in the current directory
      - %cd dir:  Change to directory dir
      - %pwd:     Show current directory
      - %clear x: Remove variable x from namespace
"""
    try:
        # Python 2
        import __builtin__ as builtins
    except ImportError:
        # Python 3
        import builtins
    try:
        from site import _Printer
    except ImportError:
        # Python 3.4
        from _sitebuiltins import _Printer
    builtins.scientific = _Printer("scientific", infos)


setscientific()
exec_print('Type "scientific" for more details.')

#==============================================================================
# Delete temp vars
#==============================================================================
del setscientific, __has_numpy, __has_scipy, __has_matplotlib, __has_guiqwt, __imports, exec_print
