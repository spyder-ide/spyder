# -*- coding: utf-8 -*-
#
# Copyright © 2009-2010 Pierre Raybaut
# Licensed under the terms of the MIT License
# (see spyderlib/__init__.py for details)

"""
Module checking Spyder requirements
"""

def check_version(actual_str, required_str):
    """Return True if actual_str version fit required_str requirement"""
    actual = actual_str.split('.')
    required = required_str.split('.')
    return actual[0] < required[0] or \
           (actual[0] == required[0] and actual[1] < required[1])
    
def show_warning(message):
    """Show warning using Tkinter if available"""
    try:
        # If Tkinter is installed (highly probable), showing an error pop-up
        import Tkinter, tkMessageBox
        root = Tkinter.Tk()
        root.withdraw()
        tkMessageBox.showerror("Spyder", message)
    except ImportError:
        pass
    raise RuntimeError, message
    
def check_path():
    """Check sys.path: is Spyder properly installed?"""
    import sys, os.path as osp
    dirname = osp.abspath(osp.join(osp.dirname(__file__), osp.pardir))
    if dirname not in sys.path:
        show_warning("Spyder must be installed properly "
                     "(e.g. from source: 'python setup.py install'),\n"
                     "or directory '%s' must be in PYTHONPATH "
                     "environment variable" % dirname)

def check_qt():
    """Check Qt binding requirements"""
    import os
    from spyderlib import qt
    qt_api = os.environ['QT_API']
    required_str = dict(pyqt="4.4", pyside="1.0")[qt_api]
    actual_str = qt.__version__
    if check_version(actual_str, required_str):
        package = dict(pyqt="PyQt4", pyside="PySide")[qt_api]
        show_warning("Please check Spyder installation requirements:\n\n"
                     "%s v%s or higher is required (found v%s)"
                     % (package, required_str, actual_str))
