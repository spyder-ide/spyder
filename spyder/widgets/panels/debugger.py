# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)
"""
This module contains the DebuggerPanel panel
"""
from qtpy.QtCore import QSize, Qt, QRect
from qtpy.QtGui import QPainter, QFontMetricsF

from spyder.utils import icon_manager as ima
from spyder.api.panel import Panel


class DebuggerPanel(Panel):
    """Debugger panel for show information about the debugging in process."""

    def __init__(self):
        """Initialize panel."""
        Panel.__init__(self)

        self.setMouseTracking(True)
        self.scrollable = True

        # Markers
        self.bp_pixmap = ima.icon('breakpoint_big')
        self.bpc_pixmap = ima.icon('breakpoint_cond_big')

    def sizeHint(self):
        """Override Qt method.

        Returns the widget size hint (based on the editor font size).
        """
        fm = QFontMetricsF(self.editor.font())
        size_hint = QSize(fm.height(), fm.height())
        if size_hint.width() > 16:
            size_hint.setWidth(16)
        return size_hint

    def _draw_breakpoint_icon(self, top, painter, pixmap):
        """Draw the given breakpoint pixmap.

        Args:
            top (int): top of the line to draw the breakpoint icon.
            painter (QPainter)
            pixmap (QIcon): pixmap icon to draw
        """
        rect = QRect(0, top, self.sizeHint().width(),
                     self.sizeHint().height())
        pixmap.paint(painter, rect)

    def paintEvent(self, event):
        """Override Qt method.

        Paint breakpoints icons.
        """
        painter = QPainter(self)
        painter.fillRect(event.rect(), self.editor.sideareas_color)

        for top, line_number, block in self.editor.visible_blocks:
            data = block.userData()
            if data is None or not data.breakpoint:
                continue

            if data.breakpoint_condition is None:
                self._draw_breakpoint_icon(top, painter, self.bp_pixmap)
            else:
                self._draw_breakpoint_icon(top, painter, self.bpc_pixmap)

    def mousePressEvent(self, event):
        """Override Qt method

        Add/remove breakpoints by single click.
        """
        line_number = self.editor.get_linenumber_from_mouse_event(event)
        shift = event.modifiers() & Qt.ShiftModifier
        self.editor.add_remove_breakpoint(line_number, edit_condition=shift)

    def wheelEvent(self, event):
        """Override Qt method.

        Needed for scroll down the editor when scrolling over the panel.
        """
        self.editor.wheelEvent(event)

    def on_state_changed(self, state):
        """Change visibility and connect/desconnect signal.

        Args:
            state (bool): Activate/deactivate.
        """
        self.setVisible(state)
        if state:
            self.editor.breakpoints_changed.connect(self.repaint)
        else:
            self.editor.breakpoints_changed.disconnect(self.repaint)
