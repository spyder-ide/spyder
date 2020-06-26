# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""Outline explorer editor server"""

# Standard library imports
import uuid

# Third-party imports
from intervaltree import IntervalTree

# Local imports
from spyder.plugins.outlineexplorer.api import OutlineExplorerProxy


class SymbolStatus:
    def __init__(self, name, position):
        self.name = name
        self.position = position
        self.id = str(uuid.uuid4())
        self.status = False

    def __eq__(self, other):
        return (self.position, self.name) == (other.position, other.name)

    def __repr__(self):
        return str(self)

    def __str__(self):
        return f'({self.position}, {self.name}, {self.id}, {self.status})'


class OutlineExplorerProxyEditor(OutlineExplorerProxy):
    def __init__(self, editor, fname):
        super(OutlineExplorerProxyEditor, self).__init__()
        self._editor = editor
        self.fname = fname
        self.symbol_info = {}
        self.current_tree = IntervalTree()
        editor.sig_cursor_position_changed.connect(
            self.sig_cursor_position_changed)

    def update_outline_info(self, info):
        for symbol in info:
            symbol_name = symbol['name']
            # NOTE: This could be also a DocumentSymbol
            symbol_range = symbol['location']['range']
            symbol_start = symbol_range['start']['line']
            symbol_end = symbol_range['end']['line']
            symbol_repr = SymbolStatus(symbol_name, (symbol_start, symbol_end))
            tree_info.append((symbol_start, symbol_end + 1, symbol_repr))

        tree = IntervalTree.from_tuples(tree_info)
        changes = tree - self.current_tree
        deleted = self.current_tree - tree

        if len(changes) == 0 and len(deleted) == 0:
            return

        adding_symbols = len(changes) > len(deleted)
        deleted_iter = iter(sorted(deleted))
        changes_iter = iter(sorted(changes))
        deleted_entry = next(deleted_iter, None)
        changed_entry = next(changes_iter, None)

        while deleted_entry is not None and changed_entry is not None:
            deleted_entry_i = deleted_entry.data
            changed_entry_i = changed_entry.data

            if deleted_entry_i.name == changed_entry_i.name:
                # Copy symbol status
                changed_entry_i.id = deleted_entry_i.id
                changed_entry_i.status = deleted_entry_i.status
                self.symbol_info[changed_entry_i.id] = changed_entry_i
                deleted_entry = next(deleted_iter, None)
                changed_entry = next(changes_iter, None)
            else:
                if adding_symbols:
                    self.symbol_info[changed_entry_i.id] = changed_entry_i
                    changed_entry = next(changes_iter, None)
                else:
                    self.symbol_info.pop(deleted_entry_i.id)
                    deleted_entry = next(deleted_iter, None)

        if deleted_entry is not None:
            while deleted_entry is not None:
                deleted_entry_i = deleted_entry.data
                self.symbol_info.pop(deleted_entry_i.id)
                deleted_entry = next(deleted_iter, None)

        if changed_entry is not None:
            while changed_entry is not None:
                changed_entry_i = changed_entry.data
                self.symbol_info[changed_entry_i.id] = changed_entry_i
                changed_entry = next(changes_iter, None)

        self.current_tree = tree
        self.sig_outline_explorer_data_changed.emit()

    def is_python(self):
        return self._editor.is_python()

    def get_id(self):
        return self._editor.get_document_id()

    def give_focus(self):
        self._editor.clearFocus()
        self._editor.setFocus()

    def get_cursor_line_number(self):
        return self._editor.get_cursor_line_number()

    def get_line_count(self):
        return self._editor.get_line_count()

    def parent(self):
        return self._editor.parent()

    def outlineexplorer_data_list(self):
        """Get outline explorer data list."""
        return self._editor.outlineexplorer_data_list()
