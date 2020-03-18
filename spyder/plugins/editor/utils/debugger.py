# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""
Contains the text debugger manager.
"""
import os.path as osp

from qtpy.QtWidgets import QInputDialog, QLineEdit

from spyder.config.manager import CONF
from spyder.config.base import _
from spyder.py3compat import to_text_string
from spyder.api.manager import Manager
from spyder.plugins.editor.utils.editor import BlockUserData


def _load_all_breakpoints():
    return CONF.get('run', 'breakpoints', {})


def load_breakpoints(filename):
    breakpoints = _load_all_breakpoints().get(filename, [])
    if breakpoints and isinstance(breakpoints[0], int):
        # Old breakpoints format
        breakpoints = [(lineno, None) for lineno in breakpoints]
    return breakpoints


def save_breakpoints(filename, breakpoints):
    bp_dict = _load_all_breakpoints()
    bp_dict[filename] = breakpoints
    CONF.set('run', 'breakpoints', bp_dict)


def clear_all_breakpoints():
    CONF.set('run', 'breakpoints', {})


def clear_breakpoint(filename, lineno):
    breakpoints = load_breakpoints(filename)
    if breakpoints:
        for breakpoint in breakpoints[:]:
            if breakpoint[0] == lineno:
                breakpoints.remove(breakpoint)
        save_breakpoints(filename, breakpoints)


class DebuggerManager(Manager):
    """
    Manages adding/removing breakpoint from the editor.
    """
    def __init__(self, editor):
        super(DebuggerManager, self).__init__(editor)
        self.filename = None
        self.breakpoints = self.get_breakpoints()
        self.editor.sig_breakpoints_changed.connect(self.breakpoints_changed)
        self.editor.sig_filename_changed.connect(self.set_filename)

    def set_filename(self, filename):
        if filename is None:
            return
        if self.filename != filename:
            old_filename = self.filename
            self.filename = filename
            if self.breakpoints:
                save_breakpoints(old_filename, [])  # clear old breakpoints
                self.save_breakpoints()

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
            condition, valid = QInputDialog.getText(self.editor,
                                                    _('Breakpoint'),
                                                    _("Condition:"),
                                                    QLineEdit.Normal,
                                                    condition)
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
        self.editor.sig_breakpoints_changed.emit()

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
        for data in self.editor.blockuserdata_list():
            data.breakpoint = False
            # data.breakpoint_condition = None  # not necessary, but logical
        # Inform the editor that the breakpoints are changed
        self.editor.sig_breakpoints_changed.emit()
        # Inform the editor that the flags must be updated
        self.editor.sig_flags_changed.emit()

    def set_breakpoints(self, breakpoints):
        """Set breakpoints"""
        self.clear_breakpoints()
        for line_number, condition in breakpoints:
            self.toogle_breakpoint(line_number, condition)
        self.breakpoints = self.get_breakpoints()

    def update_breakpoints(self):
        """Update breakpoints"""
        self.editor.sig_breakpoints_changed.emit()

    def breakpoints_changed(self):
        """Breakpoint list has changed"""
        breakpoints = self.get_breakpoints()
        if self.breakpoints != breakpoints:
            self.breakpoints = breakpoints
            self.save_breakpoints()

    def save_breakpoints(self):
        breakpoints = repr(self.breakpoints)
        filename = to_text_string(self.filename)
        breakpoints = to_text_string(breakpoints)
        filename = osp.normpath(osp.abspath(filename))
        if breakpoints:
            breakpoints = eval(breakpoints)
        else:
            breakpoints = []
        save_breakpoints(filename, breakpoints)
        self.editor.sig_breakpoints_saved.emit()

    def load_breakpoints(self):
        self.set_breakpoints(load_breakpoints(self.filename))
