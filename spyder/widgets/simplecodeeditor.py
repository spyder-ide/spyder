# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright © Spyder Project Contributors
#
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)
# ----------------------------------------------------------------------------

"""
Simple code editor with syntax highlighting and line number area.

Adapted from:
https://doc.qt.io/qt-5/qtwidgets-widgets-codeeditor-example.html
"""

# Standard library imports
import re

# Third party imports
from qtpy.QtCore import QRect, QSize, Qt, Signal
from qtpy.QtGui import QColor, QPainter, QTextCursor, QTextFormat, QTextOption
from qtpy.QtWidgets import QApplication, QPlainTextEdit, QTextEdit, QWidget

# Local imports
import spyder.utils.syntaxhighlighters as sh
from spyder.widgets.mixins import BaseEditMixin


# Constants
LANGUAGE_EXTENSIONS = {
    'Python': ('py', 'pyw', 'python', 'ipy'),
    'Cython': ('pyx', 'pxi', 'pxd'),
    'Enaml': ('enaml',),
    'Fortran77': ('f', 'for', 'f77'),
    'Fortran': ('f90', 'f95', 'f2k', 'f03', 'f08'),
    'Idl': ('pro',),
    'Diff': ('diff', 'patch', 'rej'),
    'GetText': ('po', 'pot'),
    'Nsis': ('nsi', 'nsh'),
    'Html': ('htm', 'html'),
    'Cpp': ('c', 'cc', 'cpp', 'cxx', 'h', 'hh', 'hpp', 'hxx'),
    'OpenCL': ('cl',),
    'Yaml': ('yaml', 'yml'),
    'Markdown': ('md', 'mdw'),
    # Every other language
    'None': ('', ),
}


class LineNumberArea(QWidget):
    """
    Adapted from:
    https://doc.qt.io/qt-5/qtwidgets-widgets-codeeditor-example.html
    """

    def __init__(self, code_editor=None):
        super().__init__(code_editor)

        self._editor = code_editor
        self._left_padding = 6  # Pixels
        self._right_padding = 3  # Pixels

    # --- Qt overrides
    # ------------------------------------------------------------------------
    def sizeHint(self):
        return QSize(self._editor.linenumberarea_width(), 0)

    def paintEvent(self, event):
        self._editor.linenumberarea_paint_event(event)


