# -*- coding: utf-8 -*-
#
# Copyright © 2011 Pierre Raybaut
# Licensed under the terms of the MIT License
# (see spyderlib/__init__.py for details)

import os

if os.environ['QT_API'] == 'pyqt5':
    from PyQt5.QtNetwork import *  # analysis:ignore
elif os.environ['QT_API'] == 'pyqt':
    from PyQt4.QtNetwork import *  # analysis:ignore
else:
    from PySide.QtNetwork import *  # analysis:ignore
