
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

    def paintEvent(self, event):
        """Override Qt method."""
        painter = QPainter(self)

        color = QColor(self.color)
        color.setAlphaF(.5)
        painter.setPen(color)
        offset = self.editor.document().documentMargin() + \
            self.editor.contentOffset().x()

        for _, line_number, block in self.editor.visible_blocks:

            indentation = TextBlockHelper.get_fold_lvl(block)
            ref_lvl = indentation
            block = block.next()
            last_line = block.blockNumber()
            lvl = TextBlockHelper.get_fold_lvl(block)
            if ref_lvl == lvl:  # for zone set programmatically such as imports
                # in pyqode.python
                ref_lvl -= 1

            while (block.isValid() and
                   TextBlockHelper.get_fold_lvl(block) > ref_lvl):
                last_line = block.blockNumber()
                block = block.next()

            end_of_sub_fold = block
            if last_line:
                block = block.document().findBlockByNumber(last_line)
                while ((block.blockNumber()) and (block.text().strip() == ''
                       or block.text().strip().startswith('#'))):
                    block = block.previous()
                    last_line = block.blockNumber()

            block = self.editor.document().findBlockByNumber(line_number)
            top = int(self.editor.blockBoundingGeometry(block).translated(
                self.editor.contentOffset()).top())
            bottom = top + int(self.editor.blockBoundingRect(block).height())

            indentation = TextBlockHelper.get_fold_lvl(block)

            for i in range(1, indentation):
                if (line_number > last_line and
                        TextBlockHelper.get_fold_lvl(end_of_sub_fold) <= i):
                    continue
                else:
                    x = self.editor.fontMetrics().width(i * self.i_width *
                                                        '9') + offset
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
