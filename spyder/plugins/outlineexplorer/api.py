# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""Outline explorer API.

You need to declare a OutlineExplorerProxy, and a function for handle the
edit_goto Signal.

class OutlineExplorerProxyCustom(OutlineExplorerProxy):
    ...


def handle_go_to(name, line, text):
    ...

outlineexplorer = OutlineExplorerWidget(None)
oe_proxy = OutlineExplorerProxyCustom(name)
outlineexplorer.set_current_editor(oe_proxy, update=True, clear=False)

outlineexplorer.edit_goto.connect(handle_go_to)
"""
from qtpy.QtCore import Signal, QObject


class OutlineExplorerProxy(QObject):
    """
    Proxy class between editors and OutlineExplorerWidget.
    """

    sig_cursor_position_changed = Signal(int, int)
    sig_outline_explorer_data_changed = Signal()

    def __init__(self):
        super(OutlineExplorerProxy, self).__init__()
        self.fname = None

    def is_python(self):
        """Return whether the editor is a python file or not."""
        raise NotImplementedError

    def get_id(self):
        """Return an unique id, used for identify objects in a dict"""
        raise NotImplementedError

    def give_focus(self):
        """Give focus to the editor, called when toogling visibility of
        OutlineExplorerWidget."""
        raise NotImplementedError

    def get_line_count(self):
        """Return the number of lines of the editor (int)."""
        raise NotImplementedError

    def parent(self):
        """This is used for diferenciate editors in multi-window mode."""
        return None

    def get_cursor_line_number(self):
        """Return the cursor line number."""
        raise NotImplementedError

    def outlineexplorer_data_list(self):
        """Returns a list of outline explorer data."""
        raise NotImplementedError


class OutlineExplorerData(QObject):
    CLASS, FUNCTION, STATEMENT, COMMENT, CELL = list(range(5))
    FUNCTION_TOKEN = 'def'
    CLASS_TOKEN = 'class'

    def __init__(self, block, text=None, fold_level=None, def_type=None,
                 def_name=None, color=None):
        """
        Args:
            text (str)
            fold_level (int)
            def_type (int): [CLASS, FUNCTION, STATEMENT, COMMENT, CELL]
            def_name (str)
            color (PyQt.QtGui.QTextCharFormat)
        """
        super(OutlineExplorerData, self).__init__()
        self.text = text
        self.fold_level = fold_level
        self.def_type = def_type
        self.def_name = def_name
        self.color = color
        self.block = block

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
