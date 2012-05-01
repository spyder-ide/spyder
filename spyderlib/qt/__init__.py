# -*- coding: utf-8 -*-
#
# Copyright © 2011 Pierre Raybaut
# Licensed under the terms of the MIT License
# (see spyderlib/__init__.py for details)

"""Transitional package (PyQt4 --> PySide)"""

import os

os.environ.setdefault('QT_API', 'pyqt')
assert os.environ['QT_API'] in ('pyqt', 'pyside')

API = os.environ['QT_API']
API_NAME = {'pyqt': 'PyQt4', 'pyside': 'PySide'}[API]

if API == 'pyqt':
    # We do not force QString, QVariant, ... API to #1 or #2 anymore 
    # as spyderlib is now compatible with both APIs
#    import sip
#    try:
#        sip.setapi('QString', 2)
#        sip.setapi('QVariant', 2)
#    except AttributeError:
#        # PyQt < v4.6: in future version, we should warn the user 
#        # that PyQt is outdated and won't be supported by Spyder >v2.1
#        pass
    try:
        from PyQt4.QtCore import PYQT_VERSION_STR as __version__
    except ImportError:
        # Switching to PySide
        API = os.environ['QT_API'] = 'pyside'
        API_NAME = 'PySide'
    else:
        __version_info__ = tuple(__version__.split('.')+['final', 1])
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
