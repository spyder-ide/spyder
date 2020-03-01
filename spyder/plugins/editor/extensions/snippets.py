# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""Code snippets editor extension."""

# Standard library imports
import copy
import functools
import inspect

# Third party imports
from qtpy.QtGui import QTextCursor, QColor
from qtpy.QtCore import Qt, QMutex, QMutexLocker
from diff_match_patch import diff_match_patch

try:
    from rtree import index
    rtree_available = True
except Exception:
    rtree_available = False

# Local imports
from spyder.py3compat import to_text_string
from spyder.api.editorextension import EditorExtension
from spyder.utils.snippets.ast import build_snippet_ast, nodes, tokenize


MERGE_ALLOWED = {'int', 'name', 'whitespace'}
VALID_UPDATES = {diff_match_patch.DIFF_DELETE, diff_match_patch.DIFF_INSERT}


def no_undo(f):
    """Inidicate that a modification function should not be called on undo."""
    f.no_undo = True
    return f


def lock(f):
    """Prevent concurrent access to snippets rtree."""
    @functools.wraps(f)
    def wrapper(self, *args, **kwargs):
        if not self.editor.code_snippets:
            return
        if not rtree_available:
            return
        with QMutexLocker(self.modification_lock):
            if not hasattr(f, 'no_undo'):
                self.update_undo_stack()
            return f(self, *args, **kwargs)
    return wrapper


