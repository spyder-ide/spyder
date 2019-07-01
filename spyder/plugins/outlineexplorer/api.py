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
import re

from qtpy.QtCore import Signal, QObject
from spyder.config.base import _


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

    # Emitted if the OutlineExplorerData was changed
    sig_update = Signal()

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

    @property
    def def_name(self):
        """Get the cell name."""
        # Non cell don't need unique names.
        if self.def_type != self.CELL:
            return self._def_name

        def get_name(oedata):
            name = oedata._def_name
            if not name:
                name = _('Unnamed Cell')
            return name

        self_name = get_name(self)

        existing_numbers = []

        def check_match(oedata):
            # Look for "string"
            other_name = get_name(oedata)
            pattern = '^' + re.escape(self_name) + r'(?:, #(\d+))?$'
            match = re.match(pattern, other_name)
            if match:
                # Check if already has a number
                number = match.groups()[0]
                if number:
                    existing_numbers.append(int(number))
                return True
            return False

        # Count cells
        N_prev = 0
        for oedata in self._document_cells(forward=False):
            if check_match(oedata):
                N_prev += 1
        N_fix_previous = len(existing_numbers)

        N_next = 0
        for oedata in self._document_cells(forward=True):
            if check_match(oedata):
                N_next += 1

        # Get the remaining indexeswe can use
        free_indexes = [idx for idx in range(N_prev + N_next + 1)
                        if idx + 1 not in existing_numbers]

        idx = free_indexes[N_prev - N_fix_previous]

        if N_prev + N_next > 0:
            return self_name + ', #{}'.format(idx + 1)

        return self_name

    @def_name.setter
    def def_name(self, value):
        """Set name."""
        self._def_name = value

    def _document_cells(self, forward=True):
        """
        Get all cells oedata in the document.

        Parameters
        ----------
        forward : bool, optional
            Whether to iterate forward or backward from the current block.
        """
        if forward:
            block = self.block.next()
        else:
            block = self.block.previous()

        while block.isValid():
            data = block.userData()
            if data and data.oedata and data.oedata.def_type == self.CELL:
                yield data.oedata
            if forward:
                block = block.next()
            else:
                block = block.previous()

    def update(self, other):
        """Try to update to avoid reloading everything."""
        if (self.def_type == other.def_type and
                self.fold_level == other.fold_level):
            self.text = other.text
            old_def_name = self._def_name
            self._def_name = other._def_name
            self.color = other.color
            self.sig_update.emit()
            if self.def_type == self.CELL:
                if self.cell_level != other.cell_level:
                    return False
                # Must update all other cells whose name has changed.
                for oedata in self._document_cells(forward=True):
                    if oedata._def_name in [self._def_name, old_def_name]:
                        oedata.sig_update.emit()
            return True
        return False

    def is_valid(self):
        """Check if the oedata has a valid block attached."""
        block = self.block
        return (block
                and block.isValid()
                and block.userData()
                and block.userData().oedata == self
                )

    def cell_index(self):
        """Get the cell index."""
        if self.def_type != self.CELL:
            raise RuntimeError("This is not a cell.")
        # Cell 0 has no header
        return len(list(self._document_cells(forward=False))) + 1

    def has_name(self):
        """Check if cell has a name."""
        if self._def_name:
            return True
        else:
            return False
