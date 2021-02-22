# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright (c) 2013-2016 Colin Duquesnoy and others (see pyqode/AUTHORS.rst)
# Copyright (c) 2016- Spyder Project Contributors (see AUTHORS.txt)
#
# Distributed under the terms of the MIT License
# (see NOTICE.txt in the Spyder root directory for details)
# -----------------------------------------------------------------------------

"""
This module contains utility functions/classes for Spyder's Editor.

Adapted from pyqode/core/api/utils.py of the
`PyQode project <https://github.com/pyQode/pyQode>`_.
Original file:
<https://github.com/pyQode/pyqode.core/blob/master/pyqode/core/api/utils.py>
"""

# Standard library imports
import weakref
import os.path as osp

# Third party imports
from qtpy.QtCore import QTimer, Qt
from qtpy.QtGui import (QColor, QTextBlockUserData, QTextCursor, QTextBlock,
                        QTextDocument)

# Local imports
from spyder.py3compat import to_text_string
from spyder.utils import encoding


def drift_color(base_color, factor=110):
    """
    Return color that is lighter or darker than the base color.

    If base_color.lightness is higher than 128, the returned color is darker
    otherwise is is lighter.

    :param base_color: The base color to drift from
    ;:param factor: drift factor (%)
    :return A lighter or darker color.
    """
    base_color = QColor(base_color)
    if base_color.lightness() > 128:
        return base_color.darker(factor)
    else:
        if base_color == QColor('#000000'):
            return drift_color(QColor('#101010'), factor + 20)
        else:
            return base_color.lighter(factor + 10)


class BlockUserData(QTextBlockUserData):
    def __init__(self, editor, color=None, selection_start=None,
                 selection_end=None):
        QTextBlockUserData.__init__(self)
        self.editor = editor
        self.breakpoint = False
        self.breakpoint_condition = None
        self.bookmarks = []
        self.code_analysis = []
        self.todo = ''
        self.color = color
        self.oedata = None
        self.import_statement = None
        self.selection_start = selection_start
        self.selection_end = selection_end

        # Add a reference to the user data in the editor as the block won't.
        # The list should /not/ be used to list BlockUserData as the blocks
        # they refer to might not exist anymore.
        # This prevent a segmentation fault.
        if editor is None:
            # Won't be destroyed
            self.refloop = self
            return
        # Destroy with the editor
        if not hasattr(editor, '_user_data_reference_list'):
            editor._user_data_reference_list = []
        editor._user_data_reference_list.append(self)

    def _selection(self):
        """
        Function to compute the selection.

        This is slow to call so it is only called when needed.
        """
        if self.selection_start is None or self.selection_end is None:
            return None
        document = self.editor.document()
        cursor = self.editor.textCursor()
        block = document.findBlockByNumber(self.selection_start['line'])
        cursor.setPosition(block.position())
        cursor.movePosition(QTextCursor.StartOfBlock)
        cursor.movePosition(
            QTextCursor.NextCharacter, n=self.selection_start['character'])
        block2 = document.findBlockByNumber(
            self.selection_end['line'])
        cursor.setPosition(block2.position(), QTextCursor.KeepAnchor)
        cursor.movePosition(
            QTextCursor.StartOfBlock, mode=QTextCursor.KeepAnchor)
        cursor.movePosition(
            QTextCursor.NextCharacter, n=self.selection_end['character'],
            mode=QTextCursor.KeepAnchor)
        return QTextCursor(cursor)


class DelayJobRunner(object):
    """
    Utility class for running job after a certain delay.
    If a new request is made during this delay, the previous request is dropped
    and the timer is restarted for the new request.

    We use this to implement a cooldown effect that prevents jobs from being
    executed while the IDE is not idle.

    A job is a simple callable.
    """
    def __init__(self, delay=500):
        """
        :param delay: Delay to wait before running the job. This delay applies
        to all requests and cannot be changed afterwards.
        """
        self._timer = QTimer()
        self.delay = delay
        self._timer.timeout.connect(self._exec_requested_job)
        self._args = []
        self._kwargs = {}
        self._job = lambda x: None

    def request_job(self, job, *args, **kwargs):
        """
        Request a job execution.

        The job will be executed after the delay specified in the
        DelayJobRunner contructor elapsed if no other job is requested until
        then.

        :param job: job.
        :type job: callable
        :param args: job's position arguments
        :param kwargs: job's keyworded arguments
        """
        self.cancel_requests()
        self._job = job
        self._args = args
        self._kwargs = kwargs
        self._timer.start(self.delay)

    def cancel_requests(self):
        """Cancels pending requests."""
        self._timer.stop()
        self._job = None
        self._args = None
        self._kwargs = None

    def _exec_requested_job(self):
        """Execute the requested job after the timer has timeout."""
        self._timer.stop()
        self._job(*self._args, **self._kwargs)


