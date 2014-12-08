# -*- coding: utf-8 -*-
#
# Copyright © 2011-2012 Pierre Raybaut
#           © 2012-2014 anatoly techtonik
# Licensed under the terms of the MIT License
# (see spyderlib/__init__.py for details)

"""Transitional package (PyQt4 --> PySide)"""

import os

os.environ.setdefault('QT_API', 'pyqt')
assert os.environ['QT_API'] in ('pyqt', 'pyqtv1', 'pyside')

API = os.environ['QT_API']
API_NAME = None

if API == 'pyqt':
    # Spyder 2.3 is compatible with both #1 and #2 PyQt API,
    # but to avoid issues with IPython and other Qt plugins
    # we choose to support only API #2 for 2.4+
    try:
        import sip
        sip.setapi('QString', 2)
        sip.setapi('QVariant', 2)
    except ImportError:
        print('qt: PyQt4 is not found. Fallback to PySide API')
        API = os.environ['QT_API'] = 'pyside'
    except AttributeError:
        # PyQt < 4.6. Fallback to API #1
        print('qt: Fallback to PyQt4 API #1')
        API = os.environ['QT_API'] = 'pyqtv1'

if API in ('pyqtv1', 'pyqt'):
    try:
        from PyQt4.QtCore import PYQT_VERSION_STR as __version__
    except ImportError:
        # No PyQt4. Fallback to PySide
        print('qt: Fallback to PySide API')
        API = os.environ['QT_API'] = 'pyside'
    else:
        is_old_pyqt = __version__.startswith(('4.4', '4.5', '4.6', '4.7'))
        is_pyqt46 = __version__.startswith('4.6')
        import sip
        try:
            API_NAME = ("PyQt4 (API v%d)" % sip.getapi('QString'))
        except AttributeError:
            pass

if API == 'pyside':
    try:
        from PySide import __version__  # analysis:ignore
    except ImportError:
        raise ImportError("Spyder requires PySide or PyQt to be installed")
    else:
        is_old_pyqt = is_pyqt46 = False
    API_NAME = 'PySide'
