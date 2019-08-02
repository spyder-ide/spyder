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
from qtpy.QtGui import QTextCursor, QColor
from qtpy.QtCore import Qt, Slot

try:
    from rtree import index
    rtree_available = True
except ImportError:
    rtree_available = False

# Local imports
from spyder.py3compat import to_text_string
from spyder.api.editorextension import EditorExtension
import spyder.plugins.editor.extensions.snippets.utils.nodes as nodes
from spyder.plugins.editor.extensions.snippets.utils.ast import (
    build_snippet_ast)


class SnippetSearcherVisitor:
    def __init__(self, line, column, node_number=0):
        self.line = line
        self.column = column
        self.line_offset = 0
        self.column_offset = 0
        self.node_number = node_number
        self.snippet_map = {}
        self.position_map = {}

    def visit(self, node):
        if isinstance(node, nodes.TabstopSnippetNode):
            snippet_number = node.number
            number_snippets = self.snippet_map.get(snippet_number, [])
            number_snippets.append(node)
            self.snippet_map[snippet_number] = number_snippets
        if node.mark_for_position:
            self.position_map[self.node_number] = (node.position, node)
            self.node_number += 1


class SnippetsExtension(EditorExtension):
    """CodeEditor extension on charge of autocompletion and snippet display."""

    def __init__(self):
        EditorExtension.__init__(self)
        self.is_snippet_active = False
        self.active_snippet = -1
        self.node_number = 0
        self.index = None
        self.ast = None
        self.node_position = {}
        self.snippets_map = {}
        if rtree_available:
            self.index = index.Index()

    def on_state_changed(self, state):
        """Connect/disconnect sig_key_pressed signal."""
        if state:
            self.editor.sig_key_pressed.connect(self._on_key_pressed)
            self.editor.sig_insert_completion.connect(self.insert_snippet)
            self.editor.sig_cursor_position_changed.connect(
                self.cursor_changed)
        else:
            self.editor.sig_key_pressed.disconnect(self._on_key_pressed)
            self.editor.sig_insert_completion.disconnect(self.insert_snippet)
            self.editor.sig_cursor_position_changed.disconnect(
                self.cursor_changed)

    def _on_key_pressed(self, event):
        if event.isAccepted():
            return

        if self.editor.completion_widget.isVisible():
            return

        key = event.key()
        cursor = self.editor.textCursor()
        if self.is_snippet_active:
            if key == Qt.Key_Tab:
                next_snippet = ((self.active_snippet + 1) %
                                len(self.snippets_map))
                self.select_snippet(next_snippet)
                event.accept()
            elif key == Qt.Key_Escape:
                self.reset()
                event.accept()

    def update_position_tree(self, visitor):
        self.node_number = visitor.node_number
        self.node_position.update(visitor.position_map)
        for node_position in visitor.position_map:
            position, _ = visitor.position_map[node_position]
            if isinstance(position, list):
                for segment in position:
                    segment = tuple(coor for pos in segment for coor in pos)
                    self.index.insert(node_position, segment)
            elif isinstance(position, tuple):
                if len(position) == 1:
                    position = position * 2
                position = tuple(coor for pos in position for coor in pos)
                self.index.insert(node_position, position)

    def cursor_changed(self, line, col):
        point = (line, col) * 2
        node_numbers = list(self.index.intersection(point))
        if len(node_numbers) == 0:
            self.reset()
        else:
            print(node_numbers)

    def reset(self):
        self.node_number = 0
        self.index = None
        self.is_snippet_active = False
        self.active_snippet = -1
        self.node_position = {}
        if rtree_available:
            self.index = index.Index()
        self.editor.clear_extra_selections('code_snippets')

    def draw_snippets(self):
        document = self.editor.document()
        for snippet_number in self.snippets_map:
            snippet_nodes = self.snippets_map[snippet_number]
            for node in snippet_nodes:
                cursor = QTextCursor(self.editor.textCursor())
                position = node.position
                if isinstance(node.position, tuple):
                    position = [list(node.position)]
                for path in position:
                    start_line, start_column = path[0]
                    end_line, end_column = path[-1]
                    if path[0] == path[-1]:
                        end_column += 1
                    start_block = document.findBlockByNumber(start_line)
                    cursor.setPosition(start_block.position())
                    cursor.movePosition(QTextCursor.StartOfBlock)
                    cursor.movePosition(
                        QTextCursor.NextCharacter, n=start_column)
                    end_block = document.findBlockByNumber(end_line)
                    cursor.setPosition(
                        end_block.position(), QTextCursor.KeepAnchor)
                    cursor.movePosition(
                        QTextCursor.StartOfBlock, mode=QTextCursor.KeepAnchor)
                    cursor.movePosition(
                        QTextCursor.NextCharacter, n=end_column,
                        mode=QTextCursor.KeepAnchor)
                    # color = QColor(color)
                    # color.setAlpha(255)
                    color = QColor(self.editor.comment_color)
                    # color.setAlpha(64)
                    self.editor.highlight_selection('code_snippets',
                                                    QTextCursor(cursor),
                                                    outline_color=color)
                    self.editor.update_extra_selections()

    def select_snippet(self, snippet_number):
        cursor = self.editor.textCursor()
        document = self.editor.document()
        if snippet_number not in self.snippets_map:
            snippet_number = 0
        node = self.snippets_map[snippet_number][0]
        self.active_snippet = snippet_number
        node_position = node.position
        if isinstance(node_position, tuple):
            node_position = [list(node_position)]
        start_line, start_column = node_position[0][0]
        end_line, end_column = node_position[-1][-1]
        if node_position[0][0] == node_position[-1][-1]:
            if node.text() != '':
                end_column += 1
        start_block = document.findBlockByNumber(start_line)
        # cursor.beginEditBlock()
        cursor.setPosition(start_block.position())
        cursor.movePosition(QTextCursor.StartOfBlock)
        cursor.movePosition(
            QTextCursor.NextCharacter, n=start_column)
        end_block = document.findBlockByNumber(end_line)
        cursor.setPosition(
            end_block.position(), QTextCursor.KeepAnchor)
        cursor.movePosition(
            QTextCursor.StartOfBlock, mode=QTextCursor.KeepAnchor)
        cursor.movePosition(
            QTextCursor.NextCharacter, n=end_column,
            mode=QTextCursor.KeepAnchor)
        # cursor.endEditBlock()
        self.editor.setTextCursor(cursor)
        self.editor.request_signature()

    def insert_snippet(self, text):
        line, column = self.editor.get_cursor_line_column()
        visitor = SnippetSearcherVisitor(line, column, self.node_number)
        ast = build_snippet_ast(text)
        ast.compute_position((line, column))
        ast.accept(visitor)
        self.ast = ast
        self.editor.insert_text(ast.text())
        self.editor.document_did_change()
        # TODO Handle nested snippets
        self.snippets_map = visitor.snippet_map
        if len(self.snippets_map) > 0:
            # Completion contains snippets
            self.is_snippet_active = True
            self.update_position_tree(visitor)
            self.draw_snippets()
            self.select_snippet(snippet_number=1)
        else:
            # Completion does not contain snippets
            self.reset()
