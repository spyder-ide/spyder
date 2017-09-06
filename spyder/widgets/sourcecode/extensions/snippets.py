# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)
"""This module contains the snippets editor extension."""

from qtpy.QtCore import Qt
from qtpy.QtGui import QTextCursor

from spyder.api.editorextension import EditorExtension
from spyder.utils.snippets import SnippetManager
from spyder.config.base import debug_print


class SnippetsExtension(EditorExtension):
    """Editor Extension for insert snippets."""

    def __init__(self):
        """Init editor extension, and the snippets manager"""
        super(SnippetsExtension, self).__init__()
        self.snippet_manager = SnippetManager()
        self.snippet = None  # Snippet in progress

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
                self._continue_snippet()
                event.accept()
            else:
                if self._insert_snippet():
                    event.accept()

    def _insert_snippet(self):
        """Search and insert snippet.

        Return True if the snipped was inserted, else False.
        """
        cursor = self.editor.textCursor()
        cursor.movePosition(QTextCursor.StartOfWord, QTextCursor.KeepAnchor)
        prefix = cursor.selectedText()

        self.snippet = self.snippet_manager.search_snippet(prefix)

        if self.snippet is not None:
            cursor.removeSelectedText()
            cursor.insertText(self.snippet.text())
            debug_print("Inserted snippet:{} {}".format(prefix,
                        self.snippet.content))
            self._select_variables()
            return True
        else:
            cursor.movePosition(QTextCursor.EndOfWord)
            return False

    def _select_variables(self):
        if self.snippet is None:
            return

        for variable in self.snippet.variables_position():
            pass
        else:
            self.snippet = None

    def _continue_snippet(self):
        self.snippet = None