class SimpleCodeEditor(QPlainTextEdit, BaseEditMixin):
    """Simple editor with highlight features."""

    LANGUAGE_HIGHLIGHTERS = {
        'Python': (sh.PythonSH, '#'),
        'Cython': (sh.CythonSH, '#'),
        'Fortran77': (sh.Fortran77SH, 'c'),
        'Fortran': (sh.FortranSH, '!'),
        'Idl': (sh.IdlSH, ';'),
        'Diff': (sh.DiffSH, ''),
        'GetText': (sh.GetTextSH, '#'),
        'Nsis': (sh.NsisSH, '#'),
        'Html': (sh.HtmlSH, ''),
        'Yaml': (sh.YamlSH, '#'),
        'Cpp': (sh.CppSH, '//'),
        'OpenCL': (sh.OpenCLSH, '//'),
        'Enaml': (sh.EnamlSH, '#'),
        'Markdown': (sh.MarkdownSH, '#'),
        # Every other language
        'None': (sh.TextSH, ''),
    }

    # --- Signals
    # ------------------------------------------------------------------------
    sig_focus_changed = Signal()
    """
    This signal when the focus of the editor changes, either by a
    `focusInEvent` or `focusOutEvent` event.
    """

    def __init__(self, parent=None):
        super().__init__(parent)

        # Variables
        self._linenumber_enabled = None
        self._color_scheme = "spyder/dark"
        self._language = None
        self._blanks_enabled = None
        self._scrollpastend_enabled = None
        self._wrap_mode = None
        self._highlight_current_line = None
        self.supported_language = False

        # Widgets
        self._highlighter = None
        self.linenumberarea = LineNumberArea(self)

        # Widget setup
        self.setObjectName(self.__class__.__name__ + str(id(self)))
        self.update_linenumberarea_width(0)
        self._apply_current_line_highlight()

        # Signals
        self.blockCountChanged.connect(self.update_linenumberarea_width)
        self.updateRequest.connect(self.update_linenumberarea)
        self.cursorPositionChanged.connect(self._apply_current_line_highlight)

    # --- Private API
    # ------------------------------------------------------------------------
    def _apply_color_scheme(self):
        hl = self._highlighter
        if hl is not None:
            hl.setup_formats(self.font())
            if self._color_scheme is not None:
                hl.set_color_scheme(self._color_scheme)

            self._set_palette(background=hl.get_background_color(),
                              foreground=hl.get_foreground_color())

    def _set_palette(self, background, foreground):
        style = ("QPlainTextEdit#%s {background: %s; color: %s;}" %
                 (self.objectName(), background.name(), foreground.name()))
        self.setStyleSheet(style)
        self.rehighlight()

    def _apply_current_line_highlight(self):
        if self._highlighter and self._highlight_current_line:
            extra_selections = []
            selection = QTextEdit.ExtraSelection()
            line_color = self._highlighter.get_currentline_color()
            selection.format.setBackground(line_color)
            selection.format.setProperty(QTextFormat.FullWidthSelection, True)
            selection.cursor = self.textCursor()
            selection.cursor.clearSelection()
            extra_selections.append(selection)

            self.setExtraSelections(extra_selections)
        else:
            self.setExtraSelections([])

    # --- Qt Overrides
    # ------------------------------------------------------------------------
    def focusInEvent(self, event):
        self.sig_focus_changed.emit()
        super().focusInEvent(event)

    def focusOutEvent(self, event):
        self.sig_focus_changed.emit()
        super().focusInEvent(event)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self._linenumber_enabled:
            cr = self.contentsRect()
            self.linenumberarea.setGeometry(
                QRect(
                    cr.left(),
                    cr.top(),
                    self.linenumberarea_width(),
                    cr.height(),
                )
            )

    # --- Public API
    # ------------------------------------------------------------------------
    def setup_editor(self,
                     linenumbers=True,
                     color_scheme="spyder/dark",
                     language="py",
                     font=None,
                     show_blanks=False,
                     wrap=False,
                     highlight_current_line=True,
                     scroll_past_end=False):
        """
        Setup editor options.

        Parameters
        ----------
        color_scheme: str, optional
            Default is "spyder/dark".
        language: str, optional
            Default is "py".
        font: QFont or None
            Default is None.
        show_blanks: bool, optional
            Default is False/
        wrap: bool, optional
            Default is False.
        highlight_current_line: bool, optional
            Default is True.
        scroll_past_end: bool, optional
            Default is False
        """
        if font:
            self.set_font(font)

        self.set_highlight_current_line(highlight_current_line)
        self.set_blanks_enabled(show_blanks)
        self.toggle_line_numbers(linenumbers)
        self.set_scrollpastend_enabled(scroll_past_end)
        self.set_language(language)
        self.set_color_scheme(color_scheme)
        self.toggle_wrap_mode(wrap)

    def set_font(self, font):
        """
        Set the editor font.

        Parameters
        ----------
        font: QFont
            Font to use.
        """
        if font:
            self.setFont(font)
            self._apply_color_scheme()

    def set_color_scheme(self, color_scheme):
        """
        Set the editor color scheme.

        Parameters
        ----------
        color_scheme: str
            Color scheme to use.
        """
        self._color_scheme = color_scheme
        self._apply_color_scheme()

    def set_language(self, language):
        """
        Set current syntax highlighting to use `language`.

        Parameters
        ----------
        language: str or None
            Language name or known extensions.
        """
        sh_class = sh.TextSH
        language = str(language).lower()
        self.supported_language = False
        for (key, value) in LANGUAGE_EXTENSIONS.items():
            if language in (key.lower(), ) + value:
                sh_class, __ = self.LANGUAGE_HIGHLIGHTERS[key]
                self._language = key
                self.supported_language = True

        self._highlighter = sh_class(
            self.document(), self.font(), self._color_scheme)
        self._apply_color_scheme()

    def toggle_line_numbers(self, state):
        """
        Set visibility of line number area

        Parameters
        ----------
        state: bool
            Visible state of the line number area.
        """

        self._linenumber_enabled = state
        self.linenumberarea.setVisible(state)
        self.update_linenumberarea_width(())

    def set_scrollpastend_enabled(self, state):
        """
        Set scroll past end state.

        Parameters
        ----------
        state: bool
            Scroll past end state.
        """
        self._scrollpastend_enabled = state
        self.setCenterOnScroll(state)
        self.setDocument(self.document())

    def toggle_wrap_mode(self, state):
        """
        Set line wrap..

        Parameters
        ----------
        state: bool
            Wrap state.
        """
        self.set_wrap_mode('word' if state else None)

    def set_wrap_mode(self, mode=None):
        """
        Set line wrap mode.

        Parameters
        ----------
        mode: str or None, optional
            "word", or "character". Default is None.
        """
        if mode == 'word':
            wrap_mode = QTextOption.WrapAtWordBoundaryOrAnywhere
        elif mode == 'character':
            wrap_mode = QTextOption.WrapAnywhere
        else:
            wrap_mode = QTextOption.NoWrap

        self.setWordWrapMode(wrap_mode)

    def set_highlight_current_line(self, value):
        """
        Set if the current line is highlighted.

        Parameters
        ----------
        value: bool
            The value of the current line highlight option.
        """
        self._highlight_current_line = value
        self._apply_current_line_highlight()

    def set_blanks_enabled(self, state):
        """
        Show blank spaces.

        Parameters
        ----------
        state: bool
            Blank spaces visibility.
        """
        self._blanks_enabled = state
        option = self.document().defaultTextOption()
        option.setFlags(option.flags()
                        | QTextOption.AddSpaceForLineAndParagraphSeparators)

        if self._blanks_enabled:
            option.setFlags(option.flags() | QTextOption.ShowTabsAndSpaces)
        else:
            option.setFlags(option.flags() & ~QTextOption.ShowTabsAndSpaces)

        self.document().setDefaultTextOption(option)

        # Rehighlight to make the spaces less apparent.
        self.rehighlight()

    # --- Line number area
    # ------------------------------------------------------------------------
    def linenumberarea_paint_event(self, event):
        """
        Paint the line number area.
        """
        if self._linenumber_enabled:
            painter = QPainter(self.linenumberarea)
            painter.fillRect(
                event.rect(),
                self._highlighter.get_sideareas_color(),
            )

            block = self.firstVisibleBlock()
            block_number = block.blockNumber()
            top = round(self.blockBoundingGeometry(block).translated(
                self.contentOffset()).top())
            bottom = top + round(self.blockBoundingRect(block).height())

            font = self.font()
            active_block = self.textCursor().block()
            active_line_number = active_block.blockNumber() + 1

            while block.isValid() and top <= event.rect().bottom():
                if block.isVisible() and bottom >= event.rect().top():
                    number = block_number + 1

                    if number == active_line_number:
                        font.setWeight(font.Bold)
                        painter.setFont(font)
                        painter.setPen(
                            self._highlighter.get_foreground_color())
                    else:
                        font.setWeight(font.Normal)
                        painter.setFont(font)
                        painter.setPen(QColor(Qt.darkGray))
                    right_padding = self.linenumberarea._right_padding
                    painter.drawText(
                        0,
                        top,
                        self.linenumberarea.width() - right_padding,
                        self.fontMetrics().height(),
                        Qt.AlignRight, str(number),
                    )

                block = block.next()
                top = bottom
                bottom = top + round(self.blockBoundingRect(block).height())
                block_number += 1

    def linenumberarea_width(self):
        """
        Return the line number area width.

        Returns
        -------
        int
            Line number are width in pixels.

        Notes
        -----
        If the line number area is disabled this will return zero.
        """
        width = 0
        if self._linenumber_enabled:
            digits = 1
            count = max(1, self.blockCount())
            while count >= 10:
                count /= 10
                digits += 1

            fm = self.fontMetrics()
            width = (self.linenumberarea._left_padding
                     + self.linenumberarea._right_padding
                     + fm.width('9') * digits)

        return width

    def update_linenumberarea_width(self, new_block_count=None):
        """
        Update the line number area width based on the number of blocks in
        the document.

        Parameters
        ----------
        new_block_count: int
            The current number of blocks in the document.
        """
        self.setViewportMargins(self.linenumberarea_width(), 0, 0, 0)

    def update_linenumberarea(self, rect, dy):
        """
        Update scroll position of line number area.
        """
        if self._linenumber_enabled:
            if dy:
                self.linenumberarea.scroll(0, dy)
            else:
                self.linenumberarea.update(
                    0, rect.y(), self.linenumberarea.width(), rect.height())

            if rect.contains(self.viewport().rect()):
                self.update_linenumberarea_width(0)

    # --- Text and cursor handling
    # ------------------------------------------------------------------------
    def set_selection(self, start, end):
        """
        Set current text selection.

        Parameters
        ----------
        start: int
            Selection start position.
        end: int
            Selection end position.
        """
        cursor = self.textCursor()
        cursor.setPosition(start)
        cursor.setPosition(end, QTextCursor.KeepAnchor)
        self.setTextCursor(cursor)

    def stdkey_backspace(self):
        if not self.has_selected_text():
            self.moveCursor(QTextCursor.PreviousCharacter,
                            QTextCursor.KeepAnchor)
        self.remove_selected_text()

    def restrict_cursor_position(self, position_from, position_to):
        """
        Restrict the cursor from being inside from and to positions.

        Parameters
        ----------
        position_from: int
            Selection start position.
        position_to: int
            Selection end position.
        """
        position_from = self.get_position(position_from)
        position_to = self.get_position(position_to)
        cursor = self.textCursor()
        cursor_position = cursor.position()
        if cursor_position < position_from or cursor_position > position_to:
            self.set_cursor_position(position_to)

    def truncate_selection(self, position_from):
        """
        Restrict the cursor selection to start from the given position.

        Parameters
        ----------
        position_from: int
            Selection start position.
        """
        position_from = self.get_position(position_from)
        cursor = self.textCursor()
        start, end = cursor.selectionStart(), cursor.selectionEnd()
        if start < end:
            start = max([position_from, start])
        else:
            end = max([position_from, end])

        self.set_selection(start, end)

    def set_text(self, text):
        """
        Set `text` of the document.

        Parameters
        ----------
        text: str
            Text to set.
        """
        self.setPlainText(text)

    def append(self, text):
        """
        Add `text` to the end of the document.

        Parameters
        ----------
        text: str
            Text to append.
        """
        cursor = self.textCursor()
        cursor.movePosition(QTextCursor.End)
        cursor.insertText(text)

    # --- Syntax highlighter
    # ------------------------------------------------------------------------
    def rehighlight(self):
        """
        Reapply syntax highligthing to the document.
        """
        if self._highlighter:
            self._highlighter.rehighlight()


if __name__ == "__main__":
    from spyder.utils.qthelpers import qapplication

    app = qapplication()
    editor = SimpleCodeEditor()
    editor.setup_editor(language="markdown")
    editor.set_text("# Hello!")
    editor.show()
    app.exec_()