class SnippetSearcherVisitor:
    """Traverse and extract information from snippets AST."""

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
        self.inserting_snippet = False
        self.active_snippet = -1
        self.node_number = 0
        self.index = None
        self.ast = None
        self.starting_position = None
        self.modification_lock = QMutex()
        self.event_lock = QMutex()
        self.update_lock = QMutex()
        self.node_position = {}
        self.snippets_map = {}
        self.undo_stack = []
        self.redo_stack = []
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
                self.remove_selection)
            self.editor.sig_undo.connect(self._undo)
            self.editor.sig_redo.connect(self._redo)
        else:
            try:
                self.editor.sig_key_pressed.disconnect(self._on_key_pressed)
                self.editor.sig_insert_completion.disconnect(self.insert_snippet)
                self.editor.sig_cursor_position_changed.disconnect(
                    self.cursor_changed)
                self.editor.sig_text_was_inserted.disconnect(self._redraw_snippets)
                self.editor.sig_will_insert_text.disconnect(self._process_text)
                self.editor.sig_will_paste_text.disconnect(self._process_text)
                self.editor.sig_will_remove_selection.disconnect(
                    self.remove_selection)
                self.editor.sig_undo.disconnect(self._undo)
                self.editor.sig_redo.disconnect(self._redo)
            except TypeError:
                pass

    def update_undo_stack(self):
        ast_copy = copy.deepcopy(self.ast)
        info = (ast_copy, self.starting_position, self.active_snippet)
        self.undo_stack.insert(0, info)

    @lock
    @no_undo
    def _undo(self):
        if len(self.undo_stack) == 0:
            self.reset()
        if self.is_snippet_active:
            num_pops = 0
            patch = self.editor.patch
            for diffs in patch:
                for (op, data) in diffs.diffs:
                    if op in VALID_UPDATES:
                        num_pops += len(data)
            if len(self.undo_stack) > 0:
                for _ in range(num_pops):
                    if len(self.undo_stack) == 0:
                        break
                    info = self.undo_stack.pop(0)
                    ast_copy = copy.deepcopy(self.ast)
                    redo_info = (ast_copy, self.starting_position,
                                 self.active_snippet)
                    self.redo_stack.insert(0, redo_info)
                    self.ast, self.starting_position, self.active_snippet = info
                self._update_ast()
                self.editor.clear_extra_selections('code_snippets')
                self.draw_snippets()

    @lock
    @no_undo
    def _redo(self):
        if self.is_snippet_active:
            num_pops = 0
            patch = self.editor.patch
            for diffs in patch:
                for (op, data) in diffs.diffs:
                    if op in VALID_UPDATES:
                        num_pops += len(data)
            if len(self.redo_stack) > 0:
                for _ in range(num_pops):
                    if len(self.redo_stack) == 0:
                        break
                    info = self.redo_stack.pop(0)
                    ast_copy = copy.deepcopy(self.ast)
                    undo_info = (ast_copy, self.starting_position,
                                 self.active_snippet)
                    self.undo_stack.insert(0, undo_info)
                    self.ast, self.starting_position, self.active_snippet = info
                self._update_ast()
                self.editor.clear_extra_selections('code_snippets')
                self.draw_snippets()

    @lock
    @no_undo
    def _redraw_snippets(self):
        if self.is_snippet_active:
            self.editor.clear_extra_selections('code_snippets')
            self.draw_snippets()

    def _on_key_pressed(self, event):
        if event.isAccepted():
            return

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

                    if next_snippet == 0:
                        self.reset()
                elif key == Qt.Key_Escape:
                    self.reset()
                    event.accept()
                elif len(text) > 0:
                    not_brace = text not in {'(', ')', '[', ']', '{', '}'}
                    not_completion = (
                        text not in self.editor.auto_completion_characters)
                    not_signature = (
                        text not in self.editor.signature_completion_characters
                    )
                    valid = not_brace and not_completion and not_signature
                    if node is not None:
                        if snippet is None or text == '\n':
                            # Constant text identifier was modified
                            self.reset()
                        elif valid or text == '\b':
                            self._process_text(text)

    @lock
    def _process_text(self, text):
        if self.is_snippet_active:
            line, column = self.editor.get_cursor_line_column()
            # Update placeholder text node
            if text != '\b':
                self.insert_text(text, line, column)
            elif text == '\n':
                self.reset()
            else:
                self.delete_text(line, column)
            self._update_ast()
            self.redo_stack = []

    def delete_text(self, line, column):
        has_selected_text = self.editor.has_selected_text()
        start, end = self.editor.get_selection_start_end()
        if has_selected_text:
            self._remove_selection(start, end)
            return
        node, snippet, text_node = self._find_node_by_position(line, column)
        leaf_kind = node.name
        node_position = node.position
        if len(node_position) == 1:
            # Single, terminal node
            x, y = node_position[0]
            node_position = ((x, y), (x, y))

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
            text_parent.tokens = parent_tokens

            if len(parent_tokens) > 1:
                delete_token = parent_tokens[snippet_position - 1]
                # NOTE: There might be some problems if the previous token
                # is also a snippet
                self._delete_token(delete_token, text_parent, line, column)

            next_number = snippet_number
            for current_number in self.snippets_map:
                if current_number > snippet_number:
                    snippet_nodes = self.snippets_map[current_number]
                    for snippet_node in snippet_nodes:
                        current_number = snippet_node.number
                        snippet_node.number = next_number
                        next_number = current_number
                    # next_number -= 1
        else:
            self._delete_token(node, text_node, line, column)

    def _delete_token(self, node, text_node, line, column):
        node_position = node.position
        text_node_tokens = list(text_node.tokens)
        node_index = node.index_in_parent
        if len(node_position) == 1:
            # Single character removal
            if node_index > 0 and node_index + 1 < len(text_node_tokens):
                left_node = text_node_tokens[node_index - 1]
                right_node = text_node_tokens[node_index + 1]
                offset = 1
                if left_node.mark_for_position:
                    if not isinstance(left_node, nodes.LeafNode):
                        self.reset()
                        return
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
        if len(text_node_tokens) == 0:
            text_node_tokens = [nodes.LeafNode()]
        text_node.tokens = text_node_tokens

    def insert_text(self, text, line, column):
        has_selected_text = self.editor.has_selected_text()
        start, end = self.editor.get_selection_start_end()
        if has_selected_text:
            self._remove_selection(start, end)
            line, column = start
        node, snippet, text_node = self._find_node_by_position(line, column)
        if node is None:
            self.reset()
            return
        tokens = tokenize(text)
        token_nodes = [nodes.LeafNode(t.token, t.value) for t in tokens]
        for token in token_nodes:
            token.compute_position((line, column))
        if node.name == 'EPSILON':
            new_text_node = nodes.TextNode(*token_nodes)
            snippet.placeholder = new_text_node
            return
        position = node.position
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

        text_node.tokens = text_node_tokens

    def _insert_snippet_at_node(self, leaf, snippet, new_node,
                                line, column):
        self.redo_stack = []
        value = leaf.value
        leaf_position = leaf.position
        if len(leaf_position) == 1:
            x, y = leaf_position[0]
            leaf_position = [(x, y), (x, y + 1)]

        leaf_start, leaf_end = leaf_position
        leaf_index = leaf.index_in_parent
        placeholder = snippet.placeholder
        text_tokens = list(placeholder.tokens)
        first_tokens = text_tokens[:leaf_index]
        second_tokens = text_tokens[leaf_index + 1:]
        if leaf_start == (line, column):
            single_token = False
            if len(text_tokens) == 1:
                possible_snippet = new_node.tokens[0]
                single_token = True
                if isinstance(possible_snippet, nodes.SnippetASTNode):
                    # Placeholder replacement
                    first_tokens = (
                        list(possible_snippet.placeholder.tokens) +
                        list(new_node.tokens[1:])
                    )
                    second_tokens = []
                else:
                    first_tokens = list(new_node.tokens)
                    second_tokens = []
            if not single_token:
                if isinstance(new_node, nodes.TextNode):
                    first_tokens += list(new_node.tokens)
                else:
                    first_tokens.append(new_node)
                if not new_node.text().startswith(value):
                    first_tokens.append(leaf)
        elif leaf_end == (line, column):
            first_tokens.append(leaf)
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

    def _region_to_polygon(self, start, end):
        start_line, start_column = start
        end_line, end_column = end
        root_col = min(self.node_position)
        root_position, _ = self.node_position[root_col]
        line_limits = {}
        for segment in root_position:
            (_, start), (line, end) = segment
            line_limits[line] = (start, end)

        polygon = []
        segment = [(start_line, start_column)]
        for line in range(start_line, end_line + 1):
            seg_start, seg_end = line_limits[line]
            if len(segment) == 0:
                segment = [(line, seg_start)]
            if line < end_line:
                segment.append((line, seg_end))
            elif line == end_line:
                segment.append((line, min(seg_end, end_column)))
            polygon.append(segment)
            segment = []
        return polygon

    def _find_lowest_common_ancestor(self, start_node, end_node):
        left_node, right_node = start_node, end_node
        ancestor = None
        while left_node is not None and right_node is not None:
            while left_node.depth > right_node.depth and left_node is not None:
                left_node = left_node.parent

            if left_node is None:
                break

            while (right_node.depth > left_node.depth and
                    right_node is not None):
                right_node = right_node.parent

            if right_node is None:
                break

            if id(left_node) == id(right_node):
                if isinstance(left_node, nodes.SnippetASTNode):
                    ancestor = left_node
                    break

            left_node = left_node.parent
            right_node = right_node.parent
        return ancestor

    @lock
    def remove_selection(self, selection_start, selection_end):
        self._remove_selection(selection_start, selection_end)

    def _remove_selection(self, selection_start, selection_end):
        start_node, _, _ = self._find_node_by_position(*selection_start)
        end_node, _, _ = self._find_node_by_position(*selection_end)
        ancestor = self._find_lowest_common_ancestor(start_node, end_node)
        if ancestor is None:
            self.reset()
            return
        poly = self._region_to_polygon(selection_start, selection_end)
        bboxes = [sum(segment, tuple()) for segment in poly]
        for segment in poly:
            (_, start_column), (_, end_column) = segment
            bbox = sum(segment, tuple())
            nodes_spanned = list(self.index.intersection(bbox))
            current_position = start_column
            for node_id in nodes_spanned:
                _, node = self.node_position[node_id]
                if node.to_delete:
                    continue
                if current_position >= end_column:
                    break
                node_position = node.position
                if isinstance(node, nodes.SnippetASTNode):
                    if len(node_position) == 1:
                        node_position = node_position[0]
                        node_start, node_end = node_position[0]
                        if node_position == segment:
                            node.placeholder.delete()
                            node.placeholder = nodes.TextNode(nodes.LeafNode())
                        elif node_start == current_position:
                            if node_end <= end_column:
                                node.delete()
                                node_parent = node.parent
                                parent_tokens = list(
                                    node_parent.tokens)
                                parent_tokens.pop(node.index_in_parent)
                                node_parent.tokens = parent_tokens
                                snippet_number = node.number
                                diff = 0
                                for num in self.snippets_map:
                                    if num > snippet_number:
                                        snippet = self.snippets_map[num]
                                        snippet.number = snippet_number - diff
                                        diff += 1
                elif isinstance(node, nodes.TextNode):
                    if len(node_position) == 1:
                        (node_start, node_end) = node_position[0][0]
                        if node_start == current_position:
                            if node_end <= end_column:
                                node.delete()
                                current_position = node_end
                                if node.parent is not None:
                                    node_parent = node.parent
                                    if isinstance(node_parent, nodes.TextNode):
                                        parent_tokens = list(
                                            node.parent.tokens)
                                        parent_tokens.pop(node.index_in_parent)
                                        node_parent.tokens = parent_tokens
                elif isinstance(node, nodes.LeafNode):
                    if len(node_position) == 1:
                        leaf_line, leaf_col = node_position[0]
                        node_position = (
                            (leaf_line, leaf_col), (leaf_line, leaf_col + 1))
                    (_, node_start), (_, node_end) = node_position
                    if current_position == node_start:
                        if node_end <= end_column:
                            node_parent = node.parent
                            parent_tokens = list(node_parent.tokens)
                            parent_tokens.pop(node.index_in_parent)
                            node_parent.tokens = parent_tokens
                            current_position = node_end
                        else:
                            diff = end_column - node_end
                            node_value = node.value
                            node.value = node_value[diff:]
                            current_position = node_start + diff
                    elif node_start < current_position:
                        start_diff = current_position - node_start
                        end_diff = end_column - node_end
                        node_value = node.value
                        node.value = (node_value[:start_diff] +
                                      node_value[end_diff:])
                        current_position = (
                            current_position + (end_diff - start_diff))
        self._update_ast()

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
        if not rtree_available:
            return

        if self.inserting_snippet:
            self.inserting_snippet = False
            return

        node, nearest_snippet, _ = self._find_node_by_position(line, col)
        if node is None:
            ignore = self.editor.is_undoing or self.editor.is_redoing
            if not ignore:
                self.reset()
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
            self.undo_stack = []
            self.redo_stack = []
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

                    color = QColor(self.editor.comment_color)
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

        self.editor.setTextCursor(cursor)
        self.editor.request_signature()

    def _update_ast(self):
        if self.starting_position is not None:
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
        line, column = self.editor.get_cursor_line_column()
        visitor = SnippetSearcherVisitor(line, column, self.node_number)
        ast = build_snippet_ast(text)
        ast.compute_position((line, column))
        ast.accept(visitor)

        self.inserting_snippet = True
        self.editor.insert_text(ast.text(), will_insert_text=False)
        self.editor.document_did_change()

        if not self.editor.code_snippets:
            return

        if not rtree_available:
            return

        new_snippet = True
        if self.is_snippet_active:
            with QMutexLocker(self.modification_lock):
                # This is a nested snippet / text on snippet
                leaf, snippet_root, _ = self._find_node_by_position(
                    line, column)
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
                    self.update_undo_stack()
                    self._insert_snippet_at_node(
                        leaf, snippet_root, ast, line, column)
                    self._update_ast()
                    if len(snippet_map) > 0:
                        self.select_snippet(snippet_number=root_number + 1)
                    self.draw_snippets()
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
