# -*- coding: utf-8 -*-
#
# Copyright (c) 2009- Spyder Project Contributors
#
# Distributed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""
API utilities.
"""


def get_class_values(cls):
    """
    Get the attribute values for the class enumerations used in our
    API.

    Idea from:
    https://stackoverflow.com/a/17249228/438386
    """
    return [v for (k, v) in cls.__dict__.items() if k[:1] != '_']


class PrefixNode:
    """Utility class used to represent a prefixed string tuple."""

    def __init__(self, path=None):
        self.children = {}
        self.path = path

    def __iter__(self):
        prefix = [((self.path,), self)]
        while prefix != []:
            current_prefix, node = prefix.pop(0)
            prefix += [(current_prefix + (c,), node.children[c])
                       for c in node.children]
            yield current_prefix

    def add_path(self, path):
        prefix, *rest = path
        if prefix not in self.children:
            self.children[prefix] = PrefixNode(prefix)

        if len(rest) > 0:
            child = self.children[prefix]
            child.add_path(rest)


class PrefixedTuple(PrefixNode):
    """Utility class to store and iterate over prefixed string tuples."""

    def __iter__(self):
        for key in self.children:
            child = self.children[key]
            for prefix in child:
                yield prefix