class TextHelper(object):
    """
    Text helper helps you manipulate the content of CodeEditor and extends the
    Qt text api for an easier usage.

    FIXME: Some of this methods are already implemented in CodeEditor, move
    and unify redundant methods.
    """
    @property
    def _editor(self):
        try:
            return self._editor_ref()
        except TypeError:
            return self._editor_ref

    def __init__(self, editor):
        """:param editor: The editor to work on."""
        try:
            self._editor_ref = weakref.ref(editor)
        except TypeError:
            self._editor_ref = editor

    def goto_line(self, line, column=0, end_column=0, move=True, word=''):
        """
        Moves the text cursor to the specified position.

        :param line: Number of the line to go to (0 based)
        :param column: Optional column number. Default is 0 (start of line).
        :param move: True to move the cursor. False will return the cursor
                     without setting it on the editor.
        :param word: Highlight the word, when moving to the line.
        :return: The new text cursor
        :rtype: QtGui.QTextCursor
        """
        line = min(line, self.line_count())
        text_cursor = self._move_cursor_to(line)
        if column:
            text_cursor.movePosition(text_cursor.Right, text_cursor.MoveAnchor,
                                     column)
        if end_column:
            text_cursor.movePosition(text_cursor.Right, text_cursor.KeepAnchor,
                                     end_column)
        if move:
            block = text_cursor.block()
            self.unfold_if_colapsed(text_cursor)
            self._editor.setTextCursor(text_cursor)

            if self._editor.isVisible():
                self._editor.centerCursor()
            else:
                self._editor.focus_in.connect(
                    self._editor.center_cursor_on_next_focus)
            if word and to_text_string(word) in to_text_string(block.text()):
                self._editor.find(word, QTextDocument.FindCaseSensitively)
        return text_cursor

    def unfold_if_colapsed(self, cursor):
        """Unfold parent fold trigger if the block is collapsed.

        :param block: Block to unfold.
        """
        block = cursor.block()
        try:
            folding_panel = self._editor.panels.get('FoldingPanel')
        except KeyError:
            pass
        else:
            if block.isVisible():
                return

            fold_start_line = block.blockNumber()

            # Find the innermost code folding region for the current position
            enclosing_regions = sorted(list(
                folding_panel.current_tree[fold_start_line]))

            folding_status = folding_panel.folding_status
            if len(enclosing_regions) > 0:
                for region in enclosing_regions:
                    fold_start_line = region.begin
                    block = self._editor.document().findBlockByNumber(
                        fold_start_line)
                    if fold_start_line in folding_status:
                        fold_status = folding_status[fold_start_line]
                        if fold_status:
                            folding_panel.toggle_fold_trigger(block)

            self._editor.setTextCursor(cursor)
            if self._editor.isVisible():
                self._editor.centerCursor()

    def selected_text(self):
        """Returns the selected text."""
        return self._editor.textCursor().selectedText()

    def word_under_cursor(self, select_whole_word=False, text_cursor=None):
        """
        Gets the word under cursor using the separators defined by
        :attr:`spyder.plugins.editor.widgets.codeeditor.CodeEditor.word_separators`.

        FIXME: This is not working because CodeEditor have no attribute
        word_separators

        .. note: Instead of returning the word string, this function returns
            a QTextCursor, that way you may get more information than just the
            string. To get the word, just call ``selectedText`` on the returned
            value.

        :param select_whole_word: If set to true the whole word is selected,
         else the selection stops at the cursor position.
        :param text_cursor: Optional custom text cursor (e.g. from a
            QTextDocument clone)
        :returns: The QTextCursor that contains the selected word.
        """
        editor = self._editor
        if not text_cursor:
            text_cursor = editor.textCursor()
        word_separators = editor.word_separators
        end_pos = start_pos = text_cursor.position()
        # select char by char until we are at the original cursor position.
        while not text_cursor.atStart():
            text_cursor.movePosition(
                text_cursor.Left, text_cursor.KeepAnchor, 1)
            try:
                char = text_cursor.selectedText()[0]
                word_separators = editor.word_separators
                selected_txt = text_cursor.selectedText()
                if (selected_txt in word_separators and
                        (selected_txt != "n" and selected_txt != "t") or
                        char.isspace()):
                    break  # start boundary found
            except IndexError:
                break  # nothing selectable
            start_pos = text_cursor.position()
            text_cursor.setPosition(start_pos)
        if select_whole_word:
            # select the resot of the word
            text_cursor.setPosition(end_pos)
            while not text_cursor.atEnd():
                text_cursor.movePosition(text_cursor.Right,
                                         text_cursor.KeepAnchor, 1)
                char = text_cursor.selectedText()[0]
                selected_txt = text_cursor.selectedText()
                if (selected_txt in word_separators and
                        (selected_txt != "n" and selected_txt != "t") or
                        char.isspace()):
                    break  # end boundary found
                end_pos = text_cursor.position()
                text_cursor.setPosition(end_pos)
        # now that we habe the boundaries, we can select the text
        text_cursor.setPosition(start_pos)
        text_cursor.setPosition(end_pos, text_cursor.KeepAnchor)
        return text_cursor

    def word_under_mouse_cursor(self):
        """
        Selects the word under the **mouse** cursor.

        :return: A QTextCursor with the word under mouse cursor selected.
        """
        editor = self._editor
        text_cursor = editor.cursorForPosition(editor._last_mouse_pos)
        text_cursor = self.word_under_cursor(True, text_cursor)
        return text_cursor

    def cursor_position(self):
        """
        Returns the QTextCursor position. The position is a tuple made up of
        the line number (0 based) and the column number (0 based).

        :return: tuple(line, column)
        """
        return (self._editor.textCursor().blockNumber(),
                self._editor.textCursor().columnNumber())

    def current_line_nbr(self):
        """
        Returns the text cursor's line number.

        :return: Line number
        """
        return self.cursor_position()[0]

    def current_column_nbr(self):
        """
        Returns the text cursor's column number.

        :return: Column number
        """
        return self.cursor_position()[1]

    def line_count(self):
        """
        Returns the line count of the specified editor.

        :return: number of lines in the document.
        """
        return self._editor.document().blockCount()

    def line_text(self, line_nbr):
        """
        Gets the text of the specified line.

        :param line_nbr: The line number of the text to get

        :return: Entire line's text
        :rtype: str
        """
        doc = self._editor.document()
        block = doc.findBlockByNumber(line_nbr)
        return block.text()

    def previous_line_text(self):
        """
        Gets the previous line text (relative to the current cursor pos).
        :return: previous line text (str)
        """
        if self.current_line_nbr():
            return self.line_text(self.current_line_nbr() - 1)
        return ''

    def current_line_text(self):
        """
        Returns the text of the current line.

        :return: Text of the current line
        """
        return self.line_text(self.current_line_nbr())

    def set_line_text(self, line_nbr, new_text):
        """
        Replace an entire line with ``new_text``.

        :param line_nbr: line number of the line to change.
        :param new_text: The replacement text.

        """
        editor = self._editor
        text_cursor = self._move_cursor_to(line_nbr)
        text_cursor.select(text_cursor.LineUnderCursor)
        text_cursor.insertText(new_text)
        editor.setTextCursor(text_cursor)

    def remove_last_line(self):
        """Removes the last line of the document."""
        editor = self._editor
        text_cursor = editor.textCursor()
        text_cursor.movePosition(text_cursor.End, text_cursor.MoveAnchor)
        text_cursor.select(text_cursor.LineUnderCursor)
        text_cursor.removeSelectedText()
        text_cursor.deletePreviousChar()
        editor.setTextCursor(text_cursor)

    def _move_cursor_to(self, line):
        cursor = self._editor.textCursor()
        block = self._editor.document().findBlockByNumber(line-1)
        cursor.setPosition(block.position())
        return cursor

    def select_lines(self, start=0, end=-1, apply_selection=True):
        """
        Selects entire lines between start and end line numbers.

        This functions apply the selection and returns the text cursor that
        contains the selection.

        Optionally it is possible to prevent the selection from being applied
        on the code editor widget by setting ``apply_selection`` to False.

        :param start: Start line number (0 based)
        :param end: End line number (0 based). Use -1 to select up to the
            end of the document
        :param apply_selection: True to apply the selection before returning
         the QTextCursor.
        :returns: A QTextCursor that holds the requested selection
        """
        editor = self._editor
        if end == -1:
            end = self.line_count() - 1
        if start < 0:
            start = 0
        text_cursor = self._move_cursor_to(start)
        if end > start:  # Going down
            text_cursor.movePosition(text_cursor.Down,
                                     text_cursor.KeepAnchor, end - start)
            text_cursor.movePosition(text_cursor.EndOfLine,
                                     text_cursor.KeepAnchor)
        elif end < start:  # going up
            # don't miss end of line !
            text_cursor.movePosition(text_cursor.EndOfLine,
                                     text_cursor.MoveAnchor)
            text_cursor.movePosition(text_cursor.Up,
                                     text_cursor.KeepAnchor, start - end)
            text_cursor.movePosition(text_cursor.StartOfLine,
                                     text_cursor.KeepAnchor)
        else:
            text_cursor.movePosition(text_cursor.EndOfLine,
                                     text_cursor.KeepAnchor)
        if apply_selection:
            editor.setTextCursor(text_cursor)
        return text_cursor

    def line_pos_from_number(self, line_number):
        """
        Computes line position on Y-Axis (at the center of the line) from line
        number.

        :param line_number: The line number for which we want to know the
                            position in pixels.
        :return: The center position of the line.
        """
        editor = self._editor
        block = editor.document().findBlockByNumber(line_number)
        if block.isValid():
            return int(editor.blockBoundingGeometry(block).translated(
                editor.contentOffset()).top())
        if line_number <= 0:
            return 0
        else:
            return int(editor.blockBoundingGeometry(
                block.previous()).translated(editor.contentOffset()).bottom())

    def line_nbr_from_position(self, y_pos):
        """
        Returns the line number from the y_pos.

        :param y_pos: Y pos in the editor
        :return: Line number (0 based), -1 if out of range
        """
        editor = self._editor
        height = editor.fontMetrics().height()
        for top, line, block in editor.visible_blocks:
            if top <= y_pos <= top + height:
                return line
        return -1

    def mark_whole_doc_dirty(self):
        """
        Marks the whole document as dirty to force a full refresh. **SLOW**
        """
        text_cursor = self._editor.textCursor()
        text_cursor.select(text_cursor.Document)
        self._editor.document().markContentsDirty(text_cursor.selectionStart(),
                                                  text_cursor.selectionEnd())

    def insert_text(self, text, keep_position=True):
        """
        Inserts text at the cursor position.

        :param text: text to insert
        :param keep_position: Flag that specifies if the cursor position must
            be kept. Pass False for a regular insert (the cursor will be at
            the end of the inserted text).
        """
        text_cursor = self._editor.textCursor()
        if keep_position:
            s = text_cursor.selectionStart()
            e = text_cursor.selectionEnd()
        text_cursor.insertText(text)
        if keep_position:
            text_cursor.setPosition(s)
            text_cursor.setPosition(e, text_cursor.KeepAnchor)
        self._editor.setTextCursor(text_cursor)
        self._editor.document_did_change()

    def search_text(self, text_cursor, search_txt, search_flags):
        """
        Searches a text in a text document.

        :param text_cursor: Current text cursor
        :param search_txt: Text to search
        :param search_flags: QTextDocument.FindFlags
        :returns: the list of occurrences, the current occurrence index
        :rtype: tuple([], int)

        """
        def compare_cursors(cursor_a, cursor_b):
            """
            Compares two QTextCursor.

            :param cursor_a: cursor a
            :param cursor_b: cursor b

            :returns; True if both cursor are identical (same position, same
                selection)
            """
            return (cursor_b.selectionStart() >= cursor_a.selectionStart() and
                    cursor_b.selectionEnd() <= cursor_a.selectionEnd())

        text_document = self._editor.document()
        occurrences = []
        index = -1
        cursor = text_document.find(search_txt, 0, search_flags)
        original_cursor = text_cursor
        while not cursor.isNull():
            if compare_cursors(cursor, original_cursor):
                index = len(occurrences)
            occurrences.append((cursor.selectionStart(),
                                cursor.selectionEnd()))
            cursor.setPosition(cursor.position() + 1)
            cursor = text_document.find(search_txt, cursor, search_flags)
        return occurrences, index

    def is_comment_or_string(self, cursor_or_block, formats=None):
        """
        Checks if a block/cursor is a string or a comment.
        :param cursor_or_block: QTextCursor or QTextBlock
        :param formats: the list of color scheme formats to consider. By
            default, it will consider the following keys: 'comment', 'string',
            'docstring'.
        """
        if formats is None:
            formats = ["comment", "string", "docstring"]
        layout = None
        pos = 0
        if isinstance(cursor_or_block, QTextBlock):
            pos = len(cursor_or_block.text()) - 1
            layout = cursor_or_block.layout()
        elif isinstance(cursor_or_block, QTextCursor):
            b = cursor_or_block.block()
            pos = cursor_or_block.position() - b.position()
            layout = b.layout()
        if layout is not None:
            additional_formats = layout.additionalFormats()
            sh = self._editor.syntax_highlighter
            if sh:
                ref_formats = sh.color_scheme.formats
                for r in additional_formats:
                    if r.start <= pos < (r.start + r.length):
                        for fmt_type in formats:
                            is_user_obj = (r.format.objectType() ==
                                           r.format.UserObject)
                            if (ref_formats[fmt_type] == r.format and
                                    is_user_obj):
                                return True
        return False


