# -*- coding: utf-8 -*-
"""
This module contains utility functions/classes.
"""
import functools
import logging
import weakref

from pyqode.qt import QtCore, QtGui, QtWidgets


def _logger():
    """ Returns module logger """
    return logging.getLogger(__name__)


class memoized(object):
    """
    Decorator. Caches a function's return value each time it is called.
    If called later with the same arguments, the cached value is returned
    (not reevaluated).
    """
    def __init__(self, func):
        self.func = func
        self.cache = {}

    def __call__(self, *args):
        try:
            if args in self.cache:
                return self.cache[args]
            else:
                value = self.func(*args)
                self.cache[args] = value
                return value
        except TypeError:
            return self.func(*args)

    def __repr__(self):
        """ Return the function's docstring."""
        return self.func.__doc__

    def __get__(self, obj, objtype):
        """ Support instance methods. """
        return functools.partial(self.__call__, obj)


def drift_color(base_color, factor=110):
    """
    Return color that is lighter or darker than the base color.

    If base_color.lightness is higher than 128, the returned color is darker
    otherwise is is lighter.

    :param base_color: The base color to drift from
    ;:param factor: drift factor (%)
    :return A lighter or darker color.
    """
    base_color = QtGui.QColor(base_color)
    if base_color.lightness() > 128:
        return base_color.darker(factor)
    else:
        if base_color == QtGui.QColor('#000000'):
            return drift_color(QtGui.QColor('#101010'), factor + 20)
        else:
            return base_color.lighter(factor + 10)


