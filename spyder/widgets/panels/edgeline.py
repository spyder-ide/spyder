# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""
This module contains the edge line panel
"""

from qtpy.QtCore import Qt
from qtpy.QtGui import QPainter, QColor, QPen

from spyder.py3compat import is_text_string
from spyder.api.panel import Panel


class EdgeLine(Panel):
    """Source code editor's edge line (default: 79 columns, PEP8)"""

    # --- Qt Overrides
    # -----------------------------------------------------------------
    def __init__(self, editor):
        Panel.__init__(self, editor)
        self.columns = (79,)
        self.color = Qt.darkGray

    def paintEvent(self, event):
        """Override Qt method"""
        painter = QPainter(self)
        size = self.size()

        color = QColor(self.color)
        color.setAlphaF(.5)
        painter.setPen(color)

        for column in self.columns:
            x = self.editor.fontMetrics().width(column * '9')
            painter.drawLine(x, 0, x, size.height())

    # --- Other methods
    # -----------------------------------------------------------------

    def set_enabled(self, state):
        """Toggle edge line visibility"""
        self._enabled = state
        self.setVisible(state)

    def set_columns(self, columns):
        """Set edge line columns values."""
        if isinstance(columns, tuple):
            self.columns = columns
        elif is_text_string(columns):
            self.columns = tuple(int(e) for e in columns.split(','))

        self.update()

    def update_color(self):
        """
        Set edgeline color using syntax highlighter color for comments
        """
        self.color = self.editor.highlighter.get_color_name('comment')
