# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright (c) 2013-2016 Colin Duquesnoy and others (see pyqode/AUTHORS.rst)
# Copyright (c) 2016- Spyder Project Contributors (see AUTHORS.txt)
#
# Distributed under the terms of the MIT License
# (see NOTICE.txt in the Spyder root directory for details)
# -----------------------------------------------------------------------------

"""
This module contains the text decoration API.

Adapted from pyqode/core/api/decoration.py of the
`PyQode project <https://github.com/pyQode/pyQode>`_.
Original file:
<https://github.com/pyQode/pyqode.core/blob/master/pyqode/core/api/decoration.py>
"""

# Third party imports
from qtpy.QtWidgets import QTextEdit
from qtpy.QtCore import QObject, Signal, Qt
from qtpy.QtGui import (QTextCursor, QFont, QPen, QColor, QTextFormat,
                        QTextCharFormat)

# Local imports
from spyder.utils.palette import QStylePalette, SpyderPalette


# DRAW_ORDERS are used for make some decorations appear in top of others,
# and avoid a decoration from overlapping/hiding other decorations.
#
# For example, codefolding will appear in front of current cell but behind
# other decorations.
#
# NOTE: If two decorations have the same draw_order smaller decoration will
# appear in front of the other.

DRAW_ORDERS = {'on_bottom': 0,
               'current_cell': 1,
               'codefolding': 2,
               'current_line': 3,
               'on_top': 4}


class TextDecoration(QTextEdit.ExtraSelection):
    """
    Helper class to quickly create a text decoration.

    The text decoration is an utility class that adds a few utility methods to
    QTextEdit.ExtraSelection.

    In addition to the helper methods, a tooltip can be added to a decoration.
    (useful for errors markers and so on...)

    Text decoration expose a **clicked** signal stored in a separate QObject:
        :attr:`pyqode.core.api.TextDecoration.Signals`

    .. code-block:: python

        deco = TextDecoration()
        deco.signals.clicked.connect(a_slot)

        def a_slot(decoration):
            print(decoration)  # spyder: test-skip
    """
    class Signals(QObject):
        """
        Holds the signals for a TextDecoration (since we cannot make it a
        QObject, we need to store its signals in an external QObject).
        """
        #: Signal emitted when a TextDecoration has been clicked.
        clicked = Signal(object)

    def __init__(self, cursor_or_bloc_or_doc, start_pos=None, end_pos=None,
                 start_line=None, end_line=None, draw_order=0, tooltip=None,
                 full_width=False, font=None, kind=None):
        """
        Creates a text decoration.

        .. note:: start_pos/end_pos and start_line/end_line pairs let you
            easily specify the selected text. You should use one pair or the
            other or they will conflict between each others. If you don't
            specify any values, the selection will be based on the cursor.

        :param cursor_or_bloc_or_doc: Reference to a valid
            QTextCursor/QTextBlock/QTextDocument
        :param start_pos: Selection start position
        :param end_pos: Selection end position
        :param start_line: Selection start line.
        :param end_line: Selection end line.
        :param draw_order: The draw order of the selection, highest values will
            appear on top of the lowest values.
        :param tooltip: An optional tooltips that will be automatically shown
            when the mouse cursor hover the decoration.
        :param full_width: True to select the full line width.
        :param font: Decoration font.
        :param kind: Decoration kind, e.g. 'current_cell'.

        .. note:: Use the cursor selection if startPos and endPos are none.
        """
        super(TextDecoration, self).__init__()
        self.signals = self.Signals()
        self.draw_order = draw_order
        self.tooltip = tooltip
        self.cursor = QTextCursor(cursor_or_bloc_or_doc)
        self.kind = kind

        if full_width:
            self.set_full_width(full_width)
        if start_pos is not None:
            self.cursor.setPosition(start_pos)
        if end_pos is not None:
            self.cursor.setPosition(end_pos, QTextCursor.KeepAnchor)
        if start_line is not None:
            self.cursor.movePosition(self.cursor.Start, self.cursor.MoveAnchor)
            self.cursor.movePosition(self.cursor.Down, self.cursor.MoveAnchor,
                                     start_line)
        if end_line is not None:
            self.cursor.movePosition(self.cursor.Down, self.cursor.KeepAnchor,
                                     end_line - start_line)
        if font is not None:
            self.format.setFont(font)

    def contains_cursor(self, cursor):
        """
        Checks if the textCursor is in the decoration.

        :param cursor: The text cursor to test
        :type cursor: QtGui.QTextCursor

        :returns: True if the cursor is over the selection
        """
        start = self.cursor.selectionStart()
        end = self.cursor.selectionEnd()
        if cursor.atBlockEnd():
            end -= 1
        return start <= cursor.position() <= end

    def set_as_bold(self):
        """Uses bold text."""
        self.format.setFontWeight(QFont.Bold)

    def set_foreground(self, color):
        """Sets the foreground color.
        :param color: Color
        :type color: QtGui.QColor
        """
        self.format.setForeground(color)

    def set_background(self, brush):
        """
        Sets the background brush.

        :param brush: Brush
        :type brush: QtGui.QBrush
        """
        self.format.setBackground(brush)

    def set_outline(self, color):
        """
        Uses an outline rectangle.

        :param color: Color of the outline rect
        :type color: QtGui.QColor
        """
        self.format.setProperty(QTextFormat.OutlinePen,
                                QPen(color))

    def select_line(self):
        """
        Select the entire line but starts at the first non whitespace character
        and stops at the non-whitespace character.
        :return:
        """
        self.cursor.movePosition(self.cursor.StartOfBlock)
        text = self.cursor.block().text()
        lindent = len(text) - len(text.lstrip())
        self.cursor.setPosition(self.cursor.block().position() + lindent)
        self.cursor.movePosition(self.cursor.EndOfBlock,
                                 self.cursor.KeepAnchor)

    def set_full_width(self, flag=True, clear=True):
        """
        Enables FullWidthSelection (the selection does not stops at after the
        character instead it goes up to the right side of the widget).

        :param flag: True to use full width selection.
        :type flag: bool

        :param clear: True to clear any previous selection. Default is True.
        :type clear: bool
        """
        if clear:
            self.cursor.clearSelection()
        self.format.setProperty(QTextFormat.FullWidthSelection, flag)

    def set_as_underlined(self, color=Qt.blue):
        """
        Underlines the text.

        :param color: underline color.
        """
        self.format.setUnderlineStyle(
            QTextCharFormat.SingleUnderline)
        self.format.setUnderlineColor(color)

    def set_as_spell_check(self, color=Qt.blue):
        """
        Underlines text as a spellcheck error.

        :param color: Underline color
        :type color: QtGui.QColor
        """
        self.format.setUnderlineStyle(
            QTextCharFormat.SpellCheckUnderline)
        self.format.setUnderlineColor(color)

    def set_as_error(self, color=SpyderPalette.COLOR_ERROR_2):
        """
        Highlights text as a syntax error.

        :param color: Underline color
        :type color: QtGui.QColor
        """
        self.format.setUnderlineStyle(
            QTextCharFormat.WaveUnderline)
        self.format.setUnderlineColor(color)

    def set_as_warning(self, color=QColor(SpyderPalette.COLOR_WARN_1)):
        """
        Highlights text as a syntax warning.

        :param color: Underline color
        :type color: QtGui.QColor
        """
        self.format.setUnderlineStyle(
            QTextCharFormat.WaveUnderline)
        self.format.setUnderlineColor(color)
