# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""
This module contains the Line Number panel
"""

# Standard library imports
from math import ceil

# Third party imports
from qtpy import QT_VERSION
from qtpy.QtCore import QSize, Qt
from qtpy.QtGui import QPainter, QColor

# Local imports
from spyder.py3compat import to_text_string
from spyder.utils.icon_manager import ima
from spyder.utils.programs import check_version
from spyder.api.panel import Panel
from spyder.plugins.completion.api import DiagnosticSeverity


QT55_VERSION = check_version(QT_VERSION, "5.5", ">=")


class LineNumberArea(Panel):
    """Line number area (on the left side of the text editor widget)"""

    # --- Qt Overrides
    # -----------------------------------------------------------------

    def __init__(self):
        Panel.__init__(self)

        self.setMouseTracking(True)
        self.scrollable = True
        self.linenumbers_color = QColor(Qt.darkGray)

        # Markers
        self._markers_margin = True

        # Icons
        self.error_icon = ima.icon('error')
        self.warning_icon = ima.icon('warning')
        self.info_icon = ima.icon('information')
        self.hint_icon = ima.icon('hint')
        self.todo_icon = ima.icon('todo')

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
        # See spyder-ide/spyder#2296 and spyder-ide/spyder#4811.
        font = self.editor.font()
        font_height = self.editor.fontMetrics().height()

        active_block = self.editor.textCursor().block()
        active_line_number = active_block.blockNumber() + 1

        def draw_pixmap(xleft, ytop, pixmap):
            if not QT55_VERSION:
                pixmap_height = pixmap.height()
            else:
                # scale pixmap height to device independent pixels
                pixmap_height = pixmap.height() / pixmap.devicePixelRatio()
            painter.drawPixmap(xleft, ceil(ytop +
                                           (font_height-pixmap_height) / 2),
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
                                 int(Qt.AlignRight | Qt.AlignBottom),
                                 to_text_string(line_number))

            size = self.get_markers_margin() - 2
            icon_size = QSize(size, size)

            data = block.userData()
            if self._markers_margin and data:
                if data.code_analysis:
                    errors = 0
                    warnings = 0
                    infos = 0
                    hints = 0
                    for _, _, sev, _ in data.code_analysis:
                        errors += sev == DiagnosticSeverity.ERROR
                        warnings += sev == DiagnosticSeverity.WARNING
                        infos += sev == DiagnosticSeverity.INFORMATION
                        hints += sev == DiagnosticSeverity.HINT

                    if errors:
                        draw_pixmap(1, top, self.error_icon.pixmap(icon_size))
                    elif warnings:
                        draw_pixmap(
                            1, top, self.warning_icon.pixmap(icon_size))
                    elif infos:
                        draw_pixmap(1, top, self.info_icon.pixmap(icon_size))
                    elif hints:
                        draw_pixmap(1, top, self.hint_icon.pixmap(icon_size))

                if data.todo:
                    draw_pixmap(1, top, self.todo_icon.pixmap(icon_size))

    def leaveEvent(self, event):
        """Override Qt method."""
        self.editor.hide_tooltip()

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
        else:
            self.editor.hide_tooltip()

        if event.buttons() == Qt.LeftButton:
            self._released = line_number
            self.editor.select_lines(self._pressed, self._released)

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
            font_height = self.editor.fontMetrics().height() + 2
            return font_height
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
