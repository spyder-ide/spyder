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
from spyder.plugins.editor.extensions.snippets.utils.lexer import tokenize


MERGE_ALLOWED = {'int', 'name', 'whitespace'}


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
        self.starting_position = None
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

        # if self.editor.completion_widget.isVisible():
        #     if not self.editor.completion_widget.is_empty():
        #         return

        key = event.key()
        text = to_text_string(event.text())

        cursor = self.editor.textCursor()
        if self.is_snippet_active:
            line, column = self.editor.get_cursor_line_column()
            node, snippet, text_node = self._find_node_by_position(
                line, column)
            if key == Qt.Key_Tab:
                event.accept()
                next_snippet = ((self.active_snippet + 1) %
                                len(self.snippets_map))
                self.select_snippet(next_snippet)
            elif key == Qt.Key_Escape:
                self.reset()
                event.accept()
            elif len(text) > 0:
                print('-----------------------------------------------')
                print(text)
                print('-----------------------------------------------')
                if node is not None:
                    if snippet is None:
                        # Constant text identifier was modified

                        self.reset()
                    else:
                        # Update placeholder text node
                        if text != '\b':
                            self.insert_text(text, line, column)
                            # text_node = nodes.TextNode(*token_nodes)
                            # snippet.placeholder = text_node
                        self._update_ast()

    def insert_text(self, text, line, column):
        node, snippet, text_node = self._find_node_by_position(line, column)
        leaf_kind = node.name
        tokens = tokenize(text)
        token_nodes = [nodes.LeafNode(t.token, t.value) for t in tokens]
        for token in token_nodes:
            token.compute_position((line, column))
        first_token = token_nodes[0]
        first_position = first_token.position[0]
        if node.name == 'EPSILON':
            new_text_node = nodes.TextNode(*token_nodes)
            snippet.placeholder = new_text_node
            return
        position = node.position
        print(position)
        if len(position) == 1:
            x, y = position[0]
            position = ((x, y), (x, y + 1))
        leaf_start, leaf_end = position
        if first_token.mark_for_position:
            if leaf_kind in MERGE_ALLOWED:
                if first_token.name == leaf_kind:
                    if first_position == leaf_start:
                        node.value = (
                            first_token.value + node.value)
                    elif first_position == leaf_end:
                        node.value = (
                            node.value + first_token.value)
                    else:
                        position = (first_position[1] -
                                    leaf_start[1])
                        value = node.value
                        value = (value[:position] +
                                 first_token.value +
                                 value[position:])
                        node.value = value
                    token_nodes = token_nodes[1:]
        if len(token_nodes) > 0:
            text_tokens = text_node.tokens
            next_token = token_nodes[0]
            first_position = next_token.position[0]
            leaf_position = node.index_in_parent
            if first_position == leaf_start:
                # Prepend to parent TextNode
                lower_bound = max(leaf_position - 1, 0)
                first_half = text_tokens[:lower_bound]
                second_half = text_tokens[leaf_position:]
            elif first_position == leaf_end:
                # Append to parent TextNode
                first_half = text_tokens
                second_half = []
            else:
                # Split current leaf and add in-between
                position = (
                    first_position[1] - leaf_start[1])
                leaf_value = node.value
                first_split = leaf_value[:position]
                second_split = leaf_value[position:]
                first_split = nodes.LeafNode(
                    node.name, first_split)
                second_split = nodes.LeafNode(
                    node.name, second_split)
                first_half = text_tokens[
                    :leaf_position - 1]
                first_half += [first_split]
                second_half = text_tokens[
                    leaf_position + 1:]
                second_half = [second_split] + second_half
            first_half = list(first_half)
            second_half = list(second_half)
            text_tokens = (
                first_half + token_nodes + second_half)
            for i, token in enumerate(text_tokens):
                token.index_in_parent = i
            text_node.tokens = text_tokens

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

    def _find_node_by_position(self, line, col):
        point = (line, col) * 2
        node_numbers = list(self.index.intersection(point))
        current_node, nearest_text, nearest_snippet = None, None, None
        if len(node_numbers) > 0:
            # node = self.node_position[node_numbers[-1]][-1]
            for node_number in node_numbers:
                current_node = self.node_position[node_number][-1]
                if isinstance(current_node, nodes.SnippetASTNode):
                    nearest_snippet = current_node
                elif isinstance(current_node, nodes.TextNode):
                    nearest_text = current_node
                elif isinstance(current_node, nodes.LeafNode):
                    if current_node.name == 'EPSILON':
                        break
        if nearest_text is not None:
            node_id = id(current_node)
            text_ids = set([id(token) for token in nearest_text.tokens])
            if node_id not in text_ids:
                current_node = nearest_text.tokens[-1]
        return current_node, nearest_snippet, nearest_text

    def cursor_changed(self, line, col):
        node, nearest_snippet, _ = self._find_node_by_position(line, col)
        if node is None:
            # self.reset()
            pass
        else:
            if nearest_snippet is not None:
                self.active_snippet = nearest_snippet.number

    def reset(self, partial_reset=False):
        self.node_number = 0
        self.index = None
        self.node_position = {}
        self.snippets_map = {}
        if not partial_reset:
            self.ast = None
            self.is_snippet_active = False
            self.active_snippet = -1
            self.starting_position = None
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
            if snippet_number not in self.snippets_map:
                snippet_number = max(self.snippets_map.keys())
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

    def _update_ast(self):
        self.reset(partial_reset=True)
        self.is_snippet_active = True
        self.ast.compute_position(self.starting_position)
        start_line, start_column = self.starting_position
        visitor = SnippetSearcherVisitor(
            start_line, start_column, self.node_number)
        self.ast.accept(visitor)
        self.snippets_map = visitor.snippet_map
        self.update_position_tree(visitor)
        self.editor.clear_extra_selections('code_snippets')
        self.draw_snippets()

    def insert_snippet(self, text):
        print('////////////////////////////////////////////')
        print(text)
        print('////////////////////////////////////////////')

        line, column = self.editor.get_cursor_line_column()
        visitor = SnippetSearcherVisitor(line, column, self.node_number)
        ast = build_snippet_ast(text)
        ast.compute_position((line, column))
        ast.accept(visitor)

        self.editor.insert_text(ast.text())
        self.editor.document_did_change()

        new_snippet = True
        if self.is_snippet_active:
            # This is a nested snippet / text on snippet
            leaf, snippet_root, _ = self._find_node_by_position(line, column)

            if snippet_root is not None:
                new_snippet = False
                root_number = snippet_root.number
                next_number = root_number + 1
                snippet_map = visitor.snippet_map
                for snippet_number in snippet_map:
                    snippet_nodes = snippet_map[snippet_number]
                    for snippet_node in snippet_nodes:
                        snippet_node.number = next_number
                    next_number += 1
                for snippet_number in self.snippets_map:
                    if snippet_number > root_number:
                        snippet_nodes = self.snippets_map[snippet_number]
                        for snippet_node in snippet_nodes:
                            snippet_node.number = next_number
                        next_number += 1
                snippet_root.placeholder = ast
                self._update_ast()
                if len(snippet_map) > 0:
                    self.select_snippet(snippet_number=root_number + 1)
            elif leaf is not None:
                self.reset()

        if new_snippet:
            self.reset()



            self.ast = ast
            self.snippets_map = visitor.snippet_map
            if len(self.snippets_map) > 0:
                # Completion contains snippets
                self.is_snippet_active = True
                self.starting_position = (line, column)
                self.update_position_tree(visitor)
                self.draw_snippets()
                self.select_snippet(snippet_number=1)
            else:
                # Completion does not contain snippets
                self.reset()
