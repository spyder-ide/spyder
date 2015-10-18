# -*- coding: utf-8 -*-
#
# Copyright © 2011 Pierre Raybaut
# Licensed under the terms of the MIT License
# (see spyderlib/__init__.py for details)

import os

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
    del QItemSelection, QItemSelectionRange                   # analysis:ignore
else:
    from PySide.QtGui import *                                # analysis:ignore
    QStyleOptionViewItem = QStyleOptionViewItemV4             # analysis:ignore
    del QItemSelection, QItemSelectionRange                   # analysis:ignore
