# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""
This module contains the edge line numebr panel
"""

from qtpy.QtWidgets import QWidget
from qtpy.QtCore import Qt, QRect
from qtpy.QtGui import QPainter, QColor


class EdgeLine(QWidget):
    """Source code editor's edge line (default: 79 columns, PEP8)"""

    # --- Qt Overrides
    # -----------------------------------------------------------------
    def __init__(self, editor, color=Qt.darkGray):
        QWidget.__init__(self, editor)
        self.editor = editor
        self.column = 79
        self.color = color
        self.setAttribute(Qt.WA_TransparentForMouseEvents)

        self._enabled = True

    def paintEvent(self, event):
        """Override Qt method"""
        painter = QPainter(self)
        color = QColor(self.color)
        color.setAlphaF(.5)
        painter.fillRect(event.rect(), color)

    # --- Other methods
    # -----------------------------------------------------------------

    def set_enabled(self, state):
        """Toggle edge line visibility"""
        self._enabled = state
        self.setVisible(state)

    def set_column(self, column):
        """Set edge line column value"""
        self.column = column
        self.update()

    def set_geometry(self, cr):
        # 79-column edge line
        offset = self.editor.contentOffset()
        x = self.editor.blockBoundingGeometry(self.editor.firstVisibleBlock()) \
            .translated(offset.x(), offset.y()).left() \
            +self.editor.get_linenumberarea_width() \
            +self.editor.fontMetrics().width('9'*self.column)+5
        self.setGeometry(QRect(x, cr.top(), 1, cr.bottom()))
