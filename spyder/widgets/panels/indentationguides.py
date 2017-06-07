# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""
This module contains the indentation guide panel
"""

from qtpy.QtWidgets import QWidget
from qtpy.QtCore import Qt, QRect, QPoint
from qtpy.QtGui import QPainter, QColor


class IndentationGuide(QWidget):
    """Source code editor's edge line (default: 79 columns, PEP8)"""

    # --- Qt Overrides
    # -----------------------------------------------------------------
    def __init__(self, editor, color=Qt.darkGray, indentation_width=4):
        QWidget.__init__(self, editor)
        self.editor = editor
        self.color = color
        self.i_width = indentation_width

        self.setAttribute(Qt.WA_TransparentForMouseEvents)
        self._enabled = True

    def paintEvent(self, event):
        """Override Qt method"""
        painter = QPainter(self)

        color = QColor(self.color)
        color.setAlphaF(.5)
        painter.setPen(color)

        for top, line_number, block in self.editor.visible_blocks:
            bottom = top + int(self.editor.blockBoundingRect(block).height())

            # replace tabs for spaces
            text = block.text().replace('\t', ' ' * self.i_width)

            indentation = len(text) -len(text.lstrip())
            for i in range(self.i_width, indentation, self.i_width):
                x = self.editor.fontMetrics().width(i * '9')
                painter.drawLine(x, top, x, bottom)

    # --- Other methods
    # -----------------------------------------------------------------

    def set_enabled(self, state):
        """Toggle edge line visibility"""
        self._enabled = state
        self.setVisible(state)

    def update_color(self):
        """
        Set edgeline color using syntax highlighter color for comments
        """
        self.color = self.editor.highlighter.get_color_name('comment')

    def set_indentation_width(self, indentation_width):
        """Set indentation width to be used to draw indent guides."""
        self.i_width = indentation_width

    def set_geometry(self, cr):
        """Calculate and set geometry of edge line panel.
            start --> fist line position
            width --> max position - min position
        """
        offset = self.editor.contentOffset()
        x = self.editor.blockBoundingGeometry(self.editor.firstVisibleBlock()) \
            .translated(offset.x(), offset.y()).left() + 5

        top_left = QPoint(x, cr.top())
        top_left = self.editor.calculate_real_position(top_left)
        bottom_right = QPoint(top_left.x() + cr.width(), cr.bottom())

        self.setGeometry(QRect(top_left, bottom_right))