class TextBlockHelper(object):
    """
    Helps retrieving the various part of the user state bitmask.

    This helper should be used to replace calls to
    ``QTextBlock.setUserState``/``QTextBlock.getUserState`` as well as
    ``QSyntaxHighlighter.setCurrentBlockState``/
    ``QSyntaxHighlighter.currentBlockState`` and
    ``QSyntaxHighlighter.previousBlockState``.

    The bitmask is made up of the following fields:

        - bit0 -> bit26: User state (for syntax highlighting)
        - bit26: fold trigger state
        - bit27-bit29: fold level (8 level max)
        - bit30: fold trigger flag

        - bit0 -> bit15: 16 bits for syntax highlighter user state (
          for syntax highlighting)
        - bit16-bit25: 10 bits for the fold level (1024 levels)
        - bit26: 1 bit for the fold trigger flag (trigger or not trigger)
        - bit27: 1 bit for the fold trigger state (expanded/collapsed)

    """
    @staticmethod
    def get_state(block):
        """
        Gets the user state, generally used for syntax highlighting.
        :param block: block to access
        :return: The block state

        """
        if block is None:
            return -1
        state = block.userState()
        if state == -1:
            return state
        return state & 0x0000FFFF

    @staticmethod
    def set_state(block, state):
        """
        Sets the user state, generally used for syntax highlighting.

        :param block: block to modify
        :param state: new state value.
        :return:
        """
        if block is None:
            return
        user_state = block.userState()
        if user_state == -1:
            user_state = 0
        higher_part = user_state & 0x7FFF0000
        state &= 0x0000FFFF
        state |= higher_part
        block.setUserState(state)

    @staticmethod
    def get_fold_lvl(block):
        """
        Gets the block fold level.

        :param block: block to access.
        :returns: The block fold level
        """
        if block is None:
            return 0
        state = block.userState()
        if state == -1:
            state = 0
        return (state & 0x03FF0000) >> 16

    @staticmethod
    def set_fold_lvl(block, val):
        """
        Sets the block fold level.

        :param block: block to modify
        :param val: The new fold level [0-7]
        """
        if block is None:
            return
        state = block.userState()
        if state == -1:
            state = 0
        if val >= 0x3FF:
            val = 0x3FF
        state &= 0x7C00FFFF
        state |= val << 16
        block.setUserState(state)

    @staticmethod
    def is_fold_trigger(block):
        """
        Checks if the block is a fold trigger.

        :param block: block to check
        :return: True if the block is a fold trigger (represented as a node in
            the fold panel)
        """
        if block is None:
            return False
        state = block.userState()
        if state == -1:
            state = 0
        return bool(state & 0x04000000)

    @staticmethod
    def set_fold_trigger(block, val):
        """
        Set the block fold trigger flag (True means the block is a fold
        trigger).

        :param block: block to set
        :param val: value to set
        """
        if block is None:
            return
        state = block.userState()
        if state == -1:
            state = 0
        state &= 0x7BFFFFFF
        state |= int(val) << 26
        block.setUserState(state)

    @staticmethod
    def set_collapsed(block, val):
        """
        Sets the fold trigger state (collapsed or expanded).

        :param block: The block to modify
        :param val: The new trigger state (True=collapsed, False=expanded)
        """
        if block is None:
            return
        state = block.userState()
        if state == -1:
            state = 0
        state &= 0x77FFFFFF
        state |= int(val) << 27
        block.setUserState(state)


def get_file_language(filename, text=None):
    """Get file language from filename"""
    ext = osp.splitext(filename)[1]
    if ext.startswith('.'):
        ext = ext[1:]  # file extension with leading dot
    language = ext
    if not ext:
        if text is None:
            text, _enc = encoding.read(filename)
        for line in text.splitlines():
            if not line.strip():
                continue
            if line.startswith('#!'):
                shebang = line[2:]
                if 'python' in shebang:
                    language = 'python'
            else:
                break
    return language
