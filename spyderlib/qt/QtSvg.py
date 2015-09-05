# -*- coding: utf-8 -*-
#
# Copyright © 2012 Pierre Raybaut
# Licensed under the terms of the MIT License
# (see spyderlib/__init__.py for details)

import os

<<<<<<< HEAD
if os.environ['QT_API'] == 'pyqt':
    from PyQt4.QtSvg import *  # analysis:ignore
else:
    from PySide.QtSvg import *  # analysis:ignore
=======
if os.environ['QT_API'] == 'pyqt5':
    from PyQt5.QtSvg import *                                 # analysis:ignore
elif os.environ['QT_API'] == 'pyqt':
    from PyQt4.QtSvg import *                                 # analysis:ignore
else:
    from PySide.QtSvg import *                                # analysis:ignore
>>>>>>> 68da9235aabda2be32a6204ea08e3d1a37d3e12f
