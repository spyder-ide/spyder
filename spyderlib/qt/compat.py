# -*- coding: utf-8 -*-
#
# Copyright © 2011-2012 Pierre Raybaut
# Licensed under the terms of the MIT License
# (see spyderlib/__init__.py for details)

"""
spyderlib.qt.compat
-------------------

Transitional module providing compatibility functions intended to help 
migrating from PyQt to PySide.

This module should be fully compatible with:
    * PyQt >=v4.4
    * both PyQt API #1 and API #2
    * PySide
"""

from __future__ import print_function

import os
import sys
import collections

from spyderlib.qt.QtGui import QFileDialog

from spyderlib.py3compat import is_text_string, to_text_string, TEXT_TYPES

#==============================================================================
# QVariant conversion utilities
#==============================================================================

PYQT_API_1 = False
if os.environ['QT_API'] == 'pyqt':
    import sip
    try:
        PYQT_API_1 = sip.getapi('QVariant') == 1 # PyQt API #1
    except AttributeError:
        # PyQt <v4.6
        PYQT_API_1 = True
    def to_qvariant(pyobj=None):
        """Convert Python object to QVariant
        This is a transitional function from PyQt API #1 (QVariant exist) 
        to PyQt API #2 and Pyside (QVariant does not exist)"""
        if PYQT_API_1:
            # PyQt API #1
            from PyQt4.QtCore import QVariant
            return QVariant(pyobj)
        else:
            # PyQt API #2
            return pyobj
    def from_qvariant(qobj=None, convfunc=None):
        """Convert QVariant object to Python object
        This is a transitional function from PyQt API #1 (QVariant exist) 
        to PyQt API #2 and Pyside (QVariant does not exist)"""
        if PYQT_API_1:
            # PyQt API #1
            assert isinstance(convfunc, collections.Callable)
            if convfunc in TEXT_TYPES or convfunc is to_text_string:
                return convfunc(qobj.toString())
            elif convfunc is bool:
                return qobj.toBool()
            elif convfunc is int:
                return qobj.toInt()[0]
            elif convfunc is float:
                return qobj.toDouble()[0]
            else:
                return convfunc(qobj)
        else:
            # PyQt API #2
            return qobj
else:
    def to_qvariant(obj=None):  # analysis:ignore
        """Convert Python object to QVariant
        This is a transitional function from PyQt API#1 (QVariant exist) 
        to PyQt API#2 and Pyside (QVariant does not exist)"""
        return obj
    def from_qvariant(qobj=None, pytype=None):  # analysis:ignore
        """Convert QVariant object to Python object
        This is a transitional function from PyQt API #1 (QVariant exist) 
        to PyQt API #2 and Pyside (QVariant does not exist)"""
        return qobj

#==============================================================================
# Wrappers around QFileDialog static methods
#==============================================================================

def getexistingdirectory(parent=None, caption='', basedir='',
                         options=QFileDialog.ShowDirsOnly):
    """Wrapper around QtGui.QFileDialog.getExistingDirectory static method
    Compatible with PyQt >=v4.4 (API #1 and #2) and PySide >=v1.0"""
    # Calling QFileDialog static method
    if sys.platform == "win32":
        # On Windows platforms: redirect standard outputs
        _temp1, _temp2 = sys.stdout, sys.stderr
        sys.stdout, sys.stderr = None, None
    try:
        result = QFileDialog.getExistingDirectory(parent, caption, basedir,
                                                  options)
    finally:
        if sys.platform == "win32":
            # On Windows platforms: restore standard outputs
            sys.stdout, sys.stderr = _temp1, _temp2
    if not is_text_string(result):
        # PyQt API #1
        result = to_text_string(result)
    return result

