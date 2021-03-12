# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""QPlainTextEdit base class"""

# pylint: disable=C0103
# pylint: disable=R0903
# pylint: disable=R0911
# pylint: disable=R0201

# Standard library imports
import os
import sys

# Third party imports
from qtpy.compat import to_qvariant
from qtpy.QtCore import QEvent, QPoint, Qt, Signal, Slot
from qtpy.QtGui import (QClipboard, QColor, QMouseEvent, QTextFormat,
                        QTextOption, QTextCursor)
from qtpy.QtWidgets import QApplication, QMainWindow, QPlainTextEdit, QToolTip

# Local imports
from spyder.config.gui import get_font
from spyder.config.manager import CONF
from spyder.py3compat import PY3, to_text_string
from spyder.widgets.calltip import CallTipWidget, ToolTipWidget
from spyder.widgets.mixins import BaseEditMixin
from spyder.plugins.editor.api.decoration import TextDecoration, DRAW_ORDERS
from spyder.plugins.editor.utils.decoration import TextDecorationsManager
from spyder.plugins.editor.widgets.completion import CompletionWidget
from spyder.plugins.outlineexplorer.api import is_cell_header, document_cells
from spyder.utils.palette import SpyderPalette

class TextEditBaseWidget(QPlainTextEdit, BaseEditMixin):
    """Text edit base widget"""
    BRACE_MATCHING_SCOPE = ('sof', 'eof')
    focus_in = Signal()
    zoom_in = Signal()
    zoom_out = Signal()
    zoom_reset = Signal()
    focus_changed = Signal()
    sig_insert_completion = Signal(str)
    sig_eol_chars_changed = Signal(str)

    def __init__(self, parent=None):
        QPlainTextEdit.__init__(self, parent)
        BaseEditMixin.__init__(self)

        self.has_cell_separators = False
        self.setAttribute(Qt.WA_DeleteOnClose)

        self.extra_selections_dict = {}
        self._restore_selection_pos = None

        # Trailing newlines/spaces trimming
        self.remove_trailing_spaces = False
        self.remove_trailing_newlines = False

        # Add a new line when saving
        self.add_newline = False

        # Code snippets
        self.code_snippets = True

        self.textChanged.connect(self.changed)
        self.cursorPositionChanged.connect(self.cursor_position_changed)

        self.indent_chars = " "*4
        self.tab_stop_width_spaces = 4

        # Code completion / calltips
        if parent is not None:
            mainwin = parent
            while not isinstance(mainwin, QMainWindow):
                mainwin = mainwin.parent()
                if mainwin is None:
                    break
            if mainwin is not None:
                parent = mainwin

        self.completion_widget = CompletionWidget(self, parent)
        self.codecompletion_auto = False
        self.setup_completion()

        self.calltip_widget = CallTipWidget(self, hide_timer_on=False)
        self.tooltip_widget = ToolTipWidget(self, as_tooltip=True)

        self.highlight_current_cell_enabled = False

        # The color values may be overridden by the syntax highlighter
        # Highlight current line color
        self.currentline_color = QColor(
            SpyderPalette.COLOR_ERROR_2).lighter(190)
        self.currentcell_color = QColor(
            SpyderPalette.COLOR_ERROR_2).lighter(194)

        # Brace matching
        self.bracepos = None
        self.matched_p_color = QColor(SpyderPalette.COLOR_SUCCESS_1)
        self.unmatched_p_color = QColor(SpyderPalette.COLOR_ERROR_2)

        self.decorations = TextDecorationsManager(self)

        # Save current cell. This is invalidated as soon as the text changes.
        # Useful to avoid recomputing while scrolling.
        self.current_cell = None

        def reset_current_cell():
            self.current_cell = None

        self.textChanged.connect(reset_current_cell)

    def setup_completion(self):
        size = CONF.get('main', 'completion/size')
        font = get_font()
        self.completion_widget.setup_appearance(size, font)

    def set_indent_chars(self, indent_chars):
        self.indent_chars = indent_chars

    def set_tab_stop_width_spaces(self, tab_stop_width_spaces):
        self.tab_stop_width_spaces = tab_stop_width_spaces
        self.update_tab_stop_width_spaces()

    def set_remove_trailing_spaces(self, flag):
        self.remove_trailing_spaces = flag

    def set_add_newline(self, add_newline):
        self.add_newline = add_newline

    def set_remove_trailing_newlines(self, flag):
        self.remove_trailing_newlines = flag

    def update_tab_stop_width_spaces(self):
        self.setTabStopWidth(self.fontMetrics().width(
                             ' ' * self.tab_stop_width_spaces))

    def set_palette(self, background, foreground):
        """
        Set text editor palette colors:
        background color and caret (text cursor) color
        """
        # Because QtStylsheet overrides QPalette and because some style do not
        # use the palette for all drawing (e.g. macOS styles), the background
        # and foreground color of each TextEditBaseWidget instance must be set
        # with a stylesheet extended with an ID Selector.
        # Fixes spyder-ide/spyder#2028, spyder-ide/spyder#8069 and
        # spyder-ide/spyder#9248.
        if not self.objectName():
            self.setObjectName(self.__class__.__name__ + str(id(self)))
        style = "QPlainTextEdit#%s {background: %s; color: %s;}" % \
                (self.objectName(), background.name(), foreground.name())
        self.setStyleSheet(style)

    # ---- Extra selections
    def get_extra_selections(self, key):
        """Return editor extra selections.

        Args:
            key (str) name of the extra selections group

        Returns:
            list of sourcecode.api.TextDecoration.
        """
        return self.extra_selections_dict.get(key, [])

    def set_extra_selections(self, key, extra_selections):
        """Set extra selections for a key.

        Also assign draw orders to leave current_cell and current_line
        in the background (and avoid them to cover other decorations)

        NOTE: This will remove previous decorations added to the same key.

        Args:
            key (str) name of the extra selections group.
            extra_selections (list of sourcecode.api.TextDecoration).
        """
        # use draw orders to highlight current_cell and current_line first
        draw_order = DRAW_ORDERS.get(key)
        if draw_order is None:
            draw_order = DRAW_ORDERS.get('on_top')

        for selection in extra_selections:
            selection.draw_order = draw_order
            selection.kind = key

        self.clear_extra_selections(key)
        self.extra_selections_dict[key] = extra_selections

    def update_extra_selections(self):
        """Add extra selections to DecorationsManager.

        TODO: This method could be remove it and decorations could be
        added/removed in set_extra_selections/clear_extra_selections.
        """
        extra_selections = []

        for key, extra in list(self.extra_selections_dict.items()):
            extra_selections.extend(extra)
        self.decorations.add(extra_selections)

    def clear_extra_selections(self, key):
        """Remove decorations added through set_extra_selections.

        Args:
            key (str) name of the extra selections group.
        """
        for decoration in self.extra_selections_dict.get(key, []):
            self.decorations.remove(decoration)
        self.extra_selections_dict[key] = []
        self.update()

    def changed(self):
        """Emit changed signal"""
        self.modificationChanged.emit(self.document().isModified())

    def get_visible_block_numbers(self):
        """Get the first and last visible block numbers."""
        first = self.firstVisibleBlock().blockNumber()
        bottom_right = QPoint(self.viewport().width() - 1,
                              self.viewport().height() - 1)
        last = self.cursorForPosition(bottom_right).blockNumber()
        return (first, last)

    def get_buffer_block_numbers(self):
        """
        Get the first and last block numbers of a region that covers
        the visible one plus a buffer of half that region above and
        below to make more fluid certain operations.
        """
        first_visible, last_visible = self.get_visible_block_numbers()
        buffer_height = round((last_visible - first_visible) / 2)

        first = first_visible - buffer_height
        first = 0 if first < 0 else first

        last = last_visible + buffer_height
        last = self.blockCount() if last > self.blockCount() else last

        return (first, last)

    # ------Highlight current line
    def highlight_current_line(self):
        """Highlight current line"""
        selection = TextDecoration(self.textCursor())
        selection.format.setProperty(QTextFormat.FullWidthSelection,
                                     to_qvariant(True))
        selection.format.setBackground(self.currentline_color)
        selection.cursor.clearSelection()
        self.set_extra_selections('current_line', [selection])
        self.update_extra_selections()

    def unhighlight_current_line(self):
        """Unhighlight current line"""
        self.clear_extra_selections('current_line')

    # ------Highlight current cell
    def highlight_current_cell(self):
        """Highlight current cell"""
        if (not self.has_cell_separators or
                not self.highlight_current_cell_enabled):
            return
        cursor, whole_file_selected = self.select_current_cell()
        selection = TextDecoration(cursor)
        selection.format.setProperty(QTextFormat.FullWidthSelection,
                                     to_qvariant(True))
        selection.format.setBackground(self.currentcell_color)

        if whole_file_selected:
            self.clear_extra_selections('current_cell')
        else:
            self.set_extra_selections('current_cell', [selection])
            self.update_extra_selections()

    def unhighlight_current_cell(self):
        """Unhighlight current cell"""
        self.clear_extra_selections('current_cell')

    def in_comment(self, cursor=None, position=None):
        """Returns True if the given position is inside a comment.

        Trivial default implementation. To be overridden by subclass.
        This function is used to define the default behaviour of
        self.find_brace_match.
        """
        return False

    def in_string(self, cursor=None, position=None):
        """Returns True if the given position is inside a string.

        Trivial default implementation. To be overridden by subclass.
        This function is used to define the default behaviour of
        self.find_brace_match.
        """
        return False

    def find_brace_match(self, position, brace, forward,
                         ignore_brace=None, stop=None):
        """Returns position of matching brace.

        Parameters
        ----------
        position : int
            The position of the brace to be matched.
        brace : {'[', ']', '(', ')', '{', '}'}
            The brace character to be matched.
            [ <-> ], ( <-> ), { <-> }
        forward : boolean
            Whether to search forwards or backwards for a match.
        ignore_brace : callable taking int returning boolean, optional
            Whether to ignore a brace (as function of position).
        stop : callable taking int returning boolean, optional
            Whether to stop the search early (as function of position).

        If both *ignore_brace* and *stop* are None, then brace matching
        is handled differently depending on whether *position* is
        inside a string, comment or regular code. If in regular code,
        then any braces inside strings and comments are ignored. If in a
        string/comment, then only braces in the same string/comment are
        considered potential matches. The functions self.in_comment and
        self.in_string are used to determine string/comment/code status
        of characters in this case.

        If exactly one of *ignore_brace* and *stop* is None, then it is
        replaced by a function returning False for every position. I.e.:
            lambda pos: False

        Returns
        -------
        The position of the matching brace. If no matching brace
        exists, then None is returned.
        """

        if ignore_brace is None and stop is None:
            if self.in_string(position=position):
                # Only search inside the current string
                def stop(pos):
                    return not self.in_string(position=pos)
            elif self.in_comment(position=position):
                # Only search inside the current comment
                def stop(pos):
                    return not self.in_comment(position=pos)
            else:
                # Ignore braces inside strings and comments
                def ignore_brace(pos):
                    return (self.in_string(position=pos) or
                            self.in_comment(position=pos))

        # Deal with search range and direction
        start_pos, end_pos = self.BRACE_MATCHING_SCOPE
        if forward:
            closing_brace = {'(': ')', '[': ']', '{': '}'}[brace]
            text = self.get_text(position, end_pos, remove_newlines=False)
        else:
            # Handle backwards search with the same code as forwards
            # by reversing the string to be searched.
            closing_brace = {')': '(', ']': '[', '}': '{'}[brace]
            text = self.get_text(start_pos, position+1, remove_newlines=False)
            text = text[-1::-1]  # reverse

        def ind2pos(index):
            """Computes editor position from search index."""
            return (position + index) if forward else (position - index)

        # Search starts at the first position after the given one
        # (which is assumed to contain a brace).
        i_start_close = 1
        i_start_open = 1
        while True:
            i_close = text.find(closing_brace, i_start_close)
            i_start_close = i_close+1  # next potential start
            if i_close == -1:
                return  # no matching brace exists
            elif ignore_brace is None or not ignore_brace(ind2pos(i_close)):
                while True:
                    i_open = text.find(brace, i_start_open, i_close)
                    i_start_open = i_open+1  # next potential start
                    if i_open == -1:
                        # found matching brace, but should we have
                        # stopped before this point?
                        if stop is not None:
                            # There's room for optimization here...
                            for i in range(1, i_close+1):
                                if stop(ind2pos(i)):
                                    return
                        return ind2pos(i_close)
                    elif (ignore_brace is None or
                          not ignore_brace(ind2pos(i_open))):
                        break  # must find new closing brace

    def __highlight(self, positions, color=None, cancel=False):
        if cancel:
            self.clear_extra_selections('brace_matching')
            return
        extra_selections = []
        for position in positions:
            if position > self.get_position('eof'):
                return
            selection = TextDecoration(self.textCursor())
            selection.format.setBackground(color)
            selection.cursor.clearSelection()
            selection.cursor.setPosition(position)
            selection.cursor.movePosition(QTextCursor.NextCharacter,
                                          QTextCursor.KeepAnchor)
            extra_selections.append(selection)
        self.set_extra_selections('brace_matching', extra_selections)
        self.update_extra_selections()

    def cursor_position_changed(self):
        """Handle brace matching."""
        # Clear last brace highlight (if any)
        if self.bracepos is not None:
            self.__highlight(self.bracepos, cancel=True)
            self.bracepos = None

        # Get the current cursor position, check if it is at a brace,
        # and, if so, determine the direction in which to search for able
        # matching brace.
        cursor = self.textCursor()
        if cursor.position() == 0:
            return
        cursor.movePosition(QTextCursor.PreviousCharacter,
                            QTextCursor.KeepAnchor)
        text = to_text_string(cursor.selectedText())
        if text in (')', ']', '}'):
            forward = False
        elif text in ('(', '[', '{'):
            forward = True
        else:
            return

        pos1 = cursor.position()
        pos2 = self.find_brace_match(pos1, text, forward=forward)

        # Set a new brace highlight
        if pos2 is not None:
            self.bracepos = (pos1, pos2)
            self.__highlight(self.bracepos, color=self.matched_p_color)
        else:
            self.bracepos = (pos1,)
            self.__highlight(self.bracepos, color=self.unmatched_p_color)

    # -----Widget setup and options
    def set_wrap_mode(self, mode=None):
        """
        Set wrap mode
        Valid *mode* values: None, 'word', 'character'
        """
        if mode == 'word':
            wrap_mode = QTextOption.WrapAtWordBoundaryOrAnywhere
        elif mode == 'character':
            wrap_mode = QTextOption.WrapAnywhere
        else:
            wrap_mode = QTextOption.NoWrap
        self.setWordWrapMode(wrap_mode)

    # ------Reimplementing Qt methods
    @Slot()
    def copy(self):
        """
        Reimplement Qt method
        Copy text to clipboard with correct EOL chars
        """
        if self.get_selected_text():
            QApplication.clipboard().setText(self.get_selected_text())

    def toPlainText(self):
        """
        Reimplement Qt method
        Fix PyQt4 bug on Windows and Python 3
        """
        # Fix what appears to be a PyQt4 bug when getting file
        # contents under Windows and PY3. This bug leads to
        # corruptions when saving files with certain combinations
        # of unicode chars on them (like the one attached on
        # spyder-ide/spyder#1546).
        if os.name == 'nt' and PY3:
            text = self.get_text('sof', 'eof')
            return text.replace('\u2028', '\n').replace('\u2029', '\n')\
                       .replace('\u0085', '\n')
        else:
            return super(TextEditBaseWidget, self).toPlainText()

    def keyPressEvent(self, event):
        key = event.key()
        ctrl = event.modifiers() & Qt.ControlModifier
        meta = event.modifiers() & Qt.MetaModifier
        # Use our own copy method for {Ctrl,Cmd}+C to avoid Qt
        # copying text in HTML. See spyder-ide/spyder#2285.
        if (ctrl or meta) and key == Qt.Key_C:
            self.copy()
        else:
            super(TextEditBaseWidget, self).keyPressEvent(event)

    # ------Text: get, set, ...
    def get_cell_list(self):
        """Get all cells."""
        # Reimplemented in childrens
        return []

    def get_selection_as_executable_code(self, cursor=None):
        """Return selected text as a processed text,
        to be executable in a Python/IPython interpreter"""
        ls = self.get_line_separator()

        _indent = lambda line: len(line)-len(line.lstrip())

        line_from, line_to = self.get_selection_bounds(cursor)
        text = self.get_selected_text(cursor)
        if not text:
            return

        lines = text.split(ls)
        if len(lines) > 1:
            # Multiline selection -> eventually fixing indentation
            original_indent = _indent(self.get_text_line(line_from))
            text = (" "*(original_indent-_indent(lines[0])))+text

        # If there is a common indent to all lines, find it.
        # Moving from bottom line to top line ensures that blank
        # lines inherit the indent of the line *below* it,
        # which is the desired behavior.
        min_indent = 999
        current_indent = 0
        lines = text.split(ls)
        for i in range(len(lines)-1, -1, -1):
            line = lines[i]
            if line.strip():
                current_indent = _indent(line)
                min_indent = min(current_indent, min_indent)
            else:
                lines[i] = ' ' * current_indent
        if min_indent:
            lines = [line[min_indent:] for line in lines]

        # Remove any leading whitespace or comment lines
        # since they confuse the reserved word detector that follows below
        lines_removed = 0
        while lines:
            first_line = lines[0].lstrip()
            if first_line == '' or first_line[0] == '#':
                lines_removed += 1
                lines.pop(0)
            else:
                break

        # Add an EOL character after the last line of code so that it gets
        # evaluated automatically by the console and any quote characters
        # are separated from the triple quotes of runcell
        lines.append(ls)

        # Add removed lines back to have correct traceback line numbers
        leading_lines_str = ls * lines_removed

        return leading_lines_str + ls.join(lines)

    def get_cell_as_executable_code(self, cursor=None):
        """Return cell contents as executable code."""
        if cursor is None:
            cursor = self.textCursor()
        ls = self.get_line_separator()
        cursor, __ = self.select_current_cell(cursor)
        line_from, __ = self.get_selection_bounds(cursor)
        # Get the block for the first cell line
        start = cursor.selectionStart()
        block = self.document().findBlock(start)
        if not is_cell_header(block) and start > 0:
            block = self.document().findBlock(start - 1)
        # Get text
        text = self.get_selection_as_executable_code(cursor)
        if text is not None:
            text = ls * line_from + text
        return text, block

    def select_current_cell(self, cursor=None):
        """
        Select cell under cursor in the visible portion of the file
        cell = group of lines separated by CELL_SEPARATORS
        returns
         -the textCursor
         -a boolean indicating if the entire file is selected
        """
        if cursor is None:
            cursor = self.textCursor()

        if self.current_cell:
            current_cell, cell_full_file = self.current_cell
            cell_start_pos = current_cell.selectionStart()
            cell_end_position = current_cell.selectionEnd()
            # Check if the saved current cell is still valid
            if cell_start_pos <= cursor.position() < cell_end_position:
                return current_cell, cell_full_file
            else:
                self.current_cell = None

        block = cursor.block()
        try:
            if is_cell_header(block):
                header = block.userData().oedata
            else:
                header = next(document_cells(
                    block, forward=False,
                    cell_list=self.get_cell_list()))
            cell_start_pos = header.block.position()
            cell_at_file_start = False
            cursor.setPosition(cell_start_pos)
        except StopIteration:
            # This cell has no header, so it is the first cell.
            cell_at_file_start = True
            cursor.movePosition(QTextCursor.Start)

        try:
            footer = next(document_cells(
                block, forward=True,
                cell_list=self.get_cell_list()))
            cell_end_position = footer.block.position()
            cell_at_file_end = False
            cursor.setPosition(cell_end_position, QTextCursor.KeepAnchor)
        except StopIteration:
            # This cell has no next header, so it is the last cell.
            cell_at_file_end = True
            cursor.movePosition(QTextCursor.End, QTextCursor.KeepAnchor)

        cell_full_file = cell_at_file_start and cell_at_file_end
        self.current_cell = (cursor, cell_full_file)

        return cursor, cell_full_file

    def go_to_next_cell(self):
        """Go to the next cell of lines"""
        cursor = self.textCursor()
        block = cursor.block()
        try:
            footer = next(document_cells(
                block, forward=True,
                cell_list=self.get_cell_list()))
            cursor.setPosition(footer.block.position())
        except StopIteration:
            return
        self.setTextCursor(cursor)

    def go_to_previous_cell(self):
        """Go to the previous cell of lines"""
        cursor = self.textCursor()
        block = cursor.block()
        if is_cell_header(block):
            block = block.previous()
        try:
            header = next(document_cells(
                block, forward=False,
                cell_list=self.get_cell_list()))
            cursor.setPosition(header.block.position())
        except StopIteration:
            return
        self.setTextCursor(cursor)

    def get_line_count(self):
        """Return document total line number"""
        return self.blockCount()

    def paintEvent(self, e):
        """
        Override Qt method to restore text selection after text gets inserted
        at the current position of the cursor.

        See spyder-ide/spyder#11089 for more info.
        """
        if self._restore_selection_pos is not None:
            self.__restore_selection(*self._restore_selection_pos)
            self._restore_selection_pos = None
        super(TextEditBaseWidget, self).paintEvent(e)

    def __save_selection(self):
        """Save current cursor selection and return position bounds"""
        cursor = self.textCursor()
        return cursor.selectionStart(), cursor.selectionEnd()

    def __restore_selection(self, start_pos, end_pos):
        """Restore cursor selection from position bounds"""
        cursor = self.textCursor()
        cursor.setPosition(start_pos)
        cursor.setPosition(end_pos, QTextCursor.KeepAnchor)
        self.setTextCursor(cursor)

    def __duplicate_line_or_selection(self, after_current_line=True):
        """Duplicate current line or selected text"""
        cursor = self.textCursor()
        cursor.beginEditBlock()
        cur_pos = cursor.position()
        start_pos, end_pos = self.__save_selection()
        end_pos_orig = end_pos
        if to_text_string(cursor.selectedText()):
            cursor.setPosition(end_pos)
            # Check if end_pos is at the start of a block: if so, starting
            # changes from the previous block
            cursor.movePosition(QTextCursor.StartOfBlock,
                                QTextCursor.KeepAnchor)
            if not to_text_string(cursor.selectedText()):
                cursor.movePosition(QTextCursor.PreviousBlock)
                end_pos = cursor.position()

        cursor.setPosition(start_pos)
        cursor.movePosition(QTextCursor.StartOfBlock)
        while cursor.position() <= end_pos:
            cursor.movePosition(QTextCursor.EndOfBlock, QTextCursor.KeepAnchor)
            if cursor.atEnd():
                cursor_temp = QTextCursor(cursor)
                cursor_temp.clearSelection()
                cursor_temp.insertText(self.get_line_separator())
                break
            cursor.movePosition(QTextCursor.NextBlock, QTextCursor.KeepAnchor)
        text = cursor.selectedText()
        cursor.clearSelection()

        if not after_current_line:
            # Moving cursor before current line/selected text
            cursor.setPosition(start_pos)
            cursor.movePosition(QTextCursor.StartOfBlock)
            start_pos += len(text)
            end_pos_orig += len(text)
            cur_pos += len(text)

        # We save the end and start position of the selection, so that it
        # can be restored within the paint event that is triggered by the
        # text insertion. This is done to prevent a graphical glitch that
        # occurs when text gets inserted at the current position of the cursor.
        # See spyder-ide/spyder#11089 for more info.
        if cur_pos == start_pos:
            self._restore_selection_pos = (end_pos_orig, start_pos)
        else:
            self._restore_selection_pos = (start_pos, end_pos_orig)
        cursor.insertText(text)
        cursor.endEditBlock()

        self.document_did_change()

    def duplicate_line_down(self):
        """
        Copy current line or selected text and paste the duplicated text
        *after* the current line or selected text.
        """
        self.__duplicate_line_or_selection(after_current_line=False)

    def duplicate_line_up(self):
        """
        Copy current line or selected text and paste the duplicated text
        *before* the current line or selected text.
        """
        self.__duplicate_line_or_selection(after_current_line=True)

    def __move_line_or_selection(self, after_current_line=True):
        """Move current line or selected text"""
        cursor = self.textCursor()
        cursor.beginEditBlock()
        start_pos, end_pos = self.__save_selection()
        last_line = False

        # ------ Select text
        # Get selection start location
        cursor.setPosition(start_pos)
        cursor.movePosition(QTextCursor.StartOfBlock)
        start_pos = cursor.position()

        # Get selection end location
        cursor.setPosition(end_pos)
        if not cursor.atBlockStart() or end_pos == start_pos:
            cursor.movePosition(QTextCursor.EndOfBlock)
            cursor.movePosition(QTextCursor.NextBlock)
        end_pos = cursor.position()

        # Check if selection ends on the last line of the document
        if cursor.atEnd():
            if not cursor.atBlockStart() or end_pos == start_pos:
                last_line = True

        # ------ Stop if at document boundary
        cursor.setPosition(start_pos)
        if cursor.atStart() and not after_current_line:
            # Stop if selection is already at top of the file while moving up
            cursor.endEditBlock()
            self.setTextCursor(cursor)
            self.__restore_selection(start_pos, end_pos)
            return

        cursor.setPosition(end_pos, QTextCursor.KeepAnchor)
        if last_line and after_current_line:
            # Stop if selection is already at end of the file while moving down
            cursor.endEditBlock()
            self.setTextCursor(cursor)
            self.__restore_selection(start_pos, end_pos)
            return

        # ------ Move text
        sel_text = to_text_string(cursor.selectedText())
        cursor.removeSelectedText()

        if after_current_line:
            # Shift selection down
            text = to_text_string(cursor.block().text())
            sel_text = os.linesep + sel_text[0:-1]  # Move linesep at the start
            cursor.movePosition(QTextCursor.EndOfBlock)
            start_pos += len(text)+1
            end_pos += len(text)
            if not cursor.atEnd():
                end_pos += 1
        else:
            # Shift selection up
            if last_line:
                # Remove the last linesep and add it to the selected text
                cursor.deletePreviousChar()
                sel_text = sel_text + os.linesep
                cursor.movePosition(QTextCursor.StartOfBlock)
                end_pos += 1
            else:
                cursor.movePosition(QTextCursor.PreviousBlock)
            text = to_text_string(cursor.block().text())
            start_pos -= len(text)+1
            end_pos -= len(text)+1

        cursor.insertText(sel_text)

        cursor.endEditBlock()
        self.setTextCursor(cursor)
        self.__restore_selection(start_pos, end_pos)

        self.document_did_change()

    def move_line_up(self):
        """Move up current line or selected text"""
        self.__move_line_or_selection(after_current_line=False)

    def move_line_down(self):
        """Move down current line or selected text"""
        self.__move_line_or_selection(after_current_line=True)

    def go_to_new_line(self):
        """Go to the end of the current line and create a new line"""
        self.stdkey_end(False, False)
        self.insert_text(self.get_line_separator())

    def extend_selection_to_complete_lines(self):
        """Extend current selection to complete lines"""
        cursor = self.textCursor()
        start_pos, end_pos = cursor.selectionStart(), cursor.selectionEnd()
        cursor.setPosition(start_pos)
        cursor.setPosition(end_pos, QTextCursor.KeepAnchor)
        if cursor.atBlockStart():
            cursor.movePosition(QTextCursor.PreviousBlock,
                                QTextCursor.KeepAnchor)
            cursor.movePosition(QTextCursor.EndOfBlock,
                                QTextCursor.KeepAnchor)
        self.setTextCursor(cursor)

    def delete_line(self, cursor=None):
        """Delete current line."""
        if cursor is None:
            cursor = self.textCursor()
        if self.has_selected_text():
            self.extend_selection_to_complete_lines()
            start_pos, end_pos = cursor.selectionStart(), cursor.selectionEnd()
            cursor.setPosition(start_pos)
        else:
            start_pos = end_pos = cursor.position()
        cursor.beginEditBlock()
        cursor.setPosition(start_pos)
        cursor.movePosition(QTextCursor.StartOfBlock)
        while cursor.position() <= end_pos:
            cursor.movePosition(QTextCursor.EndOfBlock, QTextCursor.KeepAnchor)
            if cursor.atEnd():
                break
            cursor.movePosition(QTextCursor.NextBlock, QTextCursor.KeepAnchor)
        cursor.removeSelectedText()
        cursor.endEditBlock()
        self.ensureCursorVisible()
        self.document_did_change()

    def set_selection(self, start, end):
        cursor = self.textCursor()
        cursor.setPosition(start)
        cursor.setPosition(end, QTextCursor.KeepAnchor)
        self.setTextCursor(cursor)

    def truncate_selection(self, position_from):
        """Unselect read-only parts in shell, like prompt"""
        position_from = self.get_position(position_from)
        cursor = self.textCursor()
        start, end = cursor.selectionStart(), cursor.selectionEnd()
        if start < end:
            start = max([position_from, start])
        else:
            end = max([position_from, end])
        self.set_selection(start, end)

    def restrict_cursor_position(self, position_from, position_to):
        """In shell, avoid editing text except between prompt and EOF"""
        position_from = self.get_position(position_from)
        position_to = self.get_position(position_to)
        cursor = self.textCursor()
        cursor_position = cursor.position()
        if cursor_position < position_from or cursor_position > position_to:
            self.set_cursor_position(position_to)

    # ------Code completion / Calltips
    def select_completion_list(self):
        """Completion list is active, Enter was just pressed"""
        self.completion_widget.item_selected()

    def insert_completion(self, completion, completion_position):
        """Insert a completion into the editor.

        completion_position is where the completion was generated.

        The replacement range is computed using the (LSP) completion's
        textEdit field if it exists. Otherwise, we replace from the
        start of the word under the cursor.
        """
        if not completion:
            return

        cursor = self.textCursor()

        has_selected_text = self.has_selected_text()
        selection_start, selection_end = self.get_selection_start_end()

        if isinstance(completion, dict) and 'textEdit' in completion:
            completion_range = completion['textEdit']['range']
            start = completion_range['start']
            end = completion_range['end']
            if isinstance(completion_range['start'], dict):
                start_line, start_col = start['line'], start['character']
                start = self.get_position_line_number(start_line, start_col)
            if isinstance(completion_range['start'], dict):
                end_line, end_col = end['line'], end['character']
                end = self.get_position_line_number(end_line, end_col)
            cursor.setPosition(start)
            cursor.setPosition(end, QTextCursor.KeepAnchor)
            text = to_text_string(completion['textEdit']['newText'])
        else:
            text = completion
            if isinstance(completion, dict):
                text = completion['insertText']
            text = to_text_string(text)

            # Get word on the left of the cursor.
            result = self.get_current_word_and_position(completion=True)
            if result is not None:
                current_text, start_position = result
                end_position = start_position + len(current_text)
                # Check if the completion position is in the expected range
                if not start_position <= completion_position <= end_position:
                    return
                cursor.setPosition(start_position)
                # Remove the word under the cursor
                cursor.setPosition(end_position,
                                   QTextCursor.KeepAnchor)
            else:
                # Check if we are in the correct position
                if cursor.position() != completion_position:
                    return

        if has_selected_text:
            self.sig_will_remove_selection.emit(selection_start, selection_end)

        cursor.removeSelectedText()
        self.setTextCursor(cursor)

        # Add text
        if self.objectName() == 'console':
            # Handle completions for the internal console
            self.insert_text(text)
        else:
            self.sig_insert_completion.emit(text)
            self.document_did_change()

    def is_completion_widget_visible(self):
        """Return True is completion list widget is visible"""
        try:
            return self.completion_widget.isVisible()
        except RuntimeError:
            # This is to avoid a RuntimeError exception when the widget is
            # already been deleted. See spyder-ide/spyder#13248.
            return False

    def hide_completion_widget(self, focus_to_parent=True):
        """Hide completion widget and tooltip."""
        self.completion_widget.hide(focus_to_parent=focus_to_parent)
        QToolTip.hideText()

    # ------Standard keys
    def stdkey_clear(self):
        if not self.has_selected_text():
            self.moveCursor(QTextCursor.NextCharacter, QTextCursor.KeepAnchor)
        self.remove_selected_text()

    def stdkey_backspace(self):
        if not self.has_selected_text():
            self.moveCursor(QTextCursor.PreviousCharacter,
                            QTextCursor.KeepAnchor)
        self.remove_selected_text()

    def __get_move_mode(self, shift):
        return QTextCursor.KeepAnchor if shift else QTextCursor.MoveAnchor

    def stdkey_up(self, shift):
        self.moveCursor(QTextCursor.Up, self.__get_move_mode(shift))

    def stdkey_down(self, shift):
        self.moveCursor(QTextCursor.Down, self.__get_move_mode(shift))

    def stdkey_tab(self):
        self.insert_text(self.indent_chars)

    def stdkey_home(self, shift, ctrl, prompt_pos=None):
        """Smart HOME feature: cursor is first moved at
        indentation position, then at the start of the line"""
        move_mode = self.__get_move_mode(shift)
        if ctrl:
            self.moveCursor(QTextCursor.Start, move_mode)
        else:
            cursor = self.textCursor()
            if prompt_pos is None:
                start_position = self.get_position('sol')
            else:
                start_position = self.get_position(prompt_pos)
            text = self.get_text(start_position, 'eol')
            indent_pos = start_position+len(text)-len(text.lstrip())
            if cursor.position() != indent_pos:
                cursor.setPosition(indent_pos, move_mode)
            else:
                cursor.setPosition(start_position, move_mode)
            self.setTextCursor(cursor)

    def stdkey_end(self, shift, ctrl):
        move_mode = self.__get_move_mode(shift)
        if ctrl:
            self.moveCursor(QTextCursor.End, move_mode)
        else:
            self.moveCursor(QTextCursor.EndOfBlock, move_mode)

    # ----Qt Events
    def mousePressEvent(self, event):
        """Reimplement Qt method"""
        if sys.platform.startswith('linux') and event.button() == Qt.MidButton:
            self.calltip_widget.hide()
            self.setFocus()
            event = QMouseEvent(QEvent.MouseButtonPress, event.pos(),
                                Qt.LeftButton, Qt.LeftButton, Qt.NoModifier)
            QPlainTextEdit.mousePressEvent(self, event)
            QPlainTextEdit.mouseReleaseEvent(self, event)
            # Send selection text to clipboard to be able to use
            # the paste method and avoid the strange spyder-ide/spyder#1445.
            # NOTE: This issue seems a focusing problem but it
            # seems really hard to track
            mode_clip = QClipboard.Clipboard
            mode_sel = QClipboard.Selection
            text_clip = QApplication.clipboard().text(mode=mode_clip)
            text_sel = QApplication.clipboard().text(mode=mode_sel)
            QApplication.clipboard().setText(text_sel, mode=mode_clip)
            self.paste()
            QApplication.clipboard().setText(text_clip, mode=mode_clip)
        else:
            self.calltip_widget.hide()
            QPlainTextEdit.mousePressEvent(self, event)

    def focusInEvent(self, event):
        """Reimplemented to handle focus"""
        self.focus_changed.emit()
        self.focus_in.emit()
        QPlainTextEdit.focusInEvent(self, event)

    def focusOutEvent(self, event):
        """Reimplemented to handle focus"""
        self.focus_changed.emit()
        QPlainTextEdit.focusOutEvent(self, event)

    def wheelEvent(self, event):
        """Reimplemented to emit zoom in/out signals when Ctrl is pressed"""
        # This feature is disabled on MacOS, see spyder-ide/spyder#1510.
        if sys.platform != 'darwin':
            if event.modifiers() & Qt.ControlModifier:
                if hasattr(event, 'angleDelta'):
                    if event.angleDelta().y() < 0:
                        self.zoom_out.emit()
                    elif event.angleDelta().y() > 0:
                        self.zoom_in.emit()
                elif hasattr(event, 'delta'):
                    if event.delta() < 0:
                        self.zoom_out.emit()
                    elif event.delta() > 0:
                        self.zoom_in.emit()
                return

        QPlainTextEdit.wheelEvent(self, event)

        # Needed to prevent stealing focus when scrolling.
        # If the current widget with focus is the CompletionWidget, it means
        # it's being displayed in the editor, so we need to hide it and give
        # focus back to the editor. If not, we need to leave the focus in
        # the widget that currently has it.
        # See spyder-ide/spyder#11502
        current_widget = QApplication.focusWidget()
        if isinstance(current_widget, CompletionWidget):
            self.hide_completion_widget(focus_to_parent=True)
        else:
            self.hide_completion_widget(focus_to_parent=False)

    def position_widget_at_cursor(self, widget):
        # Retrieve current screen height
        desktop = QApplication.desktop()
        srect = desktop.availableGeometry(desktop.screenNumber(widget))

        left, top, right, bottom = (srect.left(), srect.top(),
                                    srect.right(), srect.bottom())
        ancestor = widget.parent()
        if ancestor:
            left = max(left, ancestor.x())
            top = max(top, ancestor.y())
            right = min(right, ancestor.x() + ancestor.width())
            bottom = min(bottom, ancestor.y() + ancestor.height())

        point = self.cursorRect().bottomRight()
        point = self.calculate_real_position(point)
        point = self.mapToGlobal(point)
        # Move to left of cursor if not enough space on right
        widget_right = point.x() + widget.width()
        if widget_right > right:
            point.setX(point.x() - widget.width())
        # Push to right if not enough space on left
        if point.x() < left:
            point.setX(left)

        # Moving widget above if there is not enough space below
        widget_bottom = point.y() + widget.height()
        x_position = point.x()
        if widget_bottom > bottom:
            point = self.cursorRect().topRight()
            point = self.mapToGlobal(point)
            point.setX(x_position)
            point.setY(point.y() - widget.height())

        if ancestor is not None:
            # Useful only if we set parent to 'ancestor' in __init__
            point = ancestor.mapFromGlobal(point)

        widget.move(point)

    def calculate_real_position(self, point):
        return point
