# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""
Contains the text debugger manager.
"""
from qtpy.QtCore import Signal
from qtpy.QtWidgets import QInputDialog, QLineEdit

from spyder.config.base import _
from spyder.py3compat import to_text_string
from spyder.api.manager import Manager
from spyder.widgets.sourcecode.utils.editor import BlockUserData


class DebuggerManager(Manager):
    """
    Manages adding/removing breakpoint from the editor.
    """
    def __init__(self, editor):
        super(DebuggerManager, self).__init__(editor)
        self.breakpoints = self.get_breakpoints()

    def toogle_breakpoint(self, line_number=None, condition=None,
                          edit_condition=False):
        """Add/remove breakpoint."""
        if not self.editor.is_python_like():
            return
        if line_number is None:
            block = self.editor.textCursor().block()
        else:
            block = self.editor.document().findBlockByNumber(line_number-1)
        data = block.userData()
        if not data:
            data = BlockUserData(self.editor)
            data.breakpoint = True
        elif not edit_condition:
            data.breakpoint = not data.breakpoint
            data.breakpoint_condition = None
        if condition is not None:
            data.breakpoint_condition = condition
        if edit_condition:
            condition = data.breakpoint_condition
            condition, valid = QInputDialog.getText(self,
                                        _('Breakpoint'),
                                        _("Condition:"),
                                        QLineEdit.Normal, condition)
            if not valid:
                return
            data.breakpoint = True
            data.breakpoint_condition = str(condition) if condition else None
        if data.breakpoint:
            text = to_text_string(block.text()).strip()
            if len(text) == 0 or text.startswith(('#', '"', "'")):
                data.breakpoint = False
        block.setUserData(data)
        self.editor.sig_flags_changed.emit()
        self.editor.breakpoints_changed.emit()

    def get_breakpoints(self):
        """Get breakpoints"""
        breakpoints = []
        block = self.editor.document().firstBlock()
        for line_number in range(1, self.editor.document().blockCount()+1):
            data = block.userData()
            if data and data.breakpoint:
                breakpoints.append((line_number, data.breakpoint_condition))
            block = block.next()
        return breakpoints

    def clear_breakpoints(self):
        """Clear breakpoints"""
        self.breakpoints = []
        for data in self.editor.blockuserdata_list[:]:
            data.breakpoint = False
            # data.breakpoint_condition = None  # not necessary, but logical
            if data.is_empty():
                # This is not calling the __del__ in BlockUserData.  Not
                # sure if it's supposed to or not, but that seems to be the
                # intent.
                del data

    def set_breakpoints(self, breakpoints):
        """Set breakpoints"""
        self.clear_breakpoints()
        for line_number, condition in breakpoints:
            self.toogle_breakpoint(line_number, condition)

    def update_breakpoints(self):
        """Update breakpoints"""
        self.editor.breakpoints_changed.emit()
