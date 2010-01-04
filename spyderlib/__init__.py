# -*- coding: utf-8 -*-
"""
Spyder License Agreement (MIT License)
--------------------------------------

Copyright (c) 2009 Pierre Raybaut

Permission is hereby granted, free of charge, to any person
obtaining a copy of this software and associated documentation
files (the "Software"), to deal in the Software without
restriction, including without limitation the rights to use,
copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the
Software is furnished to do so, subject to the following
conditions:

The above copyright notice and this permission notice shall be
included in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES
OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT
HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY,
WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR
OTHER DEALINGS IN THE SOFTWARE.
"""

__version__ = '1.0.2'
__license__ = __doc__

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

def check_pyqt_qscintilla():
    wng = check_requirement("PyQt", "PyQt4.QtCore", "PYQT_VERSION_STR", "4.4")
    wng += check_requirement("QScintilla", "PyQt4.Qsci",
                             "QSCINTILLA_VERSION_STR", "2.2")
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

check_pyqt_qscintilla()
