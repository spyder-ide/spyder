# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)
"""This module contains the snippets editor extension."""

from qtpy.QtCore import Qt
from qtpy.QtGui import QTextCursor

from spyder.widgets.sourcecode.api.decoration import TextDecoration
from spyder.api.editorextension import EditorExtension
from spyder.utils.snippets import SnippetManager
from spyder.config.base import debug_print
from spyder.utils.editor import drift_color


class SnippetsExtension(EditorExtension):
    """Editor Extension for insert snippets."""

    def __init__(self):
        """Init editor extension, and the snippets manager"""
        super(SnippetsExtension, self).__init__()
        self.snippet_manager = SnippetManager()

        self._selection_decos = []
        self.snippet = None  # Snippet in progress

    def _get_color(self):
        """Return color for decorate variables."""
        color = self.editor.sideareas_color
        if color.lightness() < 128:
            return drift_color(color, 130)
        else:
            return drift_color(color, 105)

    def on_state_changed(self, state):
        """Connect/disconnect key_pressed signal."""
        if state:
            self.editor.key_pressed.connect(self._on_key_pressed)
        else:
            self.editor.key_pressed.disconnect(self._on_key_pressed)

    def _on_key_pressed(self, event):
        if event.isAccepted():
            return

        key = event.key()
        if key == Qt.Key_Tab and self.enabled:
            if self.snippet is not None:
                self._select_next_variable()
                event.accept()
            else:
                if self._insert_snippet():
                    event.accept()

    def _insert_snippet(self):
        """Search and insert snippet.

        Return True if the snipped was inserted, else False.
        """
        cursor = self.editor.textCursor()
        cursor.movePosition(QTextCursor.StartOfWord)
        position = cursor.position()
        cursor.movePosition(QTextCursor.EndOfWord, QTextCursor.KeepAnchor)
        prefix = cursor.selectedText()

        self.snippet = self.snippet_manager.search_snippet(prefix)

        if self.snippet is not None:
            cursor.removeSelectedText()
            cursor.insertText(self.snippet.text())
            debug_print("Inserted snippet:{} {}".format(prefix,
                        self.snippet.content))
            self._decorate_variables(position)
            return True
        else:
            return False

    def _decorate_selection(self, cursor):
        """Add decoration to region selected by the cursor."""
        d = TextDecoration(cursor)
        d.set_outline(self._get_color())
        self.editor.decorations.append(d)
        self._selection_decos.append(d)

    def _decorate_variables(self, position):
        """Decorate snippet variables."""
        if self.snippet is None:
            return
        cursor = self.editor.textCursor()
        variables = self.snippet.variables_position

        if not variables:
            self.snippet = None
            return

        # Decorate variables
        for start, length in variables:
            cursor.setPosition(position)
            cursor.movePosition(QTextCursor.Right, n=start)
            cursor.movePosition(QTextCursor.Right, QTextCursor.KeepAnchor,
                                length)
            self._decorate_selection(cursor)

        # select first variable
        self._select_next_variable()

    def _select_next_variable(self):
        """Select default value of the next variable."""
        cursor = self.editor.textCursor()
        try:
            d = self._selection_decos.pop(0)
        except IndexError:
            self.snippet = None
            cursor.clearSelection()
        else:
            cursor = d.cursor
        self.editor.setTextCursor(cursor)