class DelayJobRunner(object):
    """
    Utility class for running job after a certain delay. If a new request is
    made during this delay, the previous request is dropped and the timer is
    restarted for the new request.

    We use this to implement a cooldown effect that prevents jobs from being
    executed while the IDE is not idle.

    A job is a simple callable.
    """
    def __init__(self, delay=500):
        """
        :param delay: Delay to wait before running the job. This delay applies
        to all requests and cannot be changed afterwards.
        """
        self._timer = QtCore.QTimer()
        self.delay = delay
        self._timer.timeout.connect(self._exec_requested_job)
        self._args = []
        self._kwargs = {}
        self._job = lambda x: None

    def request_job(self, job, *args, **kwargs):
        """
        Request a job execution. The job will be executed after the delay
        specified in the DelayJobRunner contructor elapsed if no other job is
        requested until then.

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
        """
        Cancels pending requests.
        """
        self._timer.stop()
        self._job = None
        self._args = None
        self._kwargs = None

    def _exec_requested_job(self):
        """
        Execute the requested job after the timer has timeout.
        """
        self._timer.stop()
        self._job(*self._args, **self._kwargs)


class TextHelper(object):
    """
    Text helper helps you manipulate the content of CodeEdit and extends the
    Qt text api for an easier usage.

    """
    @property
    def _editor(self):
        try:
            return self._editor_ref()
        except TypeError:
            return self._editor_ref

    def __init__(self, editor):
        """
        :param editor: The editor to work on.
        """
        try:
            self._editor_ref = weakref.ref(editor)
        except TypeError:
            self._editor_ref = editor

    def goto_line(self, line, column=0, move=True):
        """
        Moves the text cursor to the specified position..

        :param line: Number of the line to go to (0 based)
        :param column: Optional column number. Default is 0 (start of line).
        :param move: True to move the cursor. False will return the cursor
                     without setting it on the editor.
        :return: The new text cursor
        :rtype: QtGui.QTextCursor
        """
        text_cursor = self._move_cursor_to(line)
        if column:
            text_cursor.movePosition(text_cursor.Right, text_cursor.MoveAnchor,
                                     column)
        if move:
            block = text_cursor.block()
            # unfold parent fold trigger if the block is collapsed
            try:
                folding_panel = self._editor.panels.get('FoldingPanel')
            except KeyError:
                pass
            else:
                from pyqode.core.api.folding import FoldScope
                if not block.isVisible():
                    block = FoldScope.find_parent_scope(block)
                    if TextBlockHelper.is_collapsed(block):
                        folding_panel.toggle_fold_trigger(block)
            self._editor.setTextCursor(text_cursor)
        return text_cursor

    def selected_text(self):
        """
        Returns the selected text.
        """
        return self._editor.textCursor().selectedText()

    def word_under_cursor(self, select_whole_word=False, text_cursor=None):
        """
        Gets the word under cursor using the separators defined by
        :attr:`pyqode.core.api.CodeEdit.word_separators`.

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
        Returns the line count of the specified editor

        :return: number of lines in the document.
        """
        return self._editor.document().blockCount()

    def line_text(self, line_nbr):
        """
        Gets the text of the specified line

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
        """
        Removes the last line of the document.
        """
        editor = self._editor
        text_cursor = editor.textCursor()
        text_cursor.movePosition(text_cursor.End, text_cursor.MoveAnchor)
        text_cursor.select(text_cursor.LineUnderCursor)
        text_cursor.removeSelectedText()
        text_cursor.deletePreviousChar()
        editor.setTextCursor(text_cursor)

    def clean_document(self):
        """
        Removes trailing whitespaces and ensure one single blank line at the
        end of the QTextDocument.

        ..deprecated: since pyqode 2.6.3, document is cleaned on disk only.
        """
        editor = self._editor
        value = editor.verticalScrollBar().value()
        pos = self.cursor_position()
        editor.textCursor().beginEditBlock()

        # cleanup whitespaces
        editor._cleaning = True
        eaten = 0
        removed = set()
        for line in editor._modified_lines:
            # parse line before and line after modified line (for cases where
            # key_delete or key_return has been pressed)
            for j in range(-1, 2):
                # skip current line
                if line + j != pos[0]:
                    if line + j >= 0:
                        txt = self.line_text(line + j)
                        stxt = txt.rstrip()
                        if txt != stxt:
                            self.set_line_text(line + j, stxt)
                        removed.add(line + j)
        editor._modified_lines -= removed

        # ensure there is only one blank line left at the end of the file
        i = self.line_count()
        while i:
            line = self.line_text(i - 1)
            if line.strip():
                break
            self.remove_last_line()
            i -= 1
        if self.line_text(self.line_count() - 1):
            editor.appendPlainText('')

        # restore cursor and scrollbars
        text_cursor = editor.textCursor()
        doc = editor.document()
        assert isinstance(doc, QtGui.QTextDocument)
        text_cursor = self._move_cursor_to(pos[0])
        text_cursor.movePosition(text_cursor.StartOfLine,
                                 text_cursor.MoveAnchor)
        cpos = text_cursor.position()
        text_cursor.select(text_cursor.LineUnderCursor)
        if text_cursor.selectedText():
            text_cursor.setPosition(cpos)
            offset = pos[1] - eaten
            text_cursor.movePosition(text_cursor.Right, text_cursor.MoveAnchor,
                                     offset)
        else:
            text_cursor.setPosition(cpos)
        editor.setTextCursor(text_cursor)
        editor.verticalScrollBar().setValue(value)

        text_cursor.endEditBlock()
        editor._cleaning = False

    def select_whole_line(self, line=None, apply_selection=True):
        """
        Selects an entire line.

        :param line: Line to select. If None, the current line will be selected
        :param apply_selection: True to apply selection on the text editor
            widget, False to just return the text cursor without setting it
            on the editor.
        :return: QTextCursor
        """
        if line is None:
            line = self.current_line_nbr()
        return self.select_lines(line, line, apply_selection=apply_selection)

    def _move_cursor_to(self, line):
        cursor = self._editor.textCursor()
        block = self._editor.document().findBlockByNumber(line)
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

    def selection_range(self):
        """
        Returns the selected lines boundaries (start line, end line)

        :return: tuple(int, int)
        """
        editor = self._editor
        doc = editor.document()
        start = doc.findBlock(
            editor.textCursor().selectionStart()).blockNumber()
        end = doc.findBlock(
            editor.textCursor().selectionEnd()).blockNumber()
        text_cursor = QtGui.QTextCursor(editor.textCursor())
        text_cursor.setPosition(editor.textCursor().selectionEnd())
        if text_cursor.columnNumber() == 0 and start != end:
            end -= 1
        return start, end

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
        Returns the line number from the y_pos

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

    def line_indent(self, line_nbr=None):
        """
        Returns the indent level of the specified line

        :param line_nbr: Number of the line to get indentation (1 base).
            Pass None to use the current line number. Note that you can also
            pass a QTextBlock instance instead of an int.
        :return: Number of spaces that makes the indentation level of the
                 current line
        """
        if line_nbr is None:
            line_nbr = self.current_line_nbr()
        elif isinstance(line_nbr, QtGui.QTextBlock):
            line_nbr = line_nbr.blockNumber()
        line = self.line_text(line_nbr)
        indentation = len(line) - len(line.lstrip())
        return indentation

    def get_right_word(self, cursor=None):
        """
        Gets the character on the right of the text cursor.

        :param cursor: QTextCursor where the search will start.

        :return: The word that is on the right of the text cursor.
        """
        if cursor is None:
            cursor = self._editor.textCursor()
        cursor.movePosition(QtGui.QTextCursor.WordRight,
                            QtGui.QTextCursor.KeepAnchor)
        return cursor.selectedText().strip()

    def get_right_character(self, cursor=None):
        """
        Gets the character that is on the right of the text cursor.

        :param cursor: QTextCursor that defines the position where the search
            will start.
        """
        next_char = self.get_right_word(cursor=cursor)
        if len(next_char):
            next_char = next_char[0]
        else:
            next_char = None
        return next_char

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

    def clear_selection(self):
        """
        Clears text cursor selection

        """
        text_cursor = self._editor.textCursor()
        text_cursor.clearSelection()
        self._editor.setTextCursor(text_cursor)

    def move_right(self, keep_anchor=False, nb_chars=1):
        """
        Moves the cursor on the right.

        :param keep_anchor: True to keep anchor (to select text) or False to
            move the anchor (no selection)
        :param nb_chars: Number of characters to move.
        """
        text_cursor = self._editor.textCursor()
        text_cursor.movePosition(
            text_cursor.Right, text_cursor.KeepAnchor if keep_anchor else
            text_cursor.MoveAnchor, nb_chars)
        self._editor.setTextCursor(text_cursor)

    def selected_text_to_lower(self):
        """ Replaces the selected text by its lower version """
        txt = self.selected_text()
        self.insert_text(txt.lower())

    def selected_text_to_upper(self):
        """
        Replaces the selected text by its upper version

        """
        txt = self.selected_text()
        self.insert_text(txt.upper())

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
            Compares two QTextCursor

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
        if isinstance(cursor_or_block, QtGui.QTextBlock):
            pos = len(cursor_or_block.text()) - 1
            layout = cursor_or_block.layout()
        elif isinstance(cursor_or_block, QtGui.QTextCursor):
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

    def select_extended_word(self, continuation_chars=('.',)):
        """
        Performs extended word selection. Extended selection consists in
        selecting the word under cursor and any other words that are linked
        by a ``continuation_chars``.

        :param continuation_chars: the list of characters that may extend a
            word.
        """
        cursor = self._editor.textCursor()
        original_pos = cursor.position()
        start_pos = None
        end_pos = None
        # go left
        stop = False
        seps = self._editor.word_separators + [' ']
        while not stop:
            cursor.clearSelection()
            cursor.movePosition(cursor.Left, cursor.KeepAnchor)
            char = cursor.selectedText()
            if cursor.atBlockStart():
                stop = True
                start_pos = cursor.position()
            elif char in seps and char not in continuation_chars:
                stop = True
                start_pos = cursor.position() + 1
        # go right
        cursor.setPosition(original_pos)
        stop = False
        while not stop:
            cursor.clearSelection()
            cursor.movePosition(cursor.Right, cursor.KeepAnchor)
            char = cursor.selectedText()
            if cursor.atBlockEnd():
                stop = True
                end_pos = cursor.position()
                if char in seps:
                    end_pos -= 1
            elif char in seps and char not in continuation_chars:
                stop = True
                end_pos = cursor.position() - 1
        if start_pos and end_pos:
            cursor.setPosition(start_pos)
            cursor.movePosition(cursor.Right, cursor.KeepAnchor,
                                end_pos - start_pos)
            self._editor.setTextCursor(cursor)

    def match_select(self, ignored_symbols=None):
        """
        Performs matched selection, selects text between matching quotes or
        parentheses.

        :param ignored_symbols; matching symbols to ignore.
        """
        def filter_matching(ignored_symbols, matching):
            """
            Removes any ignored symbol from the match dict.
            """
            if ignored_symbols is not None:
                for symbol in matching.keys():
                    if symbol in ignored_symbols:
                        matching.pop(symbol)
            return matching

        def find_opening_symbol(cursor, matching):
            """
            Find the position ot the opening symbol
            :param cursor: Current text cursor
            :param matching: symbol matches map
            """
            start_pos = None
            opening_char = None
            closed = {k: 0 for k in matching.values()
                      if k not in ['"', "'"]}
            # go left
            stop = False
            while not stop and not cursor.atStart():
                cursor.clearSelection()
                cursor.movePosition(cursor.Left, cursor.KeepAnchor)
                char = cursor.selectedText()
                if char in closed.keys():
                    closed[char] += 1
                elif char in matching.keys():
                    opposite = matching[char]
                    if opposite in closed.keys() and closed[opposite]:
                        closed[opposite] -= 1
                        continue
                    else:
                        # found opening quote or parenthesis
                        start_pos = cursor.position() + 1
                        stop = True
                        opening_char = char
            return opening_char, start_pos

        def find_closing_symbol(cursor, matching, opening_char, original_pos):
            """
            Finds the position of the closing symbol

            :param cursor: current text cursor
            :param matching: symbold matching dict
            :param opening_char: the opening character
            :param original_pos: position of the opening character.
            """
            end_pos = None
            cursor.setPosition(original_pos)
            rev_matching = {v: k for k, v in matching.items()}
            opened = {k: 0 for k in rev_matching.values()
                      if k not in ['"', "'"]}
            stop = False
            while not stop and not cursor.atEnd():
                cursor.clearSelection()
                cursor.movePosition(cursor.Right, cursor.KeepAnchor)
                char = cursor.selectedText()
                if char in opened.keys():
                    opened[char] += 1
                elif char in rev_matching.keys():
                    opposite = rev_matching[char]
                    if opposite in opened.keys() and opened[opposite]:
                        opened[opposite] -= 1
                        continue
                    elif matching[opening_char] == char:
                        # found opening quote or parenthesis
                        end_pos = cursor.position() - 1
                        stop = True
            return end_pos

        matching = {'(': ')', '{': '}', '[': ']', '"': '"', "'": "'"}
        filter_matching(ignored_symbols, matching)
        cursor = self._editor.textCursor()
        original_pos = cursor.position()
        end_pos = None
        opening_char, start_pos = find_opening_symbol(cursor, matching)
        if opening_char:
            end_pos = find_closing_symbol(
                cursor, matching, opening_char, original_pos)
        if start_pos and end_pos:
            cursor.setPosition(start_pos)
            cursor.movePosition(cursor.Right, cursor.KeepAnchor,
                                end_pos - start_pos)
            self._editor.setTextCursor(cursor)
            return True
        else:
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
        Gets the block fold level

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
    def is_collapsed(block):
        """
        Checks if the block is expanded or collased.

        :param block: QTextBlock
        :return: False for an open trigger, True for for closed trigger
        """
        if block is None:
            return False
        state = block.userState()
        if state == -1:
            state = 0
        return bool(state & 0x08000000)

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


