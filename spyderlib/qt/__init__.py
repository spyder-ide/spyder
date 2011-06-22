# -*- coding: utf-8 -*-
#
# Copyright © 2011 Pierre Raybaut
# Licensed under the terms of the MIT License
# (see spyderlib/__init__.py for details)

"""Transitional package (PyQt4 --> PySide)"""

import os

_modname = os.environ.setdefault('PYTHON_QT_LIBRARY', 'PyQt4')
assert _modname in ('PyQt4', 'PySide')

if _modname == 'PyQt4':
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
        __version_info__ = tuple(__version__.split('.')+['final', 1])
        is_pyqt46 = __version__.startswith('4.6')
    except ImportError:
        # Switching to PySide
        os.environ['PYTHON_QT_LIBRARY'] = _modname = 'PySide'

if _modname == 'PySide':
    import PySide
    __version__ = PySide.__version__
    from PySide import *
    is_pyqt46 = False
