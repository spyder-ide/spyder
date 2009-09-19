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

__version__ = '1.0.0beta9'
__license__ = __doc__

def check_required_package(package, actual_str, required_str):
    actual = actual_str.split('.')
    required = required_str.split('.')
    wng = ''
    if actual[0] < required[0] or \
       (actual[0] == required[0] and actual[1] < required[1]):
        wng = "\n%s v%s or higher is required (found v%s)" % (package,
                                                              required_str,
                                                              actual_str)
    return wng

def check_pyqt_qscintilla():
    from PyQt4.QtCore import PYQT_VERSION_STR
    wng = check_required_package("PyQt", PYQT_VERSION_STR, "4.4")
    from PyQt4.Qsci import QSCINTILLA_VERSION_STR
    wng += check_required_package("QScintilla", QSCINTILLA_VERSION_STR, "2.2")
    if wng:
        raise ImportError, wng
    
check_pyqt_qscintilla()