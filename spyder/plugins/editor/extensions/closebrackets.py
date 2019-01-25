# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)
"""This module contains the close quotes editor extension."""

from qtpy.QtCore import Qt
from qtpy.QtGui import QTextCursor

from spyder.api.editorextension import EditorExtension


class CloseBracketsExtension(EditorExtension):
    """Editor Extension for insert brackets automatically."""

    BRACKETS_PAIR = {Qt.Key_ParenLeft: "()", Qt.Key_ParenRight: "()",
                     Qt.Key_BraceLeft: "{}", Qt.Key_BraceRight: "{}",
                     Qt.Key_BracketLeft: "[]", Qt.Key_BracketRight: "[]"}
    BRACKETS_LEFT = {Qt.Key_ParenLeft: "(",
                     Qt.Key_BraceLeft: "{",
                     Qt.Key_BracketLeft: "["}
    BRACKETS_RIGHT = {Qt.Key_ParenRight: ")",
                      Qt.Key_BraceRight: "}",
                      Qt.Key_BracketRight: "]"}
    BRACKETS_CHAR = BRACKETS_LEFT.copy()
    BRACKETS_CHAR.update(BRACKETS_RIGHT)

    def on_state_changed(self, state):
        """Connect/disconnect sig_key_pressed signal."""
        if state:
            self.editor.sig_key_pressed.connect(self._on_key_pressed)
        else:
            self.editor.sig_key_pressed.disconnect(self._on_key_pressed)

    def _on_key_pressed(self, event):
        if event.isAccepted():
            return

        key = event.key()
        if key in self.BRACKETS_CHAR and self.enabled:
            self._autoinsert_brackets(key)
            event.accept()

    def unmatched_brackets_in_line(self, text, closing_braces_type=None):
        """
        Checks if there is an unmatched brackets in the 'text'.
        The brackets type can be general or specified by closing_braces_type
        (')', ']', '}' or '>')
        """
        if closing_braces_type is None:
            opening_braces = self.BRACKETS_LEFT.values()
            closing_braces = self.BRACKETS_RIGHT.values()
        else:
            closing_braces = [closing_braces_type]
            opening_braces = [{')': '(', '}': '{',
                               ']': '['}[closing_braces_type]]
        block = self.editor.textCursor().block()
        line_pos = block.position()
        for pos, char in enumerate(text):
            if char in opening_braces:
                match = self.editor.find_brace_match(line_pos+pos, char,
                                                     forward=True)
                if (match is None) or (match > line_pos+len(text)):
                    return True
            if char in closing_braces:
                match = self.editor.find_brace_match(line_pos+pos, char,
                                                     forward=False)
                if (match is None) or (match < line_pos):
                    return True
        return False

    def _autoinsert_brackets(self, key):
        """Control automatic insertation of brackets in various situations."""
        char = self.BRACKETS_CHAR[key]
        pair = self.BRACKETS_PAIR[key]

        line_text = self.editor.get_text('sol', 'eol')
        line_to_cursor = self.editor.get_text('sol', 'cursor')
        cursor = self.editor.textCursor()
        trailing_text = self.editor.get_text('cursor', 'eol').strip()

        if self.editor.has_selected_text():
            text = self.editor.get_selected_text()
            self.editor.insert_text("{0}{1}{2}".format(pair[0], text, pair[1]))
            # Keep text selected, for inserting multiple quotes
            cursor.movePosition(QTextCursor.Left, QTextCursor.MoveAnchor, 1)
            cursor.movePosition(QTextCursor.Left, QTextCursor.KeepAnchor,
                                len(text))
            self.editor.setTextCursor(cursor)
        elif key in self.BRACKETS_LEFT:
            if (not trailing_text or
                    trailing_text[0] in BRACKETS_RIGHT.items() + [',']):
                # Automatic insertion of quotes
                self.editor.insert_text(pair)
                cursor.movePosition(QTextCursor.PreviousCharacter)
                self.editor.setTextCursor(cursor)
            else:
                self.editor.insert_text(char)
            if char in self.editor.signature_completion_characters:
                self.editor.request_signature()
        elif key in self.BRACKETS_RIGHT:
            if (self.editor.next_char() == char and
                not self.editor.textCursor().atBlockEnd() and
                not self.unmatched_brackets_in_line(
                        cursor.block().text(), char)):
                # Overwrite an existing brackets if all in line are matched
                cursor.movePosition(QTextCursor.NextCharacter,
                                    QTextCursor.KeepAnchor, 1)
                cursor.clearSelection()
                self.editor.setTextCursor(cursor)
            else:
                self.editor.insert_text(char)
