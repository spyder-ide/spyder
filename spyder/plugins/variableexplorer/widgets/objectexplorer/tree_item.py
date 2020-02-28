# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright (c) 2016 Pepijn Kenter.
# Copyright (c) 2019- Spyder Project Contributors
#
# Based on: PySide examples/itemviews/simpletreemodel
# See: http://harmattan-dev.nokia.com/docs/library/html/qt4/
# itemviews-simpletreemodel.html
#
# Components of objectbrowser originally distributed under
# the MIT (Expat) license. Licensed under the terms of the MIT License;
# see NOTICE.txt in the Spyder root directory for details
# -----------------------------------------------------------------------------

# Standard library imports
import logging

# Local imports
from spyder.config.base import _
from spyder.plugins.variableexplorer.widgets.objectexplorer.utils import (
    cut_off_str)

logger = logging.getLogger(__name__)

# Maximum number of characters used in the __str__ method to
# represent the underlying object
MAX_OBJ_STR_LEN = 50


# Utility functions
def name_is_special(method_name):
    """Returns true if the method name starts and ends with two underscores."""
    return method_name.startswith('__') and method_name.endswith('__')


# TreeWidget Elements
class TreeItem(object):
    """Tree node class that can be used to build trees of objects."""
    def __init__(self, obj, name, obj_path, is_attribute, parent=None):
        self.parent_item = parent
        self.obj = obj
        self.obj_name = str(name)
        self.obj_path = str(obj_path)
        self.is_attribute = is_attribute
        self.child_items = []
        self.has_children = True
        self.children_fetched = False

    def __str__(self):
        n_children = len(self.child_items)
        if n_children == 0:
            return _("<TreeItem(0x{:x}): {} = {}>").format(
                id(self.obj),
                self.obj_path,
                cut_off_str(self.obj, MAX_OBJ_STR_LEN))
        else:
            return _("<TreeItem(0x{:x}): {} ({:d} children)>").format(
                id(self.obj),
                self.obj_path,
                len(self.child_items))

    def __repr__(self):
        n_children = len(self.child_items)
        return _("<TreeItem(0x{:x}): {} ({:d} children)>") \
            .format(id(self.obj), self.obj_path, n_children)

    @property
    def is_special_attribute(self):
        """
        Return true if the items is an attribute and its
        name begins and end with 2 underscores.
        """
        return self.is_attribute and name_is_special(self.obj_name)

    @property
    def is_callable_attribute(self):
        """Return true if the items is an attribute and it is callable."""
        return self.is_attribute and self.is_callable

    @property
    def is_callable(self):
        """Return true if the underlying object is callable."""
        return callable(self.obj)

    def append_child(self, item):
        item.parent_item = self
        self.child_items.append(item)

    def insert_children(self, idx, items):
        self.child_items[idx:idx] = items
        for item in items:
            item.parent_item = self

    def child(self, row):
        return self.child_items[row]

    def child_count(self):
        return len(self.child_items)

    def parent(self):
        return self.parent_item

    def row(self):
        if self.parent_item:
            return self.parent_item.child_items.index(self)
        else:
            return 0

    def pretty_print(self, indent=0):
        if 0:
            logger.debug(indent * "    " + str(self))
        else:
            logger.debug(indent * "    " + str(self))
        for child_item in self.child_items:
            child_item.pretty_print(indent + 1)
