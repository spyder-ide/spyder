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
from qtpy.QtCore import Qt, Slot, QMutex, QMutexLocker

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
        self.modification_lock = QMutex()
        self.event_lock = QMutex()
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
            self.editor.sig_text_was_inserted.connect(self._redraw_snippets)
            self.editor.sig_will_insert_text.connect(self._process_text)
            self.editor.sig_will_paste_text.connect(self._process_text)
            self.editor.sig_will_remove_selection.connect(
                self._remove_selection)
        else:
            self.editor.sig_key_pressed.disconnect(self._on_key_pressed)
            self.editor.sig_insert_completion.disconnect(self.insert_snippet)
            self.editor.sig_cursor_position_changed.disconnect(
                self.cursor_changed)
            self.editor.sig_text_was_inserted.disconnect(self._redraw_snippets)
            self.editor.sig_will_insert_text.disconnect(self._process_text)
            self.editor.sig_will_paste_text.disconnect(self._process_text)
            self.editor.sig_will_remove_selection.disconnect(
                self._remove_selection)

    def _redraw_snippets(self):
        if self.is_snippet_active:
            self.editor.clear_extra_selections('code_snippets')
            self.draw_snippets()

    def _on_key_pressed(self, event):
        if event.isAccepted():
            return

        # if self.editor.completion_widget.isVisible():
        #     if not self.editor.completion_widget.is_empty():
        #         return

        with QMutexLocker(self.event_lock):
            key = event.key()
            text = to_text_string(event.text())

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
                            self._process_text(text)

    def _process_text(self, text):
        with QMutexLocker(self.modification_lock):
            if self.is_snippet_active:
                line, column = self.editor.get_cursor_line_column()
                # Update placeholder text node
                if text != '\b':
                    self.insert_text(text, line, column)
                    # text_node = nodes.TextNode(*token_nodes)
                    # snippet.placeholder = text_node
                else:
                    self.delete_text(line, column)
                self._update_ast()

    def delete_text(self, line, column):
        node, snippet, text_node = self._find_node_by_position(line, column)
        leaf_kind = node.name
        node_position = node.position
        print(node.position)
        if len(node_position) == 1:
            # Single, terminal node
            x, y = node_position[0]
            node_position = ((x, y), (x, y))
        print(text_node.position)
        first_text_position = text_node.position[0][0]
        first_text_start, first_text_end = first_text_position
        node_start, node_end = node_position
        if first_text_position == (line, column):
            # Snippet is dissolved and replaced by its own text
            snippet_number = snippet.number
            snippet_position = snippet.index_in_parent
            text_parent = snippet.parent
            parent_tokens = list(text_parent.tokens)
            parent_tokens = (parent_tokens[:snippet_position] +
                             list(snippet.placeholder.tokens) +
                             parent_tokens[snippet_position + 1:])
            # parent_tokens.pop(snippet_position)

            # parent_tokens.insert(snippet_position, snippet.placeholder)
            text_parent.tokens = parent_tokens

            if len(parent_tokens) > 1:
                delete_token = parent_tokens[snippet_position - 1]
                # NOTE: There might be some problems if the previous token
                # is also a snippet
                self._delete_token(delete_token, text_parent, line, column)

            next_number = snippet_number - 1
            for current_number in self.snippets_map:
                if current_number > snippet_number:
                    snippet_nodes = self.snippets_map[current_number]
                    for snippet_node in snippet_nodes:
                        snippet_node.number = next_number
                    next_number -= 1
        else:
            self._delete_token(node, text_node, line, column)

    def _delete_token(self, node, text_node, line, column):
        node_position = node.position
        text_node_tokens = list(text_node.tokens)
        print(node, node_position)
        node_index = node.index_in_parent
        if len(node_position) == 1:
            # Single character removal
            if node_index > 0 and node_index + 1 < len(text_node_tokens):
                left_node = text_node_tokens[node_index - 1]
                right_node = text_node_tokens[node_index + 1]
                print(left_node, right_node)
                offset = 1
                if left_node.mark_for_position:
                    if left_node.name in MERGE_ALLOWED:
                        if left_node.name == right_node.name:
                            left_node.value = (
                                left_node.value + right_node.value)
                            offset = 2
                text_node_tokens = (
                    text_node_tokens[:node_index] +
                    text_node_tokens[node_index + offset:]
                )
            else:
                text_node_tokens.pop(node_index)
        else:
            node_start, node_end = node_position
            print(node_position, (line, column))
            if node_start == (line, column):
                previous_token = text_node_tokens[node_index - 1]
                previous_value = previous_token.value
                previous_value = previous_value[:-1]
                merge = True
                diff = 0
                if len(previous_value) == 0:
                    if node_index - 2 > 0:
                        previous_token = text_node_tokens[node_index - 2]
                    else:
                        merge = False
                    text_node_tokens.pop(node_index - 1)
                    diff = 1
                else:
                    previous_token.value = previous_value

                if merge:
                    if node.mark_for_position:
                        if node.name in MERGE_ALLOWED:
                            if node.name == previous_token.name:
                                previous_token.value = (
                                    previous_token.value + node.value)
                                text_node_tokens.pop(node_index - diff)
            elif node_end == (line, column):
                node_value = node.value
                node_value = node_value[:-1]
                if len(node_value) == 0:
                    text_node_tokens.pop(node_index)
                else:
                    node.value = node_value
            else:
                x, y = node_start
                diff = column - y
                node_value = node.value
                node_value = node_value[:diff] + node_value[diff + 1:]
                node.value = node_value
        print(text_node_tokens)
        if len(text_node_tokens) == 0:
            text_node_tokens = [nodes.LeafNode()]
        text_node.tokens = text_node_tokens

    def insert_text(self, text, line, column):
        node, snippet, text_node = self._find_node_by_position(line, column)
        leaf_kind = node.name
        tokens = tokenize(text)
        token_nodes = [nodes.LeafNode(t.token, t.value) for t in tokens]
        for token in token_nodes:
            token.compute_position((line, column))
        if node.name == 'EPSILON':
            new_text_node = nodes.TextNode(*token_nodes)
            snippet.placeholder = new_text_node
            return
        position = node.position
        print(position, (line, column))
        if len(position) == 1:
            x, y = position[0]
            position = ((x, y), (x, y + 1))
        leaf_start, leaf_end = position
        node_index = node.index_in_parent
        text_node_tokens = list(text_node.tokens)

        if (line, column) == leaf_start:
            left_offset = 0
            right_offset = 0
            first_token = token_nodes[0]
            last_token = token_nodes[-1]
            if node_index > 0 and len(text_node_tokens) > 1:
                previous_node = text_node_tokens[node_index - 1]
                if first_token.mark_for_position:
                    if first_token.name in MERGE_ALLOWED:
                        if first_token.name == previous_node.name:
                            left_offset = 1
                            first_token.value = (
                                previous_node.value + first_token.value)
            if last_token.mark_for_position:
                if last_token.name in MERGE_ALLOWED:
                    if last_token.name == node.name:
                        right_offset = 1
                        last_token.value = (
                            last_token.value + node.value)
            text_node_tokens = (
                text_node_tokens[:node_index - left_offset] +
                token_nodes +
                text_node_tokens[node_index + right_offset:]
            )
        elif (line, column) == leaf_end:
            left_offset = -1
            right_offset = 1
            first_token = token_nodes[0]
            last_token = token_nodes[-1]
            if node_index >= 1 and node_index < len(text_node_tokens) - 1:
                next_node = text_node_tokens[node_index + 1]
                if last_token.mark_for_position:
                    if last_token.name in MERGE_ALLOWED:
                        if last_token.name == next_node.name:
                            right_offset = 2
                            last_token.value = (
                                last_token.value + next_node.value)

            if first_token.mark_for_position:
                if first_token.name in MERGE_ALLOWED:
                    if first_token.name == node.name:
                        left_offset = 0
                        # right_offset = 1
                        first_token.value = (
                            node.value + first_token.value)

            text_node_tokens = (
                text_node_tokens[:node_index - left_offset] +
                token_nodes +
                text_node_tokens[node_index + right_offset:]
            )
        else:
            _, start_pos = leaf_start
            diff = column - start_pos
            value = node.value
            first_tokens = text_node_tokens[:node_index]
            second_tokens = text_node_tokens[node_index + 1:]
            first_part = value[:diff]
            second_part = value[diff:]
            print(value)
            print(first_part, second_part)
            first_token = token_nodes[0]
            last_token = token_nodes[-1]
            left_merge = False
            if first_token.mark_for_position:
                if first_token.name in MERGE_ALLOWED:
                    if first_token == node.name:
                        left_merge = True
                        first_token.value = first_part + first_token.value
            if not left_merge:
                first_tokens.append(nodes.LeafNode(node.name, first_part))

            right_merge = False
            if last_token.mark_for_position:
                if last_token.name in MERGE_ALLOWED:
                    if last_token == node.name:
                        right_merge = True
                        last_token.value = last_token.value + second_part
            if not right_merge:
                second_tokens.insert(0, nodes.LeafNode(node.name, second_part))

            text_node_tokens = first_tokens + token_nodes + second_tokens

        print(text_node_tokens)
        text_node.tokens = text_node_tokens

    def _insert_snippet_at_node(self, leaf, snippet, new_node,
                                line, column):
        value = leaf.value
        leaf_position = leaf.position
        if len(leaf_position) == 1:
            x, y = leaf_position[0]
            leaf_position = [(x, y), (x, y + 1)]
        print(leaf_position, (line, column))
        leaf_start, leaf_end = leaf_position
        leaf_index = leaf.index_in_parent
        placeholder = snippet.placeholder
        text_tokens = list(placeholder.tokens)
        first_tokens = text_tokens[:leaf_index]
        second_tokens = text_tokens[leaf_index + 1:]
        if leaf_start == (line, column):
            print(value, new_node.text())
            # first_tokens = first_tokens + new_node.tokens
            single_token = False
            if len(text_tokens) == 1:
                print('Single text_token')
                print(new_node.tokens)
                possible_snippet = new_node.tokens[0]
                print(possible_snippet)
                single_token = True
                if isinstance(possible_snippet, nodes.SnippetASTNode):
                    # Placeholder replacement
                    print('Moving placeholder to up')
                    first_tokens = (
                        list(possible_snippet.placeholder) +
                        list(new_node.tokens[1:])
                    )
                    second_tokens = []
                else:
                    first_tokens = list(new_node.tokens)
                    second_tokens = []
            if not single_token:
                first_tokens.append(new_node)
                if not new_node.text().startswith(value):
                    first_tokens.append(leaf)
        elif leaf_end == (line, column):
            # if not value.endswith(new_node.text()):
            #     first_tokens.append(leaf)
            # if self.editor.completion_widget.is_empty():
            # print(value, new_node.text())
            first_tokens.append(leaf)
            # first_tokens = first_tokens + new_node.tokens
            first_tokens.append(new_node)
        else:
            _, start_pos = leaf_start
            diff = column - start_pos

            first_part = value[:diff]
            second_part = value[diff:]
            first_node = nodes.LeafNode(leaf.name, first_part)
            second_node = nodes.LeafNode(leaf.name, second_part)
            first_tokens.append(first_node)
            first_tokens.append(new_node)
            first_tokens.append(second_node)
        text_tokens = first_tokens + second_tokens
        placeholder.tokens = text_tokens
        print(text_tokens)

    def _remove_selection(self, selection_start, selection_end):
        with QMutexLocker(self.modification_lock):
            print(selection_start, selection_end)

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

        self.editor.insert_text(ast.text(), will_insert_text=False)
        self.editor.document_did_change()

        new_snippet = True
        if self.is_snippet_active:
            with QMutexLocker(self.modification_lock):
                # This is a nested snippet / text on snippet
                leaf, snippet_root, _ = self._find_node_by_position(
                    line, column)
                print(leaf, snippet_root)

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
                    # snippet_root.placeholder = ast
                    self._insert_snippet_at_node(
                        leaf, snippet_root, ast, line, column)
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
