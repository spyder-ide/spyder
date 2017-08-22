# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)
"""
This module contains the quote select editor extension
"""

from qtpy.QtCore import Qt
from qtpy.QtGui import QTextCursor

from spyder.api.editorextension import EditorExtension


class QuoteEditorExtension(EditorExtension):
    """"""

    def on_state_changed(self, state):
        """"""
        if state:
            self.editor.key_pressed.connect(self._on_key_pressed)
        else:
            self.editor.key_pressed.disconnect(self._on_key_pressed)

    def _on_key_pressed(self, event):
        if event.isAccepted():
            return

        key = event.key()
        if key in (Qt.Key_QuoteDbl, Qt.Key_Apostrophe) and self.enabled:
            self.autoinsert_quotes(key)
            event.accept()

    def autoinsert_quotes(self, key):
        """Control how to automatically insert quotes in various situations"""
        char = {Qt.Key_QuoteDbl: '"', Qt.Key_Apostrophe: '\''}[key]

        line_text = self.editor.get_text('sol', 'eol')
        line_to_cursor = self.editor.get_text('sol', 'cursor')
        cursor = self.editor.textCursor()
        last_three = self.editor.get_text('sol', 'cursor')[-3:]
        last_two = self.editor.get_text('sol', 'cursor')[-2:]
        trailing_text = self.editor.get_text('cursor', 'eol').strip()

        if self.editor.has_selected_text():
            text = ''.join([char, self.editor.get_selected_text(), char])
            self.editor.insert_text(text)
        elif self.editor.__in_comment():
            self.editor.insert_text(char)
        elif len(trailing_text) > 0 and not \
                self.editor.__unmatched_quotes_in_line(line_to_cursor) == char:
            self.editor.insert_text(char)
        elif self.editor.__unmatched_quotes_in_line(line_text) and \
                (not last_three == 3*char):
            self.editor.insert_text(char)
        # Move to the right if we are before a quote
        elif self.editor.__next_char() == char:
            cursor.movePosition(QTextCursor.NextCharacter,
                                QTextCursor.KeepAnchor, 1)
            cursor.clearSelection()
            self.editor.setTextCursor(cursor)
        # Automatic insertion of triple double quotes (for docstrings)
        elif last_three == 3*char:
            self.editor.insert_text(3*char)
            cursor = self.editor.textCursor()
            cursor.movePosition(QTextCursor.PreviousCharacter,
                                QTextCursor.KeepAnchor, 3)
            cursor.clearSelection()
            self.editor.setTextCursor(cursor)
        # If last two chars are quotes, just insert one more because most
        # probably the user wants to write a docstring
        elif last_two == 2*char:
            self.editor.insert_text(char)
        # Automatic insertion of quotes
        else:
            self.editor.insert_text(2*char)
            cursor = self.editor.textCursor()
            cursor.movePosition(QTextCursor.PreviousCharacter)
            self.editor.setTextCursor(cursor)
