# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""
This module contains the edge line numebr panel
"""

from qtpy.QtWidgets import QWidget
from qtpy.QtCore import Qt
from qtpy.QtGui import QPainter, QColor


class EdgeLine(QWidget):
    """Source code editor's edge line (default: 79 columns, PEP8)"""

    # --- Qt Overrides
    # -----------------------------------------------------------------
    def __init__(self, editor):
        QWidget.__init__(self, editor)
        self.code_editor = editor
        self.column = 79
        self.setAttribute(Qt.WA_TransparentForMouseEvents)

        self._enabled = True

    def paintEvent(self, event):
        """Override Qt method"""
        painter = QPainter(self)
        color = QColor(Qt.darkGray)
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
