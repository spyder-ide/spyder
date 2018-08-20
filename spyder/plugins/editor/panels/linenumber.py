# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)
"""
This module contains the Line Number panel
"""
import sys

from qtpy import QT_VERSION
from qtpy.QtCore import QSize, Qt
from qtpy.QtGui import QPainter, QColor

from spyder.py3compat import to_text_string
from spyder.utils import icon_manager as ima
from spyder.utils.programs import check_version
from spyder.api.panel import Panel
from spyder.plugins.editor.lsp import DiagnosticSeverity


QT55_VERSION = check_version(QT_VERSION, "5.5", ">=")


class LineNumberArea(Panel):
    """Line number area (on the left side of the text editor widget)"""

    # --- Qt Overrides
    # -----------------------------------------------------------------

    def __init__(self, editor):
        Panel.__init__(self, editor)

        self.setMouseTracking(True)
        self.scrollable = True
        self.linenumbers_color = QColor(Qt.darkGray)

        # Markers
        self._markers_margin = True
        self._markers_margin_width = 15
        self.error_pixmap = ima.icon('error').pixmap(QSize(14, 14))
        self.warning_pixmap = ima.icon('warning').pixmap(QSize(14, 14))
        self.todo_pixmap = ima.icon('todo').pixmap(QSize(14, 14))
        self.bp_pixmap = ima.icon('breakpoint_big').pixmap(QSize(14, 14))
        self.bpc_pixmap = ima.icon('breakpoint_cond_big').pixmap(QSize(14, 14))

        # Line number area management
        self._margin = True
        self._pressed = -1
        self._released = -1

    def sizeHint(self):
        """Override Qt method."""
        return QSize(self.compute_width(), 0)

    def paintEvent(self, event):
        """Override Qt method.

        Painting line number area
        """
        painter = QPainter(self)
        painter.fillRect(event.rect(), self.editor.sideareas_color)
        # This is needed to make that the font size of line numbers
        # be the same as the text one when zooming
        # See Issue 2296 and 4811
        font = self.editor.font()
        font_height = self.editor.fontMetrics().height()

        active_block = self.editor.textCursor().block()
        active_line_number = active_block.blockNumber() + 1

        def draw_pixmap(ytop, pixmap):
            if not QT55_VERSION:
                pixmap_height = pixmap.height()
            else:
                # scale pixmap height to device independent pixels
                pixmap_height = pixmap.height() / pixmap.devicePixelRatio()
            painter.drawPixmap(0, ytop + (font_height-pixmap_height) / 2,
                               pixmap)

        for top, line_number, block in self.editor.visible_blocks:
            if self._margin:
                if line_number == active_line_number:
                    font.setWeight(font.Bold)
                    painter.setFont(font)
                    painter.setPen(self.editor.normal_color)
                else:
                    font.setWeight(font.Normal)
                    painter.setFont(font)
                    painter.setPen(self.linenumbers_color)

                painter.drawText(0, top, self.width(),
                                 font_height,
                                 Qt.AlignRight | Qt.AlignBottom,
                                 to_text_string(line_number))

            data = block.userData()
            if self._markers_margin and data:
                if data.code_analysis:
                    for source, code, severity, message in data.code_analysis:
                        error = severity == DiagnosticSeverity.ERROR
                        if error:
                            break
                    if error:
                        draw_pixmap(top, self.error_pixmap)
                    else:
                        draw_pixmap(top, self.warning_pixmap)
                if data.todo:
                    draw_pixmap(top, self.todo_pixmap)
                if data.breakpoint:
                    if data.breakpoint_condition is None:
                        draw_pixmap(top, self.bp_pixmap)
                    else:
                        draw_pixmap(top, self.bpc_pixmap)

    def mouseMoveEvent(self, event):
        """Override Qt method.

        Show code analisis, if left button pressed select lines.
        """
        line_number = self.editor.get_linenumber_from_mouse_event(event)
        block = self.editor.document().findBlockByNumber(line_number-1)
        data = block.userData()

        # this disables pyflakes messages if there is an active drag/selection
        # operation
        check = self._released == -1
        if data and data.code_analysis and check:
            self.editor.show_code_analysis_results(line_number,
                                                   data)

        if event.buttons() == Qt.LeftButton:
            self._released = line_number
            self.editor.select_lines(self._pressed, self._released)

    def mouseDoubleClickEvent(self, event):
        """Override Qt method.

        Add or remove breakpoints.
        """
        line_number = self.editor.get_linenumber_from_mouse_event(event)
        shift = event.modifiers() & Qt.ShiftModifier
        self.editor.add_remove_breakpoint(line_number, edit_condition=shift)

    def mousePressEvent(self, event):
        """Override Qt method

        Select line, and starts selection
        """
        line_number = self.editor.get_linenumber_from_mouse_event(event)
        self._pressed = line_number
        self._released = line_number
        self.editor.select_lines(self._pressed,
                                 self._released)

    def mouseReleaseEvent(self, event):
        """Override Qt method."""
        self._released = -1
        self._pressed = -1

    def wheelEvent(self, event):
        """Override Qt method."""
        self.editor.wheelEvent(event)

    # --- Other methods
    # -----------------------------------------------------------------

    def compute_width(self):
        """Compute and return line number area width"""
        if not self._enabled:
            return 0
        digits = 1
        maxb = max(1, self.editor.blockCount())
        while maxb >= 10:
            maxb /= 10
            digits += 1
        if self._margin:
            margin = 3+self.editor.fontMetrics().width('9'*digits)
        else:
            margin = 0
        return margin+self.get_markers_margin()

    def get_markers_margin(self):
        if self._markers_margin:
            return self._markers_margin_width
        else:
            return 0


    def setup_margins(self, linenumbers=True, markers=True):
        """
        Setup margin settings
        (except font, now set in editor.set_font)
        """
        self._margin = linenumbers
        self._markers_margin = markers
        self.set_enabled(linenumbers or markers)

    def set_enabled(self, state):
        self._enabled = state
        self.setVisible(state)

    def get_width(self):
        """Return current line number area width"""
        return self.contentsRect().width()
