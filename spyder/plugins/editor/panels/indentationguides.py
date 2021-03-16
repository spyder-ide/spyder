# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""
This module contains the indentation guide panel.
"""

# Third party imports
from qtpy.QtCore import Qt
from qtpy.QtGui import QPainter, QColor

# Local imports
from spyder.api.panel import Panel


class IndentationGuide(Panel):
    """Indentation guides to easy identify nested blocks."""

    # --- Qt Overrides
    # -----------------------------------------------------------------
    def __init__(self):
        """Initialize IndentationGuide panel.
        i_width(int): identation width in characters.
        """
        Panel.__init__(self)
        self.color = Qt.darkGray
        self.i_width = 4
        self.bar_offset = 0

    def on_install(self, editor):
        """Manages install setup of the pane."""
        super().on_install(editor)
        horizontal_scrollbar = editor.horizontalScrollBar()
        horizontal_scrollbar.valueChanged.connect(self.update_bar_position)
        horizontal_scrollbar.sliderReleased.connect(self.update)

    def update_bar_position(self, value):
        self.bar_offset = value

    def sizeHint(self):
        """Override Qt method."""
        return self.size()

    def paintEvent(self, event):
        """
        Overriden Qt method.

        Paint indent guides.
        """
        # Set painter
        painter = QPainter(self)
        color = QColor(self.color)
        color.setAlphaF(.5)
        painter.setPen(color)

        # Compute offset
        offset = (self.editor.document().documentMargin() +
                  self.editor.contentOffset().x())

        # Folding info
        folding_panel = self.editor.panels.get('FoldingPanel')
        folding_regions = folding_panel.folding_regions
        leading_whitespaces = self.editor.leading_whitespaces

        # Visible block numbers
        visible_blocks = self.editor.get_visible_block_numbers()

        # Paint lines
        for start_line in folding_regions:
            end_line = folding_regions[start_line]
            line_numbers = (start_line, end_line)

            if self.do_paint(visible_blocks, line_numbers):
                start_block = self.editor.document().findBlockByNumber(
                    start_line)
                end_block = self.editor.document().findBlockByNumber(
                    end_line - 1)

                content_offset = self.editor.contentOffset()
                top = int(self.editor.blockBoundingGeometry(
                    start_block).translated(content_offset).top())
                bottom = int(self.editor.blockBoundingGeometry(
                    end_block).translated(content_offset).bottom())

                total_whitespace = leading_whitespaces.get(
                    max(start_line - 1, 0))
                end_whitespace = leading_whitespaces.get(end_line - 1)

                if end_whitespace and end_whitespace != total_whitespace:
                    font_metrics = self.editor.fontMetrics()
                    x = (font_metrics.width(total_whitespace * '9') +
                         self.bar_offset + offset)
                    painter.drawLine(x, top, x, bottom)

    # --- Other methods
    # -----------------------------------------------------------------
    def set_enabled(self, state):
        """Toggle edge line visibility."""
        self._enabled = state
        self.setVisible(state)

        # We need to request folding when toggling state so the lines
        # are computed when handling the folding response.
        self.editor.request_folding()

    def update_color(self):
        """Set color using syntax highlighter color for comments."""
        self.color = self.editor.highlighter.get_color_name('comment')

    def set_indentation_width(self, indentation_width):
        """Set indentation width to be used to draw indent guides."""
        self.i_width = indentation_width

    def do_paint(self, visible_blocks, line_numbers):
        """
        Decide if we need to paint an indent guide according to the
        visible region.
        """
        # Line numbers for the visible region.
        first_visible_line = visible_blocks[0] + 1
        last_visible_line = visible_blocks[1] + 1

        # Line numbers for the indent guide.
        start_line = line_numbers[0]
        end_line = line_numbers[1]

        # Guide starts before the visible region and ends inside it.
        if (start_line < first_visible_line and
                (first_visible_line <= end_line <= last_visible_line)):
            return True

        # Guide starts before the visible region and ends after it.
        if start_line <= first_visible_line and end_line >= last_visible_line:
            return True

        # Guide starts inside the visible region and ends after it.
        if ((first_visible_line <= start_line <= last_visible_line) and
                end_line > last_visible_line):
            return True

        # Guide starts and ends inside the visible region.
        if ((first_visible_line <= start_line <= last_visible_line) and
                (first_visible_line <= end_line <= last_visible_line)):
            return True

        # If none of those cases are true, we don't need to paint this guide.
        return False
