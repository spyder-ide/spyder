# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)
"""This module contains the close quotes editor extension."""

from qtpy.QtGui import QTextCursor
from spyder.api.editorextension import EditorExtension


class CloseBracketsExtension(EditorExtension):
    """Editor Extension for insert brackets automatically."""
    BRACKETS_CHAR = ["(", ")", "{", "}", "[", "]"]
    BRACKETS_LEFT = BRACKETS_CHAR[::2]
    BRACKETS_RIGHT = BRACKETS_CHAR[1::2]
    BRACKETS_PAIR = {"(": "()", ")": "()",
                     "{": "{}", "}": "{}",
                     "[": "[]", "]": "[]"}

    def on_state_changed(self, state):
        """Connect/disconnect sig_key_pressed signal."""
        if state:
            self.editor.sig_key_pressed.connect(self._on_key_pressed)
        else:
            self.editor.sig_key_pressed.disconnect(self._on_key_pressed)

    def _on_key_pressed(self, event):
        if event.isAccepted():
            return

        # It is necessary to use here the text of the event and not the key
        # to avoid issues with international keyboards.
        # See spyder-ide/spyder#9749
        char = event.text()
        if char in self.BRACKETS_CHAR and self.enabled:
            self.editor.completion_widget.hide()
            self._autoinsert_brackets(char)
            self.editor.document_did_change()
            event.accept()

    def unmatched_brackets_in_line(self, text, closing_brackets_type=None,
                                   autoinsert=False):
        """
        Checks if there is an unmatched brackets in the 'text'.

        The brackets type can be general or specified by closing_brackets_type
        (')', ']' or '}')
        """
        if closing_brackets_type is None:
            opening_brackets = self.BRACKETS_LEFT
            closing_brackets = self.BRACKETS_RIGHT
        else:
            closing_brackets = [closing_brackets_type]
            opening_brackets = [{')': '(', '}': '{',
                                 ']': '['}[closing_brackets_type]]
        block = self.editor.textCursor().block()
        line_pos = block.position()
        for pos, char in enumerate(text):
            if char in opening_brackets:
                match = self.editor.find_brace_match(line_pos+pos, char,
                                                     forward=True)
                if (match is None) or (match > line_pos+len(text)):
                    return True
            if char in closing_brackets:
                match = self.editor.find_brace_match(line_pos+pos, char,
                                                     forward=False)
                # Only validate match existence for autoinsert.
                # Having the missing bracket in a previous line is possible.
                # See spyder-ide/spyder#11217
                if (match is None) or (match < line_pos and not autoinsert):
                    return True
        return False

    def _autoinsert_brackets(self, char):
        """Control automatic insertation of brackets in various situations."""
        pair = self.BRACKETS_PAIR[char]

        line_text = self.editor.get_text('sol', 'eol')
        line_to_cursor = self.editor.get_text('sol', 'cursor')
        cursor = self.editor.textCursor()
        trailing_text = self.editor.get_text('cursor', 'eol').strip()

        if self.editor.has_selected_text():
            text = self.editor.get_selected_text()
            self.editor.insert_text("{0}{1}{2}".format(pair[0], text, pair[1]))
            # Keep text selected, for inserting multiple brackets
            cursor.movePosition(QTextCursor.Left, QTextCursor.MoveAnchor, 1)
            cursor.movePosition(QTextCursor.Left, QTextCursor.KeepAnchor,
                                len(text))
            self.editor.setTextCursor(cursor)
        elif char in self.BRACKETS_LEFT:
            if (not trailing_text or
                    trailing_text[0] in self.BRACKETS_RIGHT or
                    trailing_text[0] in [',', ':', ';']):
                # Automatic insertion of brackets
                self.editor.insert_text(pair)
                cursor.movePosition(QTextCursor.PreviousCharacter)
                self.editor.setTextCursor(cursor)
            else:
                self.editor.insert_text(char)
            if char in self.editor.signature_completion_characters:
                self.editor.request_signature()
        elif char in self.BRACKETS_RIGHT:
            if (self.editor.next_char() == char and
                    not self.editor.textCursor().atBlockEnd() and
                    not self.unmatched_brackets_in_line(
                        cursor.block().text(), char, autoinsert=True)):
                # Overwrite an existing brackets if all in line are matched
                cursor.movePosition(QTextCursor.NextCharacter,
                                    QTextCursor.KeepAnchor, 1)
                cursor.clearSelection()
                self.editor.setTextCursor(cursor)
            else:
                self.editor.insert_text(char)
