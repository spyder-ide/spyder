# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)
"""
This module contains the DebuggerPanel panel
"""
from qtpy.QtCore import QSize, Qt
from qtpy.QtGui import QPainter, QFontMetricsF

from spyder.utils import icon_manager as ima
from spyder.api.panel import Panel


class DebuggerPanel(Panel):
    """Debugger panel for show information about the debugging in process."""

    def __init__(self):
        Panel.__init__(self)

        self.setMouseTracking(True)
        self.scrollable = True

        # Markers
        self.bp_pixmap = ima.icon('breakpoint_big').pixmap(QSize(14, 14))
        self.bpc_pixmap = ima.icon('breakpoint_cond_big').pixmap(QSize(14, 14))

    def sizeHint(self):
        """Override Qt method.
        Returns the widget size hint (based on the editor font size) """
        fm = QFontMetricsF(self.editor.font())
        size_hint = QSize(fm.height(), fm.height())
        if size_hint.width() > 16:
            size_hint.setWidth(16)
        return size_hint

    def paintEvent(self, event):
        """Override Qt method.

        Paint breakpoints and current line arrow.
        """

        painter = QPainter(self)
        painter.fillRect(event.rect(), self.editor.sideareas_color)

    def mouseMoveEvent(self, event):
        """Override Qt method.

        Add/remove breakpoint by single click.
        Move arror
        """
        if event.buttons() == Qt.LeftButton:
            line_number = self.editor.get_linenumber_from_mouse_event(event)
            shift = event.modifiers() & Qt.ShiftModifier
            self.editor.add_remove_breakpoint(line_number,
                                              edit_condition=shift)

    def mousePressEvent(self, event):
        """Override Qt method"""
        pass

    def mouseReleaseEvent(self, event):
        """Override Qt method."""
        pass

    def wheelEvent(self, event):
        """Override Qt method."""
        self.editor.wheelEvent(event)

    def on_state_changed(self, state):
        self.setVisible(state)
