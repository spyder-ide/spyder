# -*- coding: utf-8 -*-

# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""General purpose prefix tree, also known as a trie."""


class TrieNode:
    def __init__(self, key=None, value=None):
        self.children = {}
        self.key = key
        self.value = value

    def __setitem__(self, sequence, value):
        elem = sequence[0]
        if self.key is None:
            self.key = elem

        if len(self.key) > 0:
            sequence = sequence[1:]

        if sequence:
            elem = sequence[0]
            node = self.children.get(elem, None)
            if node is None:
                node = TrieNode()
                self.children[elem] = node
            node[sequence] = value
        else:
            self.value = value

    def __getitem__(self, sequence):
        node = None
        if sequence[0] == self.key:
            sequence = sequence[1:]
            if sequence:
                if sequence[0] in self.children:
                    next_children = self.children[sequence[0]]
                    node = next_children[sequence]
            else:
                node = self
        return node

    def __iter__(self):
        queue = [self]
        while queue != []:
            node = queue.pop(0)
            queue += list(node.children.values())
            if node.value is not None:
                yield node

    def __contains__(self, sequence):
        if len(sequence) + len(self.key) == 0:
            return True

        elem = sequence[0]
        if elem == self.key:
            sequence = sequence[1:]
            if not sequence:
                if self.value is not None:
                    return True
                else:
                    return False
            elem = sequence[0]

        found = elem in self.children
        if found:
            next_children = self.children[elem]
            found = sequence in next_children
        return found


class Trie(TrieNode):
    def __init__(self):
        super().__init__('')
        self.sequences = []

    def __getitem__(self, sequence):
        if sequence:
            elem = sequence[0]
            if elem in self.children:
                node = self.children[elem]
                return node[sequence]
        else:
            return self
        return None

    def __setitem__(self, sequence, value):
        if sequence:
            super().__setitem__(sequence, value)
        else:
            self.value = value
