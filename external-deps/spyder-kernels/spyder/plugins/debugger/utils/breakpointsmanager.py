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
from qtpy.QtCore import Signal, QObject

from spyder.api.config.decorators import on_conf_change
from spyder.api.config.mixins import SpyderConfigurationObserver
from spyder.config.manager import CONF
from spyder.config.base import _
from spyder.py3compat import to_text_string
from spyder.plugins.editor.api.manager import Manager
from spyder.plugins.editor.utils.editor import BlockUserData
from spyder.plugins.debugger.panels.debuggerpanel import DebuggerPanel


def _load_all_breakpoints():
    bp_dict = CONF.get("debugger", "breakpoints", {})
    for filename in list(bp_dict.keys()):
        # Make sure we don't have the same file under different names
        new_filename = osp.normcase(filename)
        if new_filename != filename:
            bp = bp_dict.pop(filename)
            if new_filename in bp_dict:
                bp_dict[new_filename].extend(bp)
            else:
                bp_dict[new_filename] = bp
    return bp_dict


def load_breakpoints(filename):
    breakpoints = _load_all_breakpoints().get(osp.normcase(filename), [])
    if breakpoints and isinstance(breakpoints[0], int):
        # Old breakpoints format
        breakpoints = [(lineno, None) for lineno in breakpoints]
    return breakpoints


def save_breakpoints(filename, breakpoints):
    bp_dict = _load_all_breakpoints()
    bp_dict[osp.normcase(filename)] = breakpoints
    CONF.set("debugger", "breakpoints", bp_dict)


def clear_all_breakpoints():
    CONF.set("debugger", "breakpoints", {})


def clear_breakpoint(filename, lineno):
    breakpoints = load_breakpoints(filename)
    if breakpoints:
        for breakpoint in breakpoints[:]:
            if breakpoint[0] == lineno:
                breakpoints.remove(breakpoint)
        save_breakpoints(filename, breakpoints)


class BreakpointsManager(Manager, SpyderConfigurationObserver, QObject):
    """
    Manages adding/removing breakpoint from the editor.
    """
    CONF_SECTION = 'debugger'

    sig_breakpoints_saved = Signal()
    sig_repaint_breakpoints = Signal()

    def __init__(self, editor):
        super().__init__(editor)
        self.filename = editor.filename
        self._breakpoint_blocks = {}
        self.breakpoints = []

        # Debugger panel (Breakpoints)
        self.debugger_panel = DebuggerPanel(self)
        editor.panels.register(self.debugger_panel)
        self.debugger_panel.order_in_zone = 1
        self.update_panel_visibility()

        # Load breakpoints
        self.load_breakpoints()

        # Update breakpoints if the number of lines in the file changes
        editor.blockCountChanged.connect(self.breakpoints_changed)

    def update_pdb_state(self, state, filename, line_number):
        """
        Enable/disable debugging actions and handle pdb state change.

        Update debugger panel state.
        """
        if (
            state
            and filename
            and self.filename
            and osp.normcase(filename) == osp.normcase(self.filename)
        ):
            self.debugger_panel.start_clean()
            self.debugger_panel.set_current_line_arrow(line_number)
            return

        self.debugger_panel.stop_clean()

    def set_filename(self, filename):
        if filename is None:
            return
        if self.filename == filename:
            return
        old_filename = self.filename
        self.filename = filename
        if self.breakpoints:
            save_breakpoints(old_filename, [])  # clear old breakpoints
            self.save_breakpoints()

    def update_panel_visibility(self):
        """Update the panel visibility."""
        self.debugger_panel.setVisible(
            self.get_conf('editor_debugger_panel', default=True))

    @on_conf_change(option='editor_debugger_panel')
    def on_editor_debugger_panel_update(self, value):
        self.update_panel_visibility()

    def toogle_breakpoint(
        self, line_number=None, condition=None, edit_condition=False
    ):
        """Add/remove breakpoint."""
        if not self.editor.is_python_like():
            return
        if line_number is None:
            block = self.editor.textCursor().block()
        else:
            block = self.editor.document().findBlockByNumber(line_number - 1)
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
            condition, valid = QInputDialog.getText(
                self.editor,
                _("Breakpoint"),
                _("Condition:"),
                QLineEdit.Normal,
                condition,
            )
            if not valid:
                return
            data.breakpoint = True
            data.breakpoint_condition = str(condition) if condition else None
        if data.breakpoint:
            text = to_text_string(block.text()).strip()
            if len(text) == 0 or text.startswith(("#", '"', "'")):
                data.breakpoint = False
            else:
                self._breakpoint_blocks[id(block)] = block
        block.setUserData(data)
        self.editor.sig_flags_changed.emit()
        self.breakpoints_changed()

    def get_breakpoints(self):
        """Get breakpoints"""
        breakpoints = []
        pruned_breakpoint_blocks = {}
        for block_id in self._breakpoint_blocks:
            block = self._breakpoint_blocks[block_id]
            if block.isValid():
                data = block.userData()
                if data and data.breakpoint:
                    pruned_breakpoint_blocks[block_id] = block
                    line_number = block.blockNumber() + 1
                    breakpoints.append(
                        (line_number, data.breakpoint_condition)
                    )
        self._breakpoint_blocks = pruned_breakpoint_blocks
        return breakpoints

    def clear_breakpoints(self):
        """Clear breakpoints"""
        self.breakpoints = []
        for data in self.editor.blockuserdata_list():
            data.breakpoint = False
            # data.breakpoint_condition = None  # not necessary, but logical
        self._breakpoint_blocks = {}
        # Inform the editor that the breakpoints are changed
        self.breakpoints_changed()
        # Inform the editor that the flags must be updated
        self.editor.sig_flags_changed.emit()

    def set_breakpoints(self, breakpoints):
        """Set breakpoints"""
        self.clear_breakpoints()
        for line_number, condition in breakpoints:
            self.toogle_breakpoint(line_number, condition)
        self.breakpoints = self.get_breakpoints()

    def breakpoints_changed(self):
        """Breakpoint list has changed"""
        breakpoints = self.get_breakpoints()
        if self.breakpoints != breakpoints:
            self.breakpoints = breakpoints
            self.save_breakpoints()
            self.sig_repaint_breakpoints.emit()

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
        self.sig_breakpoints_saved.emit()

    def load_breakpoints(self):
        self.set_breakpoints(load_breakpoints(self.filename))
