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
            sip.setapi('QString', 1)
    except ImportError:
        pass
