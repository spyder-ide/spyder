# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)
"""This module contains the close quotes editor extension."""

from qtpy.QtCore import Qt
from qtpy.QtGui import QTextCursor

from spyder.api.editorextension import EditorExtension


def unmatched_quotes_in_line(text):
    """Return whether a string has open quotes.

    This simply counts whether the number of quote characters of either
    type in the string is odd.

    Take from the IPython project (in IPython/core/completer.py in v0.13)
    Spyder team: Add some changes to deal with escaped quotes

    - Copyright (C) 2008-2011 IPython Development Team
    - Copyright (C) 2001-2007 Fernando Perez. <fperez@colorado.edu>
    - Copyright (C) 2001 Python Software Foundation, www.python.org

    Distributed under the terms of the BSD License.
    """
    # We check " first, then ', so complex cases with nested quotes will
    # get the " to take precedence.
    text = text.replace("\\'", "")
    text = text.replace('\\"', '')
    if text.count('"') % 2:
        return '"'
    elif text.count("'") % 2:
        return "'"
    else:
        return ''


class CloseQuotesExtension(EditorExtension):
    """Editor Extension for insert closing quotes automatically."""

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
        if key in (Qt.Key_QuoteDbl, Qt.Key_Apostrophe) and self.enabled:
            self.editor.completion_widget.hide()
            self._autoinsert_quotes(key)
            self.editor.document_did_change()
            event.accept()

    def _autoinsert_quotes(self, key):
        """Control how to automatically insert quotes in various situations."""
        char = {Qt.Key_QuoteDbl: '"', Qt.Key_Apostrophe: '\''}[key]

        line_text = self.editor.get_text('sol', 'eol')
        line_to_cursor = self.editor.get_text('sol', 'cursor')
        cursor = self.editor.textCursor()
        last_three = self.editor.get_text('sol', 'cursor')[-3:]
        last_two = self.editor.get_text('sol', 'cursor')[-2:]
        trailing_text = self.editor.get_text('cursor', 'eol').strip()

        if self.editor.has_selected_text():
            text = self.editor.get_selected_text()
            self.editor.insert_text("{0}{1}{0}".format(char, text))
            # keep text selected, for inserting multiple quotes
            cursor.movePosition(QTextCursor.Left, QTextCursor.MoveAnchor, 1)
            cursor.movePosition(QTextCursor.Left, QTextCursor.KeepAnchor,
                                len(text))
            self.editor.setTextCursor(cursor)
        elif self.editor.in_comment():
            self.editor.insert_text(char)
        elif (len(trailing_text) > 0 and
                not unmatched_quotes_in_line(line_to_cursor) == char and
                not trailing_text[0] in (',', ':', ';', ')', ']', '}')):
            self.editor.insert_text(char)
        elif (unmatched_quotes_in_line(line_text) and
                (not last_three == 3*char)):
            self.editor.insert_text(char)
        # Move to the right if we are before a quote
        elif self.editor.next_char() == char:
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
            self.editor.delayed_popup_docstring()
        # Automatic insertion of quotes
        else:
            self.editor.insert_text(2*char)
            cursor = self.editor.textCursor()
            cursor.movePosition(QTextCursor.PreviousCharacter)
            self.editor.setTextCursor(cursor)
