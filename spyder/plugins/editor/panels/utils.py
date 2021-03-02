# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""General editor panel utilities."""

# Standard library imports
import bisect
import uuid

# Third-party imports
from intervaltree import IntervalTree
import textdistance

# --------------------- Code Folding Panel ------------------------------------


class FoldingRegion:
    """Internal representation of a code folding region."""

    def __init__(self, text, fold_range):
        self.text = text
        self.fold_range = fold_range
        self.id = str(uuid.uuid4())
        self.index = None
        self.nesting = 0
        self.children = []
        self.status = False
        self.parent = None

    def delete(self):
        for child in self.children:
            child.parent = None

        self.children = []
        if self.parent is not None:
            self.parent.remove_node(self)
            self.parent = None

    def add_node(self, node):
        node.parent = self
        node.nesting = self.nesting + 1
        children_ranges = [c.fold_range[0] for c in self.children]
        node_range = node.fold_range[0]
        new_index = bisect.bisect_left(children_ranges, node_range)
        node.index = new_index
        for child in self.children[new_index:]:
            child.index += 1
        self.children.insert(new_index, node)

    def remove_node(self, node):
        for child in self.children[node.index + 1:]:
            child.index -= 1

        try:
            self.children.pop(node.index)
        except IndexError:
            pass
        for idx, next_idx in zip(self.children, self.children[1:]):
            assert idx.index < next_idx.index

    def clone_node(self, node):
        self.id = node.id
        self.index = node.index
        self.nesting = node.nesting
        self.parent = node.parent
        self.children = node.children
        self.status = node.status

        for child in self.children:
            child.parent = self

        if self.parent is not None:
            self.parent.replace_node(self.index, self)

    def replace_node(self, index, node):
        self.children[index] = node
        node.parent = self

    def __repr__(self):
        return str(self)

    def __str__(self):
        return '({0}, {1}, {2}, {3})'.format(
            self.fold_range, self.text, self.id, self.status)


class FoldingStatus(dict):
    """
    Code folding status storage.

    This dictionary subclass is used to update and get the status of a
    folding region without having to deal with the internal representation.
    """

    def values(self):
        values = dict.values(self)
        return [x.status for x in values]

    def __getitem__(self, key):
        value = dict.__getitem__(self, key)
        return value.status

    def __setitem__(self, key, value):
        if isinstance(value, FoldingRegion):
            dict.__setitem__(self, key, value)
        else:
            region = dict.__getitem__(self, key)
            region.status = value


def merge_interval(parent, node):
    """Build code folding tree representation from interval tree."""
    match = False
    start, __ = node.fold_range
    while parent.parent is not None and not match:
        __, parent_end = parent.fold_range
        if parent_end <= start:
            parent = parent.parent
        else:
            match = True

    if node.parent is not None:
        node.parent.remove_node(node)
        node.parent = None

    parent.add_node(node)
    return node


def merge_folding(ranges, current_tree, root):
    """Compare previous and current code folding tree information."""
    folding_ranges = []
    for starting_line, ending_line, text in ranges:
        if ending_line > starting_line:
            starting_line += 1
            ending_line += 1
            folding_repr = FoldingRegion(text, (starting_line, ending_line))
            folding_ranges.append((starting_line, ending_line, folding_repr))

    tree = IntervalTree.from_tuples(folding_ranges)
    changes = tree - current_tree
    deleted = current_tree - tree
    adding_folding = len(changes) > len(deleted)

    deleted_iter = iter(sorted(deleted))
    changes_iter = iter(sorted(changes))
    deleted_entry = next(deleted_iter, None)
    changed_entry = next(changes_iter, None)
    non_merged = 0

    while deleted_entry is not None and changed_entry is not None:
        deleted_entry_i = deleted_entry.data
        changed_entry_i = changed_entry.data
        dist = textdistance.jaccard.normalized_similarity(
            deleted_entry_i.text, changed_entry_i.text)

        if dist >= 0.80:
            # Copy folding status
            changed_entry_i.clone_node(deleted_entry_i)
            deleted_entry = next(deleted_iter, None)
            changed_entry = next(changes_iter, None)
        else:
            if adding_folding:
                # New symbol added
                non_merged += 1
                changed_entry = next(changes_iter, None)
            else:
                # Symbol removed
                deleted_entry_i.delete()
                non_merged += 1
                deleted_entry = next(deleted_iter, None)

    if deleted_entry is not None:
        while deleted_entry is not None:
            # Symbol removed
            deleted_entry_i = deleted_entry.data
            deleted_entry_i.delete()
            non_merged += 1
            deleted_entry = next(deleted_iter, None)

    if changed_entry is not None:
        while changed_entry is not None:
            non_merged += 1
            changed_entry = next(changes_iter, None)

    if non_merged > 0:
        tree_copy = IntervalTree(tree)
        tree_copy.merge_overlaps(
            data_reducer=merge_interval,
            data_initializer=root)
    return tree, root


def collect_folding_regions(root):
    queue = [(x, 0, -1) for x in root.children]
    folding_status = FoldingStatus({})
    folding_regions = {}
    folding_nesting = {}
    folding_levels = {}
    while queue != []:
        node, folding_level, folding_nest = queue.pop(0)
        start, end = node.fold_range
        folding_regions[start] = end
        folding_levels[start] = folding_level
        folding_nesting[start] = folding_nest
        folding_status[start] = node
        queue = [(x, folding_level + 1, start) for x in node.children] + queue
    return folding_regions, folding_nesting, folding_levels, folding_status
