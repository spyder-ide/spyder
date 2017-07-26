# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""Outline explorer API."""


class OutlineExplorerProxy(object):
    """
    Proxy class between editors and OutlineExplorerWidget.
    """
    def __init__(self):
        self.fname = None

    def get_id(self):
        """Return an unique id, used for identify objects in a dict"""
        raise NotImplementedError

    def give_focus(self):
        """Give focus to the editor, called when toogling visibility of
        OutlineExplorerWidget."""
        raise NotImplementedError

    def get_outlineexplorer_data(self):
        """Return a dict of OutlineExplorerData objects."""
        raise NotImplementedError

    def get_line_count(self):
        """Return the number of lines of the editor (int)."""
        raise NotImplementedError

    def parent():
        """This is used for diferenciate editors in multi-window mode."""
        return None


class OutlineExplorerData(object):
    CLASS, FUNCTION, STATEMENT, COMMENT, CELL = list(range(5))
    FUNCTION_TOKEN = 'def'
    CLASS_TOKEN = 'class'

    def __init__(self):
        self.text = None
        self.fold_level = None
        self.def_type = None
        self.def_name = None

    def is_not_class_nor_function(self):
        return self.def_type not in (self.CLASS, self.FUNCTION)

    def is_class_or_function(self):
        return self.def_type in (self.CLASS, self.FUNCTION)

    def is_comment(self):
        return self.def_type in (self.COMMENT, self.CELL)

    def get_class_name(self):
        if self.def_type == self.CLASS:
            return self.def_name

    def get_function_name(self):
        if self.def_type == self.FUNCTION:
            return self.def_name

    def get_token(self):
        if self.def_type == self.FUNCTION:
            token = self.FUNCTION_TOKEN
        elif self.def_type == self.CLASS:
            token = self.CLASS_TOKEN

        return token
