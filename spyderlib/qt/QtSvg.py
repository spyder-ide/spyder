# -*- coding: utf-8 -*-
#
# Copyright © 2012 Pierre Raybaut
# Licensed under the terms of the MIT License
# (see spyderlib/__init__.py for details)

import os

if os.environ['QT_API'] == 'pyqt':
    from PyQt4.QtSvg import *  # analysis:ignore
else:
    from PySide.QtSvg import *  # analysis:ignore