def _qfiledialog_wrapper(attr, parent=None, caption='', basedir='',
                         filters='', selectedfilter='', options=None):
    if options is None:
        options = QFileDialog.Options(0)
    try:
        # PyQt <v4.6 (API #1)
        from spyderlib.qt.QtCore import QString
    except ImportError:
        # PySide or PyQt >=v4.6
        QString = None  # analysis:ignore
    tuple_returned = True
    try:
        # PyQt >=v4.6
        func = getattr(QFileDialog, attr+'AndFilter')
    except AttributeError:
        # PySide or PyQt <v4.6
        func = getattr(QFileDialog, attr)
        if QString is not None:
            selectedfilter = QString()
            tuple_returned = False
    
    # Calling QFileDialog static method
    if sys.platform == "win32":
        # On Windows platforms: redirect standard outputs
        _temp1, _temp2 = sys.stdout, sys.stderr
        sys.stdout, sys.stderr = None, None
    try:
        result = func(parent, caption, basedir,
                      filters, selectedfilter, options)
    except TypeError:
        # The selectedfilter option (`initialFilter` in Qt) has only been 
        # introduced in Jan. 2010 for PyQt v4.7, that's why we handle here 
        # the TypeError exception which will be raised with PyQt v4.6
        # (see Issue 960 for more details)
        result = func(parent, caption, basedir, filters, options)
    finally:
        if sys.platform == "win32":
            # On Windows platforms: restore standard outputs
            sys.stdout, sys.stderr = _temp1, _temp2
            
    # Processing output
    if tuple_returned:
        # PySide or PyQt >=v4.6
        output, selectedfilter = result
    else:
        # PyQt <v4.6 (API #1)
        output = result
    if QString is not None:
        # PyQt API #1: conversions needed from QString/QStringList
        selectedfilter = to_text_string(selectedfilter)
        if isinstance(output, QString):
            # Single filename
            output = to_text_string(output)
        else:
            # List of filenames
            output = [to_text_string(fname) for fname in output]
            
    # Always returns the tuple (output, selectedfilter)
    return output, selectedfilter

def getopenfilename(parent=None, caption='', basedir='', filters='',
                    selectedfilter='', options=None):
    """Wrapper around QtGui.QFileDialog.getOpenFileName static method
    Returns a tuple (filename, selectedfilter) -- when dialog box is canceled,
    returns a tuple of empty strings
    Compatible with PyQt >=v4.4 (API #1 and #2) and PySide >=v1.0"""
    return _qfiledialog_wrapper('getOpenFileName', parent=parent,
                                caption=caption, basedir=basedir,
                                filters=filters, selectedfilter=selectedfilter,
                                options=options)

def getopenfilenames(parent=None, caption='', basedir='', filters='',
                     selectedfilter='', options=None):
    """Wrapper around QtGui.QFileDialog.getOpenFileNames static method
    Returns a tuple (filenames, selectedfilter) -- when dialog box is canceled,
    returns a tuple (empty list, empty string)
    Compatible with PyQt >=v4.4 (API #1 and #2) and PySide >=v1.0"""
    return _qfiledialog_wrapper('getOpenFileNames', parent=parent,
                                caption=caption, basedir=basedir,
                                filters=filters, selectedfilter=selectedfilter,
                                options=options)

def getsavefilename(parent=None, caption='', basedir='', filters='',
                    selectedfilter='', options=None):
    """Wrapper around QtGui.QFileDialog.getSaveFileName static method
    Returns a tuple (filename, selectedfilter) -- when dialog box is canceled,
    returns a tuple of empty strings
    Compatible with PyQt >=v4.4 (API #1 and #2) and PySide >=v1.0"""
    return _qfiledialog_wrapper('getSaveFileName', parent=parent,
                                caption=caption, basedir=basedir,
                                filters=filters, selectedfilter=selectedfilter,
                                options=options)

if __name__ == '__main__':
    from spyderlib.utils.qthelpers import qapplication
    _app = qapplication()
    print(repr(getexistingdirectory()))
    print(repr(getopenfilename(filters='*.py;;*.txt')))
    print(repr(getopenfilenames(filters='*.py;;*.txt')))
    print(repr(getsavefilename(filters='*.py;;*.txt')))
    sys.exit()
