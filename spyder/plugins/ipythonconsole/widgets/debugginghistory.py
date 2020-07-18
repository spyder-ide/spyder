# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""
Widget that manages a history file for the debugging.
"""

import pdb

from qtconsole.rich_jupyter_widget import RichJupyterWidget
from IPython.core.history import HistoryManager

from spyder.config.base import get_conf_path


class PdbHistory(HistoryManager):

    def _get_hist_file_name(self, profile=None):
        """
        Get default pdb history file name.

        The profile parameter is ignored, but must exist for compatibility with
        the parent class.
        """
        return get_conf_path('pdb_history.sqlite')


class DebuggingHistoryWidget(RichJupyterWidget):
    """
    Widget with the necessary attributes and methods to handle
    communications between a console in debugging mode and
    Spyder
    """
    PDB_HIST_MAX = 400

    def __init__(self, *args, **kwargs):
        # History
        self._pdb_history_input_number = 0  # Input number for current session
        self._pdb_history_file = PdbHistory()
        self._pdb_history = [
            line[-1] for line in self._pdb_history_file.get_tail(
                self.PDB_HIST_MAX, include_latest=True)]
        self._pdb_history_edits = {}  # Temporary history edits
        self._pdb_history_index = len(self._pdb_history)
        # super init
        super(DebuggingHistoryWidget, self).__init__(*args, **kwargs)

    # --- Public API --------------------------------------------------
    def shutdown(self):
        """Shutdown the widget"""
        try:
            self._pdb_history_file.save_thread.stop()
            self._pdb_history_file.db.close()
        except AttributeError:
            pass

    def new_history_session(self):
        """Start a new history session."""
        self._pdb_history_input_number = 0
        self._pdb_history_file.new_session()

    def end_history_session(self):
        """End an history session."""
        self._pdb_history_input_number = 0
        self._pdb_history_file.end_session()

    def add_to_pdb_history(self, line):
        """Add command to history"""
        self._pdb_history_input_number += 1
        line_num = self._pdb_history_input_number
        self._pdb_history_index = len(self._pdb_history)
        self._pdb_history_edits = {}
        line = line.rstrip()
        if not line:
            return

        # If repeated line
        history = self._pdb_history
        if len(history) > 0 and history[-1] == line:
            return

        cmd = line.split(" ")[0]
        args = line.split(" ")[1:]
        is_pdb_cmd = (
            cmd.strip() and cmd[0] == '!' and "do_" + cmd[1:] in dir(pdb.Pdb))
        if cmd and (not is_pdb_cmd or len(args) > 0):
            self._pdb_history.append(line)
            self._pdb_history_index = len(self._pdb_history)
            self._pdb_history_file.store_inputs(line_num, line)

    def is_debugging(self):
        """Check if we are debugging"""
        # This is implemented in subclass
        raise NotImplementedError

    # --- Private API (overrode by us) --------------------------------
    @property
    def _history(self):
        """Get history."""
        if self.is_debugging():
            return self._pdb_history
        else:
            return self.__history

    @_history.setter
    def _history(self, history):
        """Set history."""
        if self.is_debugging():
            self._pdb_history = history
        else:
            self.__history = history

    @property
    def _history_edits(self):
        """Get edited history."""
        if self.is_debugging():
            return self._pdb_history_edits
        else:
            return self.__history_edits

    @_history_edits.setter
    def _history_edits(self, history_edits):
        """Set edited history."""
        if self.is_debugging():
            self._pdb_history_edits = history_edits
        else:
            self.__history_edits = history_edits

    @property
    def _history_index(self):
        """Get history index."""
        if self.is_debugging():
            return self._pdb_history_index
        else:
            return self.__history_index

    @_history_index.setter
    def _history_index(self, history_index):
        """Set history index."""
        if self.is_debugging():
            self._pdb_history_index = history_index
        else:
            self.__history_index = history_index
