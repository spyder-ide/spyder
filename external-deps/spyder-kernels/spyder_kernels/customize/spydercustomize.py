#
# Copyright (c) 2009- Spyder Kernels Contributors
#
# Licensed under the terms of the MIT License
# (see spyder_kernels/__init__.py for details)
# -----------------------------------------------------------------------------
#
# IMPORTANT NOTE: Don't add a coding line here! It's not necessary for
# site files
#
# Spyder consoles sitecustomize
#

import logging
import os
import pdb
import sys
import warnings

from spyder_kernels.customize.spyderpdb import SpyderPdb


# =============================================================================
# sys.argv can be missing when Python is embedded, taking care of it.
# Fixes Issue 1473 and other crazy crashes with IPython 0.13 trying to
# access it.
# =============================================================================
if not hasattr(sys, 'argv'):
    sys.argv = ['']

# =============================================================================
# Main constants
# =============================================================================
IS_EXT_INTERPRETER = os.environ.get('SPY_EXTERNAL_INTERPRETER') == "True"
HIDE_CMD_WINDOWS = os.environ.get('SPY_HIDE_CMD') == "True"

# =============================================================================
# Prevent subprocess.Popen calls to create visible console windows on Windows.
# See issue #4932
# =============================================================================
if os.name == 'nt' and HIDE_CMD_WINDOWS:
    import subprocess
    creation_flag = 0x08000000  # CREATE_NO_WINDOW

    class SubprocessPopen(subprocess.Popen):
        def __init__(self, *args, **kwargs):
            kwargs['creationflags'] = creation_flag
            super(SubprocessPopen, self).__init__(*args, **kwargs)

    subprocess.Popen = SubprocessPopen

# =============================================================================
# Importing user's sitecustomize
# =============================================================================
try:
    import sitecustomize  #analysis:ignore
except Exception:
    pass

# =============================================================================
# Set PyQt API to #2
# =============================================================================
if os.environ.get("QT_API") == 'pyqt':
    try:
        import sip
        for qtype in ('QString', 'QVariant', 'QDate', 'QDateTime',
                      'QTextStream', 'QTime', 'QUrl'):
            sip.setapi(qtype, 2)
    except Exception:
        pass
else:
    try:
        os.environ.pop('QT_API')
    except KeyError:
        pass


# =============================================================================
# Patch PyQt4 and PyQt5
# =============================================================================
# This saves the QApplication instances so that Python doesn't destroy them.
# Python sees all the QApplication as differnet Python objects, while
# Qt sees them as a singleton (There is only one Application!). Deleting one
# QApplication causes all the other Python instances to become broken.
# See spyder-ide/spyder/issues/2970
try:
    from PyQt5 import QtWidgets

    class SpyderQApplication(QtWidgets.QApplication):
        def __init__(self, *args, **kwargs):
            super(SpyderQApplication, self).__init__(*args, **kwargs)
            # Add reference to avoid destruction
            # This creates a Memory leak but avoids a Segmentation fault
            SpyderQApplication._instance_list.append(self)

    SpyderQApplication._instance_list = []
    QtWidgets.QApplication = SpyderQApplication
except Exception:
    pass

try:
    from PyQt4 import QtGui

    class SpyderQApplication(QtGui.QApplication):
        def __init__(self, *args, **kwargs):
            super(SpyderQApplication, self).__init__(*args, **kwargs)
            # Add reference to avoid destruction
            # This creates a Memory leak but avoids a Segmentation fault
            SpyderQApplication._instance_list.append(self)

    SpyderQApplication._instance_list = []
    QtGui.QApplication = SpyderQApplication
except Exception:
    pass


# =============================================================================
# IPython adjustments
# =============================================================================
# Patch unittest.main so that errors are printed directly in the console.
# See http://comments.gmane.org/gmane.comp.python.ipython.devel/10557
# Fixes Issue 1370
import unittest
from unittest import TestProgram

class IPyTesProgram(TestProgram):
    def __init__(self, *args, **kwargs):
        test_runner = unittest.TextTestRunner(stream=sys.stderr)
        kwargs['testRunner'] = kwargs.pop('testRunner', test_runner)
        kwargs['exit'] = False
        TestProgram.__init__(self, *args, **kwargs)

