# -*- coding: utf-8 -*-
#
# Copyright © 2011-2012 Pierre Raybaut
#           © 2012-2014 anatoly techtonik
# Licensed under the terms of the MIT License
# (see spyderlib/__init__.py for details)

"""Transitional package (PyQt4 --> PySide)"""

import os
import imp

try:
    #be friendly with Pyqt5
    are_you_here = __import__('PyQt5')
    os.environ.setdefault('QT_API','pyqt5')
except:
    os.environ.setdefault('QT_API', 'pyqt')

assert os.environ['QT_API'] in ('pyqt5', 'pyqt', 'pyside')

API = os.environ['QT_API']
API_NAME = {'pyqt5': 'PyQt5', 'pyqt': 'PyQt4', 'pyside': 'PySide'}[API]

PYQT5 = False

if API == 'pyqt5':
    try:
        from PyQt5.QtCore import PYQT_VERSION_STR as __version__
        is_old_pyqt = False
        is_pyqt46 = False
        PYQT5 = True
    except ImportError:
        pass
elif API == 'pyqt':
    # Spyder 2.3 is compatible with both #1 and #2 PyQt API,
    # but to avoid issues with IPython and other Qt plugins
    # we choose to support only API #2 for 2.4+
    import sip
    try:
        sip.setapi('QString', 2)
        sip.setapi('QVariant', 2)
        sip.setapi('QDate', 2)
        sip.setapi('QDateTime', 2)
        sip.setapi('QTextStream', 2)
        sip.setapi('QTime', 2)
        sip.setapi('QUrl', 2)
    except AttributeError:
        # PyQt < v4.6. The actual check is done by requirements.check_qt()
        # call from spyder.py
        pass

    try:
        from PyQt4.QtCore import PYQT_VERSION_STR as __version__ # analysis:ignore
    except ImportError:
        # Switching to PySide
        API = os.environ['QT_API'] = 'pyside'
        API_NAME = 'PySide'
    else:
        is_old_pyqt = __version__.startswith(('4.4', '4.5', '4.6', '4.7'))
        is_pyqt46 = __version__.startswith('4.6')
        import sip
        try:
            API_NAME += (" (API v%d)" % sip.getapi('QString'))
        except AttributeError:
            pass

if API == 'pyside':
    try:
        from PySide import __version__  # analysis:ignore
    except ImportError:
        raise ImportError("Spyder requires PySide or PyQt to be installed")
    else:
        is_old_pyqt = is_pyqt46 = False
