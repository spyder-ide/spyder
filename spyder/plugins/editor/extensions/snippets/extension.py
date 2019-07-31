# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""Code snippets editor extension."""

# Standard library imports
import re
from collections import OrderedDict

# Third party imports
from qtpy.QtGui import QTextCursor
from qtpy.QtCore import Qt

# Local imports
from spyder.py3compat import to_text_string
from spyder.api.editorextension import EditorExtension
import spyder.plugins.editor.extensions.snippets.utils.nodes as nodes
from spyder.plugins.editor.extensions.snippets.utils.ast import (
    build_snippet_ast)


class SnippetSearcherVisitor:
    def __init__(self, line, column):
        self.line = line
        self.column = column
        self.line_offset = 0
        self.column_offset = 0
        self.node_number = 0
        self.snippet_map = {}
        self.position_map = {}

    def visit(self, node):
        if isinstance(node, nodes.TabstopSnippetNode):
            node.update_position((self.line, self.column))
            snippet_number = node.number
            number_snippets = self.snippet_map.get(snippet_number, [])
            number_snippets.append(node)
            self.snippet_map[snippet_number] = number_snippets
        self.position_map[self.node_number] = (node.position, node)
        self.node_number += 1


class SnippetsExtension(EditorExtension):
    """CodeEditor extension on charge of autocompletion and snippet display."""

    def __init__(self):
        EditorExtension.__init__(self)
        self.is_snippet_active = False
        self.snippet_start = -1
        self.snippet_end = -1
        self.current_idx = -1
        self.snippet_components = []

    def on_state_changed(self, state):
        """Connect/disconnect sig_key_pressed signal."""
        if state:
            self.editor.sig_key_pressed.connect(self._on_key_pressed)
            self.editor.sig_insert_completion.connect(self.insert_snippet)
        else:
            self.editor.sig_key_pressed.disconnect(self._on_key_pressed)
            self.editor.sig_insert_completion.disconnect(self.insert_snippet)
            self.editor.sig_insert_completion.connect(self.insert_snippet)

    def _on_key_pressed(self, event):
        if event.isAccepted():
            return

        if self.editor.completion_widget.isVisible():
            return

        key = event.key()
        cursor = self.editor.textCursor()
        if self.is_snippet_active:
            if key == Qt.Key_Tab:
                self.current_idx = ((self.current_idx + 1) %
                                    len(self.snippet_components))
                current_snippet = self.snippet_components[self.current_idx]
                component_start = current_snippet['start']
                cursor.movePosition(QTextCursor.StartOfBlock)
                cursor.movePosition(
                    QTextCursor.NextCharacter, n=component_start)

    def insert_snippet(self, text):
        cursor = self.editor.textCursor()
        line, column = self.editor.get_cursor_line_column()
        visitor = SnippetSearcherVisitor(line, column)
        ast = build_snippet_ast(text)
        ast.compute_position((line, column))
        ast.accept(visitor)
        print(visitor.position_map)
        if len(visitor.snippet_map) > 0:
            # Completion contains snippets
            pass
        self.editor.insert_text(ast.text())
        self.editor.document_did_change()
