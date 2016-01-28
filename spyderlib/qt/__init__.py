# -*- coding: utf-8 -*-
#
# Copyright © 2011-2012 Pierre Raybaut
#           © 2012-2014 anatoly techtonik
# Licensed under the terms of the MIT License
# (see spyderlib/__init__.py for details)

"""Spyder Qt Shim"""

import os

os.environ.setdefault('QT_API', 'pyqt5')
assert os.environ['QT_API'] in ('pyqt5', 'pyqt', 'pyside')

API = os.environ['QT_API']
API_NAME = {'pyqt5': 'PyQt5', 'pyqt': 'PyQt4', 'pyside': 'PySide'}[API]

is_old_pyqt = is_pyqt46 = False
PYQT5 = True

if API == 'pyqt5':
    try:
        from PyQt5.QtCore import PYQT_VERSION_STR as __version__
        from PyQt5 import uic  # analysis:ignore
    except ImportError:
        API = os.environ['QT_API'] = 'pyqt'
        API_NAME = 'PyQt4'

if API == 'pyqt':
    try:
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

        from PyQt4.QtCore import PYQT_VERSION_STR as __version__ # analysis:ignore
        from PyQt4 import uic  # analysis:ignore
        PYQT5 = False
    except ImportError:
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
        PYQT5 = False
    except ImportError:
        raise ImportError("Spyder requires PyQt5, PyQt4 or PySide (deprecated) "
                          "to be installed")
