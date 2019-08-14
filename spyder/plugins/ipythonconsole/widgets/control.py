# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""Control widgets used by ShellWidget"""
import pdb

from qtpy.QtCore import Qt, Signal
from qtpy.QtWidgets import QTextEdit
from IPython.core.history import HistoryManager

from spyder.config.base import get_conf_path
from spyder.utils.qthelpers import restore_keyevent
from spyder.widgets.calltip import CallTipWidget
from spyder.widgets.mixins import (BaseEditMixin, GetHelpMixin,
                                   TracebackLinksMixin,
                                   BrowseHistoryMixin)


class PdbHistory(HistoryManager):

    def _get_hist_file_name(self, profile=None):
        """
        Get default pdb history file name.

        The profile parameter is ignored, but must exist for compatibility with
        the parent class.
        """

        return get_conf_path('pdb_history.sqlite')


class ControlWidget(TracebackLinksMixin, GetHelpMixin, BrowseHistoryMixin,
                    QTextEdit, BaseEditMixin):
    """
    Subclass of QTextEdit with features from Spyder's mixins to use as the
    control widget for IPython widgets
    """
    QT_CLASS = QTextEdit
    visibility_changed = Signal(bool)
    go_to_error = Signal(str)
    focus_changed = Signal()
    PDB_HIST_MAX = 400

    def __init__(self, parent=None):
        QTextEdit.__init__(self, parent)
        BaseEditMixin.__init__(self)
        TracebackLinksMixin.__init__(self)
        GetHelpMixin.__init__(self)
        BrowseHistoryMixin.__init__(self)

        self.pdb_history_file = PdbHistory()
        self.history = [line[-1]
                        for line in self.pdb_history_file.get_tail(
                            self.PDB_HIST_MAX, include_latest=True)]

        self.calltip_widget = CallTipWidget(self, hide_timer_on=False)
        self.found_results = []

        # To not use Spyder calltips obtained through the monitor
        self.calltips = False

    def showEvent(self, event):
        """Reimplement Qt Method"""
        self.visibility_changed.emit(True)

    def _key_paren_left(self, text):
        """ Action for '(' """
        self.current_prompt_pos = self.parentWidget()._prompt_pos
        if self.get_current_line_to_cursor():
            last_obj = self.get_last_obj()
            if last_obj and not last_obj.isdigit():
                self.show_object_info(last_obj)
        self.insert_text(text)

    def keyPressEvent(self, event):
        """Reimplement Qt Method - Basic keypress event handler"""
        event, text, key, ctrl, shift = restore_keyevent(event)
        if key == Qt.Key_ParenLeft and not self.has_selected_text() \
          and self.help_enabled and not self.parent()._reading:
            self._key_paren_left(text)
        else:
            # Let the parent widget handle the key press event
            QTextEdit.keyPressEvent(self, event)

    def focusInEvent(self, event):
        """Reimplement Qt method to send focus change notification"""
        self.focus_changed.emit()
        return super(ControlWidget, self).focusInEvent(event)

    def focusOutEvent(self, event):
        """Reimplement Qt method to send focus change notification"""
        self.focus_changed.emit()
        return super(ControlWidget, self).focusOutEvent(event)

    def add_to_pdb_history(self, line_num, line):
        """Add command to history"""
        self.histidx = None
        if not line:
            return
        line = line.strip()

        # If repeated line
        if len(self.history) > 0 and self.history[-1] == line:
            return

        cmd = line.split(" ")[0]
        args = line.split(" ")[1:]
        is_pdb_cmd = "do_" + cmd in dir(pdb.Pdb)
        if cmd and (not is_pdb_cmd or len(args) > 0):
            self.history.append(line)
            self.pdb_history_file.store_inputs(line_num, line)


class PageControlWidget(QTextEdit, BaseEditMixin):
    """
    Subclass of QTextEdit with features from Spyder's mixins.BaseEditMixin to
    use as the paging widget for IPython widgets
    """
    QT_CLASS = QTextEdit
    visibility_changed = Signal(bool)
    show_find_widget = Signal()
    focus_changed = Signal()

    def __init__(self, parent=None):
        QTextEdit.__init__(self, parent)
        BaseEditMixin.__init__(self)
        self.found_results = []

    def showEvent(self, event):
        """Reimplement Qt Method"""
        self.visibility_changed.emit(True)

    def keyPressEvent(self, event):
        """Reimplement Qt Method - Basic keypress event handler"""
        event, text, key, ctrl, shift = restore_keyevent(event)

        if key == Qt.Key_Slash and self.isVisible():
            self.show_find_widget.emit()

    def focusInEvent(self, event):
        """Reimplement Qt method to send focus change notification"""
        self.focus_changed.emit()
        return super(PageControlWidget, self).focusInEvent(event)

    def focusOutEvent(self, event):
        """Reimplement Qt method to send focus change notification"""
        self.focus_changed.emit()
        return super(PageControlWidget, self).focusOutEvent(event)
