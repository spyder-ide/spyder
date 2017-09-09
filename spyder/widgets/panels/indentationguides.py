# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""
This module contains the indentation guide panel.
"""

from qtpy.QtCore import Qt, QRect, QPoint
from qtpy.QtGui import QPainter, QColor

from spyder.utils.editor import TextBlockHelper
from spyder.api.panel import Panel

class IndentationGuide(Panel):
    """Indentation guides to easy identify nested blocks."""

    # --- Qt Overrides
    # -----------------------------------------------------------------
    def __init__(self, editor):
        """Initialize IndentationGuide panel.

        i_width(int): identation width in characters.
        """
        Panel.__init__(self, editor)
        self.color = Qt.darkGray
        self.i_width = 4

    def paintEvent(self, event):
        """Override Qt method."""
        painter = QPainter(self)

        color = QColor(self.color)
        color.setAlphaF(.5)
        painter.setPen(color)

        for top, line_number, block in self.editor.visible_blocks:
            bottom = top + int(self.editor.blockBoundingRect(block).height())

            indentation = TextBlockHelper.get_fold_lvl(block)

            for i in range(1, indentation):
                x = self.editor.fontMetrics().width(i * self.i_width * '9')
                painter.drawLine(x, top, x, bottom)

    # --- Other methods
    # -----------------------------------------------------------------

    def set_enabled(self, state):
        """Toggle edge line visibility."""
        self._enabled = state
        self.setVisible(state)

    def update_color(self):
        """Set color using syntax highlighter color for comments."""
        self.color = self.editor.highlighter.get_color_name('comment')

    def set_indentation_width(self, indentation_width):
        """Set indentation width to be used to draw indent guides."""
        self.i_width = indentation_width
