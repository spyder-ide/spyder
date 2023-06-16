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
import math

# Third party imports
from qtpy.QtCore import QSize, Qt, QPointF
from qtpy.QtGui import (
    QColor, QFontMetricsF, QPainter, QStaticText, QTextOption
)

# Local imports
from spyder.utils.icon_manager import ima
from spyder.api.panel import Panel
from spyder.plugins.completion.api import DiagnosticSeverity


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

        # This is a tuple composed of (number of digits, current width)
        self._width_cache = None

        # Cache line numbers
        self._static_line_numbers = None
        self._static_active_line = None

        # Static text must be flushed when dpi changes (qt bug?)
        self._static_text_dpi = None

    def sizeHint(self):
        """Override Qt method."""
        return QSize(self.compute_width(), 0)

    def paintEvent(self, event):
        """Override Qt method.

        Painting line number area
        """
        painter = QPainter(self)
        painter.fillRect(event.rect(), self.editor.sideareas_color)
        font_height = self.editor.fontMetrics().height()

        def draw_pixmap(xleft, ytop, pixmap):
            # Scale pixmap height to device independent pixels
            pixmap_height = pixmap.height() / pixmap.devicePixelRatio()
            painter.drawPixmap(
                xleft,
                ceil(ytop + (font_height-pixmap_height) / 2),
                pixmap
            )

        size = self.get_markers_margin() - 2
        icon_size = QSize(size, size)

        if self._margin:
            font = self.editor.font()
            fm = QFontMetricsF(font)
            if (
                fm.leading() == 0
                and self.editor.lineWrapMode() == QTextOption.NoWrap
            ):
                self.draw_linenumbers(painter)
            else:
                # The editor doesn't care about leading or the text is being
                # wrapped, so each line must be drawn independently.
                self.draw_linenumbers_slow(painter)

        for top, line_number, block in self.editor.visible_blocks:
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

    def draw_linenumbers(self, painter):
        """Draw line numbers."""
        if len(self.editor.visible_blocks) == 0:
            return
        active_line_number = self.editor.textCursor().blockNumber() + 1
        number_digits = self.compute_width_digits()
        width = self.width()

        visible_lines = [ln for _, ln, _ in self.editor.visible_blocks]

        try:
            idx = visible_lines.index(active_line_number)
            active_top = self.editor.visible_blocks[idx][0]
        except ValueError:
            active_top = None

        # Right align
        line_numbers = [f"{ln:{number_digits}d}" for ln in visible_lines]

        # Use non-breaking spaces and <br> returns
        lines = "<br>".join(line_numbers).replace(" ", "&nbsp;")

        # This is needed to make that the font size of line numbers
        # be the same as the text one when zooming
        # See spyder-ide/spyder#2296 and spyder-ide/spyder#4811.
        font = self.editor.font()
        font.setWeight(font.Normal)
        painter.setFont(font)
        painter.setPen(self.linenumbers_color)

        if self.logicalDpiX() != self._static_text_dpi:
            self._static_text_dpi = self.logicalDpiX()
            self._static_line_numbers = None
            self._static_active_line = None

        if self._static_line_numbers:
            if lines != self._static_line_numbers.text():
                self._static_line_numbers.setText(lines)
        else:
            self._static_line_numbers = QStaticText(lines)
            self._static_line_numbers.prepare(font=font)

        top = self.editor.visible_blocks[0][0]
        left = width - self._static_line_numbers.size().width()

        painter.drawStaticText(
            QPointF(left, top), self._static_line_numbers)

        if active_top is not None:
            font.setWeight(font.Bold)
            painter.setFont(font)
            painter.setPen(self.editor.normal_color)

            text = str(active_line_number)
            if self._static_active_line:
                if text != self._static_active_line.text():
                    self._static_active_line.setText(text)
            else:
                self._static_active_line = QStaticText(text)
                self._static_active_line.setTextFormat(Qt.PlainText)
                self._static_active_line.prepare(font=font)

            size = self._static_active_line.size()
            left = width - size.width()

            # Hide non-bold number
            painter.fillRect(
                int(left), active_top, int(size.width()), int(size.height()),
                self.editor.sideareas_color
            )

            # Paint bold number
            painter.drawStaticText(
                QPointF(left, active_top), self._static_active_line)

    def draw_linenumbers_slow(self, painter):
        """
        Slower way (2x) to draw line numbers.

        This is necessary for some fonts and when the wrap lines option
        is active.
        """
        font = self.editor.font()
        font_height = self.editor.fontMetrics().height()
        active_block = self.editor.textCursor().block()
        active_line_number = active_block.blockNumber() + 1
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
                                 str(line_number))

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

    def compute_width_digits(self):
        """Compute and return line number area width in digits."""
        number_lines = self.editor.blockCount()
        return max(1, math.ceil(math.log10(
             number_lines + 1)))

    def compute_width(self):
        """Compute and return line number area width."""
        if not self._enabled:
            return 0
        number_digits = self.compute_width_digits()
        if (self._width_cache is not None and
                self._width_cache[0] == number_digits):
            return self._width_cache[1]

        if self._margin:
            margin = 3 + self.editor.fontMetrics().width('9' * number_digits)
        else:
            margin = 0
        width = margin + self.get_markers_margin()
        self._width_cache = (number_digits, width)
        return width

    def _clear_width_cache(self):
        """Clear width cache."""
        self._width_cache = None

    def on_install(self, editor):
        """Clear width cache on font change."""
        super(LineNumberArea, self).on_install(editor)
        editor.sig_font_changed.connect(self._clear_width_cache)

    def on_uninstall(self):
        """Disconnect signal."""
        self.editor.sig_font_changed.disconnect(self._clear_width_cache)
        super(LineNumberArea, self).on_uninstall()

    def get_markers_margin(self):
        """Get marker margins."""
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
        self._width_cache = None
        self._margin = linenumbers
        self._markers_margin = markers
        self.set_enabled(linenumbers or markers)

    def set_enabled(self, state):
        self._enabled = state
        self.setVisible(state)

    def get_width(self):
        """Return current line number area width"""
        return self.contentsRect().width()
