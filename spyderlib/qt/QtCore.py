# -*- coding: utf-8 -*-
#
# Copyright © 2011 Pierre Raybaut
# Licensed under the terms of the MIT License
# (see spyderlib/__init__.py for details)

import os

if os.environ['QT_API'] == 'pyqt':
    from PyQt4.QtCore import *  # analysis:ignore
    from PyQt4.QtCore import QCoreApplication  # analysis:ignore
    from PyQt4.QtCore import Qt  # analysis:ignore
    from PyQt4.QtCore import pyqtSignal as Signal  # analysis:ignore
    from PyQt4.QtCore import pyqtSlot as Slot  # analysis:ignore
    from PyQt4.QtCore import pyqtProperty as Property  # analysis:ignore
    from PyQt4.QtCore import QT_VERSION_STR as __version__
else:
    import PySide.QtCore
    __version__ = PySide.QtCore.__version__  # analysis:ignore
    from PySide.QtCore import *  # analysis:ignore
