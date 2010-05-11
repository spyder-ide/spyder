# -*- coding: utf-8 -*-
#
# Copyright © 2009 Pierre Raybaut
# Licensed under the terms of the MIT License
# (see spyderlib/__init__.py for details)

"""
Module checking Spyder requirements (PyQt4, QScintilla2)
"""

def check_requirement(package, module_name, version_attr, required_str):
    wng = "\n%s v%s or higher is required" % (package, required_str)
    try:
        module = __import__(module_name)
    except ImportError:
        return wng+" (not found!)"
    else:
        if module_name.find('.'):
            module = getattr(module, module_name.split('.')[1])
        actual_str = getattr(module, version_attr)
        actual = actual_str.split('.')
        required = required_str.split('.')
        if actual[0] < required[0] or \
           (actual[0] == required[0] and actual[1] < required[1]):
            return wng+" (found v%s)" % actual_str
        else:
            return ''

def check_pyqt():
    wng = check_requirement("PyQt", "PyQt4.QtCore", "PYQT_VERSION_STR", "4.4")
    if wng:
        import os
        message = "Please check Spyder installation requirements:"+wng
        if os.name == 'nt':
            message += """
    
Windows XP/Vista/7 users:
QScintilla2 is distributed together with PyQt4
(Python(x,y) plugin or official PyQt4 Windows installer)"""
        try:
            # If Tkinter is installed (highly probable), showing an error pop-up
            import Tkinter, tkMessageBox
            root = Tkinter.Tk()
            root.withdraw()
            tkMessageBox.showerror("Spyder", message)
        except ImportError:
            pass
        raise ImportError, wng

check_pyqt()
