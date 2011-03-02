# -*- coding: utf-8 -*-
#
# Copyright © 2011 Pierre Raybaut
# Licensed under the terms of the MIT License
# (see spyderlib/__init__.py for details)

import os

if os.environ['PYTHON_QT_LIBRARY'] == 'PyQt4':
    from PyQt4.QtCore import *
    def QVariant(obj=None):
        import PyQt4.QtCore
        return PyQt4.QtCore.QVariant(obj)
    from PyQt4.Qt import QCoreApplication
    from PyQt4.Qt import Qt
else:
    PYQT_VERSION_STR = ''
    from PySide.QtCore import *
    def QVariant(obj=None):
        return obj
