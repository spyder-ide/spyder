# -*- coding: utf-8 -*-
#
# Copyright © 2011 Pierre Raybaut
# Licensed under the terms of the MIT License
# (see spyderlib/__init__.py for details)

"""Transitional package (PyQt4 --> PySide)"""

import imp, os

for _modname in ('PySide', 'PyQt4'):
    try:
        imp.find_module(_modname)
        os.environ['PYTHON_QT_LIBRARY'] = _modname
        if _modname == 'PyQt4':
            import sip
            try:
                sip.setapi('QString', 1)
            except AttributeError:
                # PyQt < v4.6: in future version, we should warn the user 
                # that PyQt is outdated and won't be supported by Spyder >v2.1
                pass
    except ImportError:
        pass