class ParenthesisInfo(object):
    """
    Stores information about a parenthesis in a line of code.
    """
    def __init__(self, pos, char):
        #: Position of the parenthesis, expressed as a number of character
        self.position = pos
        #: The parenthesis character, one of "(", ")", "{", "}", "[", "]"
        self.character = char


def get_block_symbol_data(editor, block):
    """
    Gets the list of ParenthesisInfo for specific text block.

    :param editor: Code edit instance
    :param block: block to parse
    """
    def list_symbols(editor, block, character):
        """
        Retuns  a list of symbols found in the block text

        :param editor: code edit instance
        :param block: block to parse
        :param character: character to look for.
        """
        text = block.text()
        symbols = []
        cursor = QtGui.QTextCursor(block)
        cursor.movePosition(cursor.StartOfBlock)
        pos = text.find(character, 0)
        cursor.movePosition(cursor.Right, cursor.MoveAnchor, pos)

        while pos != -1:
            if not TextHelper(editor).is_comment_or_string(cursor):
                # skips symbols in string literal or comment
                info = ParenthesisInfo(pos, character)
                symbols.append(info)
            pos = text.find(character, pos + 1)
            cursor.movePosition(cursor.StartOfBlock)
            cursor.movePosition(cursor.Right, cursor.MoveAnchor, pos)
        return symbols

    parentheses = sorted(
        list_symbols(editor, block, '(') + list_symbols(editor, block, ')'),
        key=lambda x: x.position)
    square_brackets = sorted(
        list_symbols(editor, block, '[') + list_symbols(editor, block, ']'),
        key=lambda x: x.position)
    braces = sorted(
        list_symbols(editor, block, '{') + list_symbols(editor, block, '}'),
        key=lambda x: x.position)
    return parentheses, square_brackets, braces


def keep_tc_pos(func):
    """
    Cache text cursor position and restore it when the wrapped
    function exits.

    This decorator can only be used on modes or panels.

    :param func: wrapped function
    """
    @functools.wraps(func)
    def wrapper(editor, *args, **kwds):
        """ Decorator """
        sb = editor.verticalScrollBar()
        spos = sb.sliderPosition()
        pos = editor.textCursor().position()
        retval = func(editor, *args, **kwds)
        text_cursor = editor.textCursor()
        text_cursor.setPosition(pos)
        editor.setTextCursor(text_cursor)
        sb.setSliderPosition(spos)
        return retval
    return wrapper


def with_wait_cursor(func):
    """
    Show a wait cursor while the wrapped function is running. The cursor is
    restored as soon as the function exits.

    :param func: wrapped function
    """
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        QtWidgets.QApplication.setOverrideCursor(
            QtGui.QCursor(QtCore.Qt.WaitCursor))
        try:
            ret_val = func(*args, **kwargs)
        finally:
            QtWidgets.QApplication.restoreOverrideCursor()
        return ret_val
    return wrapper