unittest.main = IPyTesProgram

# Ignore some IPython/ipykernel warnings
try:
    warnings.filterwarnings(action='ignore', category=DeprecationWarning,
                            module='ipykernel.ipkernel')
except Exception:
    pass


# =============================================================================
# Turtle adjustments
# =============================================================================
# This is needed to prevent turtle scripts crashes after multiple runs in the
# same IPython Console instance.
# See Spyder issue #6278
try:
    import turtle
    from turtle import Screen, Terminator

    def spyder_bye():
        try:
            Screen().bye()
            turtle.TurtleScreen._RUNNING = True
        except Terminator:
            pass
    turtle.bye = spyder_bye
except Exception:
    pass


# =============================================================================
# Pandas adjustments
# =============================================================================
try:
    import pandas as pd

    # Set Pandas output encoding
    pd.options.display.encoding = 'utf-8'

    # Filter warning that appears for DataFrames with np.nan values
    # Example:
    # >>> import pandas as pd, numpy as np
    # >>> pd.Series([np.nan,np.nan,np.nan],index=[1,2,3])
    # Fixes Issue 2991
    # For 0.18-
    warnings.filterwarnings(action='ignore', category=RuntimeWarning,
                            module='pandas.core.format',
                            message=".*invalid value encountered in.*")
    # For 0.18.1+
    warnings.filterwarnings(action='ignore', category=RuntimeWarning,
                            module='pandas.formats.format',
                            message=".*invalid value encountered in.*")
except Exception:
    pass


# =============================================================================
# Numpy adjustments
# =============================================================================
try:
    # Filter warning that appears when users have 'Show max/min'
    # turned on and Numpy arrays contain a nan value.
    # Fixes Issue 7063
    # Note: It only happens in Numpy 1.14+
    warnings.filterwarnings(action='ignore', category=RuntimeWarning,
                            module='numpy.core._methods',
                            message=".*invalid value encountered in.*")
except Exception:
    pass


# =============================================================================
# Multiprocessing adjustments
# =============================================================================
# This could fail with changes in Python itself, so we protect it
# with a try/except
try:
    import multiprocessing.spawn
    _old_preparation_data = multiprocessing.spawn.get_preparation_data

    def _patched_preparation_data(name):
        """
        Patched get_preparation_data to work when all variables are
        removed before execution.
        """
        try:
            d = _old_preparation_data(name)
        except AttributeError:
            main_module = sys.modules['__main__']
            # Any string for __spec__ does the job
            main_module.__spec__ = ''
            d = _old_preparation_data(name)
        # On windows, there is no fork, so we need to save the main file
        # and import it
        if (os.name == 'nt' and 'init_main_from_path' in d
                and not os.path.exists(d['init_main_from_path'])):
            print(
                "Warning: multiprocessing may need the main file to exist. "
                "Please save {}".format(d['init_main_from_path']))
            # Remove path as the subprocess can't do anything with it
            del d['init_main_from_path']
        return d
    multiprocessing.spawn.get_preparation_data = _patched_preparation_data
except Exception:
    pass


# =============================================================================
# os adjustments
# =============================================================================
# This is necessary to have better support for Rich and Colorama.
def _patched_get_terminal_size(fd=None):
    return os.terminal_size((80, 30))

os.get_terminal_size = _patched_get_terminal_size


# =============================================================================
# Pdb adjustments
# =============================================================================
pdb.Pdb = SpyderPdb

# =============================================================================
# PYTHONPATH and sys.path Adjustments
# =============================================================================
# PYTHONPATH is not passed to kernel directly, see spyder-ide/spyder#13519
# This allows the kernel to start without crashing if modules in PYTHONPATH
# shadow standard library modules.
def set_spyder_pythonpath():
    pypath = os.environ.get('SPY_PYTHONPATH')
    if pypath:
        sys.path.extend(pypath.split(os.pathsep))
        os.environ.update({'PYTHONPATH': pypath})

set_spyder_pythonpath()
