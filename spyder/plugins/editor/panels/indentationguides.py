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
from intervaltree import IntervalTree

# Local imports
from spyder.plugins.editor.utils.editor import TextBlockHelper
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
        self.bar_offset = 0
        horizontal_scrollbar = editor.horizontalScrollBar()
        horizontal_scrollbar.valueChanged.connect(self.update_bar_position)
        horizontal_scrollbar.sliderReleased.connect(self.update)

    def update_bar_position(self, value):
        self.bar_offset = value

    def paintEvent(self, event):
        """Override Qt method."""
        painter = QPainter(self)

        color = QColor(self.color)
        color.setAlphaF(.5)
        painter.setPen(color)
        offset = self.editor.document().documentMargin() + \
            self.editor.contentOffset().x()
        folding_panel = self.editor.panels.get('FoldingPanel')
        folding_regions = folding_panel.folding_regions
        folding_status = folding_panel.folding_status
        leading_whitespaces = self.editor.leading_whitespaces
        for line_number in folding_regions:
            post_update = False
            end_line = folding_regions[line_number]
            start_block = self.editor.document().findBlockByNumber(
                line_number)
            end_block = self.editor.document().findBlockByNumber(end_line - 1)
            top = int(self.editor.blockBoundingGeometry(
                start_block).translated(self.editor.contentOffset()).top())
            bottom = int(self.editor.blockBoundingGeometry(
                end_block).translated(self.editor.contentOffset()).bottom())
            total_whitespace = leading_whitespaces.get(max(line_number - 1, 0))
            end_whitespace = leading_whitespaces.get(end_line - 1)
            if end_whitespace and end_whitespace != total_whitespace:
                x = (self.editor.fontMetrics().width(total_whitespace * '9') +
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
