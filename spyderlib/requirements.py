# -*- coding: utf-8 -*-
#
# Copyright © 2009-2010 Pierre Raybaut
# Licensed under the terms of the MIT License
# (see spyderlib/__init__.py for details)

"""
Module checking Spyder requirements
"""

def check_requirement(package, module_name, version_attr, required_str):
    wng = "\n%s v%s or higher is required" % (package, required_str)
    try:
        module = __import__(module_name)
    except ImportError:
        return wng+" (not found!)"
    else:
        if '.' in module_name:
            module = getattr(module, module_name.split('.')[1])
        actual_str = getattr(module, version_attr)
        actual = actual_str.split('.')
        required = required_str.split('.')
        if actual[0] < required[0] or \
           (actual[0] == required[0] and actual[1] < required[1]):
            return wng+" (found v%s)" % actual_str
        else:
            return ''
    
def show_warning(message):
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
    import sys, os.path as osp
    dirname = osp.abspath(osp.join(osp.dirname(__file__), osp.pardir))
    if dirname not in sys.path:
        show_warning("Spyder must be installed properly "
                     "(e.g. from source: 'python setup.py install'),\n"
                     "or directory '%s' must be in PYTHONPATH "
                     "environment variable" % dirname)

def check_qt():
    wng1 = check_requirement("PyQt", "PyQt4.QtCore", "PYQT_VERSION_STR", "4.4")
    wng2 = check_requirement("PySide", "PySide", "__version__", "1.0")
    if wng1 and wng2:
        show_warning("Please check Spyder installation requirements:\n"
                     +wng1+"\nor"+wng2)
