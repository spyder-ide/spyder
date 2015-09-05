# -*- coding: utf-8 -*-
#
# Copyright © 2011 Pierre Raybaut
# Licensed under the terms of the MIT License
# (see spyderlib/__init__.py for details)

import os

<<<<<<< HEAD
if os.environ['QT_API'] == 'pyqt':
    from PyQt4.Qt import QKeySequence, QTextCursor  # analysis:ignore
    from PyQt4.QtGui import *  # analysis:ignore
else:
    from PySide.QtGui import *  # analysis:ignore
=======
if os.environ['QT_API'] == 'pyqt5':
    from PyQt5.QtCore import QSortFilterProxyModel            # analysis:ignore
    from PyQt5.QtPrintSupport import (QPrinter, QPrintDialog, # analysis:ignore
                                      QAbstractPrintDialog)
    from PyQt5.QtPrintSupport import QPrintPreviewDialog      # analysis:ignore
    from PyQt5.QtGui import *                                 # analysis:ignore
    from PyQt5.QtWidgets import *                             # analysis:ignore
elif os.environ['QT_API'] == 'pyqt':
    from PyQt4.Qt import QKeySequence, QTextCursor            # analysis:ignore
    from PyQt4.QtGui import *                                 # analysis:ignore
    QStyleOptionViewItem = QStyleOptionViewItemV4             # analysis:ignore
else:
    from PySide.QtGui import *                                # analysis:ignore
    QStyleOptionViewItem = QStyleOptionViewItemV4             # analysis:ignore
>>>>>>> 68da9235aabda2be32a6204ea08e3d1a37d3e12f
