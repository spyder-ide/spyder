# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""
Mixin to manage editing with multiple cursors.
"""

# Standard library imports
import functools
import itertools

# Third party imports
from qtpy.QtCore import Qt, QTimer, Slot
from qtpy.QtGui import (
    QColor, QFontMetrics, QPaintEvent, QPainter, QTextCursor, QKeyEvent
)
from qtpy.QtWidgets import QApplication

# Local imports
from spyder.plugins.editor.api.decoration import TextDecoration
from spyder.utils.palette import SpyderPalette


class MultiCursorMixin:
    """Mixin to manage editing with multiple cursors."""

    def init_multi_cursor(self):
        """Initialize attrs and callbacks for multi-cursor functionality"""
        # actual default comes from setup_editor default args
        self.multi_cursor_enabled = False
        self.cursor_width = self.get_conf('cursor/width', section='main')
        self.overwrite_mode = self.overwriteMode()

        # Track overwrite manually when for painting reasons with multi-cursor
        self.setOverwriteMode(False)
        self.setCursorWidth(0)  # draw our own cursor
        self.extra_cursors = []
        self.cursor_blink_state = False
        self.cursor_blink_timer = QTimer(self)
        self.cursor_blink_timer.setInterval(
            QApplication.cursorFlashTime() // 2
        )
        self.cursor_blink_timer.timeout.connect(
            self._on_cursor_blinktimer_timeout
        )
        self.focus_in.connect(self.start_cursor_blink)
        self.focus_changed.connect(self.stop_cursor_blink)
        self.painted.connect(self.paint_cursors)
        self.multi_cursor_ignore_history = False
        self._drag_cursor = None

    def toggle_multi_cursor(self, enabled):
        """Enable/disable multi-cursor editing."""
        self.multi_cursor_enabled = enabled

        # TODO: Any restrictions on enabling? only python-like? only code?
        if not enabled:
            self.clear_extra_cursors()

    def add_cursor(self, cursor: QTextCursor):
        """Add this cursor to the list of extra cursors"""
        if self.multi_cursor_enabled:
            self.extra_cursors.append(cursor)
            self.merge_extra_cursors(True)

    def add_column_cursor(self, event):
        """
        Add a cursor on each row between primary cursor and click location.
        """

        if not self.multi_cursor_enabled:
            return

        self.multi_cursor_ignore_history = True

        # Ctrl-Shift-Alt click adds colum of cursors towards primary
        # cursor
        cursor_for_pos = self.cursorForPosition(event.pos())
        first_cursor = self.textCursor()
        anchor_block = first_cursor.block()
        anchor_col = first_cursor.anchor() - anchor_block.position()
        pos_block = cursor_for_pos.block()
        pos_col = cursor_for_pos.positionInBlock()

        # Move primary cursor to pos_col
        p_col = min(len(anchor_block.text()), pos_col)

        # block.length() includes line separator? just \n?
        # use len(block.text()) instead
        first_cursor.setPosition(anchor_block.position() + p_col,
                                 QTextCursor.MoveMode.KeepAnchor)
        self.setTextCursor(first_cursor)
        block = anchor_block
        while block != pos_block:
            # Get the next block
            if anchor_block < pos_block:
                block = block.next()
            else:
                block = block.previous()

            # Add a cursor for this block
            if block.isVisible() and block.isValid():
                cursor = QTextCursor(first_cursor)

                a_col = min(len(block.text()), anchor_col)
                cursor.setPosition(block.position() + a_col,
                                   QTextCursor.MoveMode.MoveAnchor)
                p_col = min(len(block.text()), pos_col)
                cursor.setPosition(block.position() + p_col,
                                   QTextCursor.MoveMode.KeepAnchor)
                self.add_cursor(cursor)

        self.multi_cursor_ignore_history = False
        self.cursorPositionChanged.emit()

    def add_remove_cursor(self, event):
        """Add or remove extra cursor on mouse click event"""

        if not self.multi_cursor_enabled:
            return

        self.multi_cursor_ignore_history = True

        # Move existing primary cursor to extra_cursors list and set
        # new primary cursor
        cursor_for_pos = self.cursorForPosition(event.pos())
        old_cursor = self.textCursor()

        # Don't attempt to remove cursor if there's only one
        removed_cursor = False
        if self.extra_cursors:
            same_cursor = None
            for cursor in self.all_cursors:
                if cursor_for_pos.position() == cursor.position():
                    same_cursor = cursor
                    break
            if same_cursor is not None:
                removed_cursor = True
                if same_cursor in self.extra_cursors:
                    # cursor to be removed was not primary
                    self.extra_cursors.remove(same_cursor)
                else:
                    # cursor to be removed is primary cursor
                    # pick a new primary by position
                    new_primary = max(
                        self.extra_cursors,
                        key=lambda cursor: cursor.position()
                    )
                    self.extra_cursors.remove(new_primary)
                    self.setTextCursor(new_primary)

                # Possibly clear selection of removed cursor
                self.set_extra_cursor_selections()

        if not removed_cursor:
            self.setTextCursor(cursor_for_pos)
            self.add_cursor(old_cursor)

        self.multi_cursor_ignore_history = False
        self.cursorPositionChanged.emit()

    def add_cursor_up(self):
        if self.multi_cursor_enabled:
            self.extra_cursors.append(self.textCursor())
            self.moveCursor(QTextCursor.MoveOperation.Up)
            self.merge_extra_cursors(True)

    def add_cursor_down(self):
        if self.multi_cursor_enabled:
            self.extra_cursors.append(self.textCursor())
            self.moveCursor(QTextCursor.MoveOperation.Down)
            self.merge_extra_cursors(True)

    def set_extra_cursor_selections(self):
        selections = []
        for cursor in self.extra_cursors:
            extra_selection = TextDecoration(
                cursor, draw_order=5, kind="extra_cursor_selection"
            )

            extra_selection.set_foreground(
                QColor(SpyderPalette.COLOR_TEXT_1)
            )
            extra_selection.set_background(
                QColor(SpyderPalette.COLOR_ACCENT_2)
            )

            selections.append(extra_selection)
        self.set_extra_selections('extra_cursor_selections', selections)

    def clear_extra_cursors(self):
        """Remove all extra cursors"""
        self.extra_cursors = []
        self.set_extra_selections('extra_cursor_selections', [])

    @property
    def all_cursors(self):
        """Return list of all extra_cursors (if any) plus the primary cursor"""
        return self.extra_cursors + [self.textCursor()]

    def merge_extra_cursors(self, increasing_position):
        """Merge overlapping cursors"""
        if not self.extra_cursors:
            return

        previous_history = self.multi_cursor_ignore_history
        self.multi_cursor_ignore_history = True

        while True:
            cursor_was_removed = False

            cursors = self.all_cursors
            main_cursor = cursors[-1]
            cursors.sort(key=lambda cursor: cursor.position())

            for i, cursor1 in enumerate(cursors[:-1]):
                if cursor_was_removed:
                    break  # list will be modified, so re-start at while loop

                for cursor2 in cursors[i + 1:]:
                    # given cursors.sort, pos1 should be <= pos2
                    pos1 = cursor1.position()
                    pos2 = cursor2.position()
                    anchor1 = cursor1.anchor()
                    anchor2 = cursor2.anchor()

                    if not pos1 == pos2:
                        continue  # only merge coincident cursors

                    if cursor1 is main_cursor:
                        # swap cursors to keep main_cursor
                        cursor1, cursor2 = cursor2, cursor1

                    self.extra_cursors.remove(cursor1)
                    cursor_was_removed = True

                    # reposition cursor we're keeping
                    positions = sorted([pos1, anchor1, anchor2])
                    if not increasing_position:
                        positions.reverse()
                    cursor2.setPosition(
                        positions[0],
                        QTextCursor.MoveMode.MoveAnchor
                    )
                    cursor2.setPosition(
                        positions[2],
                        QTextCursor.MoveMode.KeepAnchor
                    )
                    if cursor2 is main_cursor:
                        self.setTextCursor(cursor2)
                    break

            if not cursor_was_removed:
                break

        self.set_extra_cursor_selections()
        self.multi_cursor_ignore_history = previous_history

    @Slot(QKeyEvent)
    def handle_multi_cursor_keypress(self, event: QKeyEvent):
        """Re-Implement keyEvent handler for multi-cursor"""

        key = event.key()
        ctrl = event.modifiers() & Qt.KeyboardModifier.ControlModifier
        alt = event.modifiers() & Qt.KeyboardModifier.AltModifier
        shift = event.modifiers() & Qt.KeyboardModifier.ShiftModifier

        # ---- Handle insert
        if key == Qt.Key.Key_Insert and not (ctrl or alt or shift):
            self.overwrite_mode = not self.overwrite_mode
            return

        self.textCursor().beginEditBlock()
        self.multi_cursor_ignore_history = True

        # Handle all signals before editing text
        cursors = []
        accepted = []
        for cursor in self.all_cursors:
            self.setTextCursor(cursor)
            event.ignore()
            self.sig_key_pressed.emit(event)
            cursors.append(self.textCursor())
            accepted.append(event.isAccepted())

        increasing_position = True
        new_cursors = []
        for skip, cursor in zip(accepted, cursors):
            self.setTextCursor(cursor)
            if skip:
                # Text folding swallows most input to prevent typing on folded
                # lines.
                pass
            # ---- Handle Tab
            elif key == Qt.Key.Key_Tab and not ctrl:  # ctrl-tab is shortcut
                # Don't do intelligent tab with multi-cursor to skip
                # calls to do_completion. Avoiding completions with multi
                # cursor is much easier than solving all the edge cases.
                self.indent(force=self.tab_mode)
            elif key == Qt.Key.Key_Backtab and not ctrl:
                increasing_position = False
                # TODO: Ignore indent level of neighboring lines and simply
                # indent by 1 level at a time. Cursor update order can
                # make this unpredictable otherwise.
                self.unindent(force=self.tab_mode)
            # ---- Handle enter/return
            elif key in (Qt.Key_Enter, Qt.Key_Return):
                if not shift and not ctrl:
                    if (
                        self.add_colons_enabled and
                        self.is_python_like() and
                        self.autoinsert_colons()
                    ):
                        self.insert_text(':' + self.get_line_separator())
                        if self.strip_trailing_spaces_on_modify:
                            self.fix_and_strip_indent()
                        else:
                            self.fix_indent()
                    else:
                        cur_indent = self.get_block_indentation(
                            self.textCursor().blockNumber())
                        self._handle_keypress_event(event)

                        # Check if we're in a comment or a string at the
                        # current position
                        cmt_or_str_cursor = self.in_comment_or_string()

                        # Check if the line start with a comment or string
                        cursor = self.textCursor()
                        cursor.setPosition(
                            cursor.block().position(),
                            QTextCursor.KeepAnchor
                        )
                        cmt_or_str_line_begin = self.in_comment_or_string(
                            cursor=cursor
                        )

                        # Check if we are in a comment or a string
                        cmt_or_str = (
                            cmt_or_str_cursor and cmt_or_str_line_begin
                        )

                        if self.strip_trailing_spaces_on_modify:
                            self.fix_and_strip_indent(
                                comment_or_string=cmt_or_str,
                                cur_indent=cur_indent
                            )
                        else:
                            self.fix_indent(
                                comment_or_string=cmt_or_str,
                                cur_indent=cur_indent
                            )
            # ---- Intelligent backspace handling
            elif key == Qt.Key_Backspace and not shift and not ctrl:
                increasing_position = False
                if self.has_selected_text() or not self.intelligent_backspace:
                    self._handle_keypress_event(event)
                else:
                    leading_text = self.get_text('sol', 'cursor')
                    leading_length = len(leading_text)
                    trailing_spaces = (
                        leading_length - len(leading_text.rstrip())
                    )
                    trailing_text = self.get_text('cursor', 'eol')
                    matches = ('()', '[]', '{}', '\'\'', '""')
                    if (
                        not leading_text.strip() and
                        (leading_length > len(self.indent_chars))
                    ):
                        if leading_length % len(self.indent_chars) == 0:
                            self.unindent()
                        else:
                            self._handle_keypress_event(event)
                    elif trailing_spaces and not trailing_text.strip():
                        self.remove_suffix(leading_text[-trailing_spaces:])
                    elif (
                        leading_text and
                        trailing_text and
                        (leading_text[-1] + trailing_text[0] in matches)
                    ):
                        cursor = self.textCursor()
                        cursor.movePosition(QTextCursor.PreviousCharacter)
                        cursor.movePosition(
                            QTextCursor.NextCharacter,
                            QTextCursor.KeepAnchor, 2
                        )
                        cursor.removeSelectedText()
                    else:
                        self._handle_keypress_event(event)
            # ---- Handle home, end
            elif key == Qt.Key.Key_Home:
                increasing_position = False
                self.stdkey_home(shift, ctrl)
            elif key == Qt.Key.Key_End:
                # See spyder-ide/spyder#495: on MacOS X, it is necessary to
                # redefine this basic action which should have been implemented
                # natively
                self.stdkey_end(shift, ctrl)
            # ---- Use default handler for cursor (text)
            else:
                if key in (Qt.Key.Key_Up, Qt.Key.Key_Left):
                    increasing_position = False
                if (
                    key in (Qt.Key.Key_Up, Qt.Key.Key_Down)
                    and cursor.verticalMovementX() == -1
                ):
                    # Builtin handler somehow does not set verticalMovementX
                    # when moving up and down (but works fine for single
                    # cursor somehow)
                    # TODO: Why? Are we forgetting something?
                    x = self.cursorRect(cursor).x()
                    cursor.setVerticalMovementX(x)
                    self.setTextCursor(cursor)
                self._handle_keypress_event(event)

            # Update edited extra_cursors
            new_cursors.append(self.textCursor())

        self.extra_cursors = new_cursors[:-1]
        self.merge_extra_cursors(increasing_position)
        self.textCursor().endEditBlock()
        self.multi_cursor_ignore_history = False
        self.cursorPositionChanged.emit()
        event.accept()  # TODO when to pass along keypress or not

    def _on_cursor_blinktimer_timeout(self):
        """
        Text cursor blink timer generates paint events and inverts draw state
        """
        self.cursor_blink_state = not self.cursor_blink_state
        if self.isVisible():
            self.viewport().update()

    @Slot(QPaintEvent)
    def paint_cursors(self, event):
        """Paint all cursors"""
        if self.overwrite_mode:
            font = self.font()
            cursor_width = QFontMetrics(font).horizontalAdvance(" ")
        else:
            cursor_width = self.cursor_width

        qp = QPainter()
        qp.begin(self.viewport())
        offset = self.contentOffset()
        content_offset_y = offset.y()
        qp.setBrushOrigin(offset)
        editable = not self.isReadOnly()
        flags = (
            self.textInteractionFlags()
            & Qt.TextInteractionFlag.TextSelectableByKeyboard
        )

        if self._drag_cursor is not None and (editable or flags):
            cursor = self._drag_cursor
            block = cursor.block()
            if block.isVisible():
                block_top = int(self.blockBoundingGeometry(block).top())
                offset.setY(block_top + content_offset_y)
                layout = block.layout()
                if layout is not None:  # Fix exceptions in test_flag_painting
                    layout.drawCursor(
                        qp,
                        offset,
                        cursor.positionInBlock(),
                        cursor_width
                    )

        draw_cursor = self.cursor_blink_state and (editable or flags)

        for cursor in self.all_cursors:
            block = cursor.block()
            if draw_cursor and block.isVisible():
                block_top = int(self.blockBoundingGeometry(block).top())
                offset.setY(block_top + content_offset_y)
                layout = block.layout()
                if layout is not None:
                    layout.drawCursor(
                        qp,
                        offset,
                        cursor.positionInBlock(),
                        cursor_width
                    )
        qp.end()

    @Slot()
    def start_cursor_blink(self):
        """Start manually updating the cursor(s) blink state: Show cursors."""
        self.cursor_blink_state = True
        self.cursor_blink_timer.start()

    @Slot()
    def stop_cursor_blink(self):
        """Stop manually updating the cursor(s) blink state: Hide cursors."""
        self.cursor_blink_state = False
        self.cursor_blink_timer.stop()

    def multi_cursor_copy(self):
        """
        Join all cursor selections in position sorted order by line_separator,
        and put text to clipboard.
        """
        cursors = self.all_cursors
        cursors.sort(key=lambda cursor: cursor.position())
        selections = []
        for cursor in cursors:
            text = cursor.selectedText().replace(
                "\u2029",
                self.get_line_separator()
            )
            selections.append(text)
        clip_text = self.get_line_separator().join(selections)
        QApplication.clipboard().setText(clip_text)

    def multi_cursor_cut(self):
        """Multi-cursor copy then removeSelectedText"""
        self.multi_cursor_copy()
        self.textCursor().beginEditBlock()
        for cursor in self.all_cursors:
            cursor.removeSelectedText()

        # Merge direction doesn't matter here as all selections are removed
        self.merge_extra_cursors(True)
        self.textCursor().endEditBlock()

    def multi_cursor_paste(self, clip_text):
        """
        Split clipboard by lines, and paste one line per cursor in position
        sorted order.
        """
        main_cursor = self.textCursor()
        main_cursor.beginEditBlock()
        cursors = self.all_cursors
        cursors.sort(key=lambda cursor: cursor.position())
        self.skip_rstrip = True
        self.sig_will_paste_text.emit(clip_text)
        lines = clip_text.splitlines()

        if len(lines) == 1:
            lines = itertools.repeat(lines[0])

        self.multi_cursor_ignore_history = True
        for cursor, text in zip(cursors, lines):
            self.setTextCursor(cursor)
            cursor.insertText(text)
            # handle extra lines or extra cursors?

        self.setTextCursor(main_cursor)
        self.multi_cursor_ignore_history = False
        self.cursorPositionChanged.emit()

        # Merge direction doesn't matter here as all selections are removed
        self.merge_extra_cursors(True)
        main_cursor.endEditBlock()
        self.sig_text_was_inserted.emit()
        self.skip_rstrip = False

    def for_each_cursor(self, method, merge_increasing=True):
        """Wrap callable to execute once for each cursor"""
        @functools.wraps(method)
        def wrapper():
            self.textCursor().beginEditBlock()
            new_cursors = []
            self.multi_cursor_ignore_history = True
            for cursor in self.all_cursors:
                self.setTextCursor(cursor)

                # May call setTtextCursor with modified copy
                method()

                # Get modified cursor to re-add to extra_cursors
                new_cursors.append(self.textCursor())

            # re-add extra cursors
            self.clear_extra_cursors()
            for cursor in new_cursors[:-1]:
                self.add_cursor(cursor)
            self.setTextCursor(new_cursors[-1])
            self.merge_extra_cursors(merge_increasing)
            self.textCursor().endEditBlock()
            self.multi_cursor_ignore_history = False
            self.cursorPositionChanged.emit()

        return wrapper

    def clears_extra_cursors(self, method):
        """Wrap callable to clear extra_cursors prior to calling"""
        @functools.wraps(method)
        def wrapper():
            self.clear_extra_cursors()
            method()

        return wrapper

    def restrict_single_cursor(self, method):
        """Wrap callable to only execute if there is a single cursor"""
        @functools.wraps(method)
        def wrapper():
            if not self.extra_cursors:
                method()

        return wrapper

    def go_to_next_cell(self):
        """
        Reimplement TextEditBaseWidget.go_to_next_cell to clear extra cursors.
        """
        self.clear_extra_cursors()
        super().go_to_next_cell()

    def go_to_previous_cell(self):
        """
        Reimplement TextEditBaseWidget.go_to_previous_cell to clear extra
        cursors.
        """
        self.clear_extra_cursors()
        super().go_to_previous_cell()
