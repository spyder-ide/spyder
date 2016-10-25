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
    def __init__(self, editor, colors=[Qt.darkGray], columns=[79]):
        QWidget.__init__(self, editor)
        self.editor = editor
        self.columns = columns
        self.colors = colors
        self.setAttribute(Qt.WA_TransparentForMouseEvents)

        self._enabled = True

    def paintEvent(self, event):
        """Override Qt method"""
        painter = QPainter(self)
        size = self.size()

        offsets = [col - min(self.columns) for col in self.columns]
        for offset, qcolor in zip(offsets, self.colors):
            color = QColor(qcolor)
            color.setAlphaF(.5)
            painter.setPen(color)

            x = self.editor.fontMetrics().width(offset * '9')
            painter.drawLine(x, 0, x, size.height())

    # --- Other methods
    # -----------------------------------------------------------------

    def set_enabled(self, state):
        """Toggle edge line visibility"""
        self._enabled = state
        self.setVisible(state)

    def set_column(self, column, index=0):
        """Set edge line column value"""
        self.columns[index] = column
        self.update()

    def set_geometry(self, cr):
        """Calculate and set geometry of edge line panel.
            start --> fist line position
            width --> max position - min position
        """
        width = self.editor.fontMetrics().width('9'*(max(self.columns) - min(self.columns))) + 1
        offset = self.editor.contentOffset()
        x = self.editor.blockBoundingGeometry(self.editor.firstVisibleBlock()) \
            .translated(offset.x(), offset.y()).left() \
            +self.editor.linenumberarea.get_width() \
            +self.editor.fontMetrics().width('9'*min(self.columns))+5
        self.setGeometry(QRect(x, cr.top(), width, cr.bottom()))
