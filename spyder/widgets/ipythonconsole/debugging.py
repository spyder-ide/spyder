# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""
Widget that handles communications between a console in debugging
mode and Spyder
"""

import ast
import os.path as osp
import pickle

from qtpy.QtCore import QEventLoop

from qtconsole.rich_jupyter_widget import RichJupyterWidget

from spyder.py3compat import to_text_string
from spyder.utils.programs import TEMPDIR


class DebuggingWidget(RichJupyterWidget):
    """
    Widget with the necessary attributes and methods to handle
    communications between a console in debugging mode and
    Spyder
    """

    _pdb_state = {}

    # --- Public API --------------------------------------------------
    def write_to_stdin(self, line):
        """Send raw characters to the IPython kernel through stdin"""
        self.kernel_client.input(line)

    def set_spyder_breakpoints(self):
        """Set Spyder breakpoints into a debugging session"""
        if self._reading:
            self.kernel_client.input(
                "!get_ipython().kernel._set_spyder_breakpoints()")

    def dbg_exec_magic(self, magic, args=''):
        """Run an IPython magic while debugging."""
        code = "!get_ipython().kernel.shell.run_line_magic('{}', '{}')".format(
                    magic, args)
        self.kernel_client.input(code)

    # ---- Private API (defined by us) -------------------------------
    def _load_pdb_state(self):
        """
        Load Pdb state saved to disk after running any pdb command.

        See dump_pdb_state in utils/ipython/spyder_kernel.py and
        notify_spyder in utils/site/sitecustomize.py and
        """
        filename = osp.join(TEMPDIR, self.ipyclient.kernel_id +
                            '-pdb_state.pkl')
        try:
            with open(filename, 'rb') as f:
                self._pdb_state = pickle.load(f)
        except IOError:
            pass

    def _refresh_from_pdb(self):
        """Refresh Variable Explorer and Editor from a Pdb session."""
        self._load_pdb_state()

        if 'step' in self._pdb_state and 'fname' in self._pdb_state['step']:
            fname = self._pdb_state['step']['fname']
            lineno = self._pdb_state['step']['lineno']
            self.sig_pdb_step.emit(fname, lineno)

        if 'namespace_view' in self._pdb_state:
            self.sig_namespace_view.emit(self._pdb_state['namespace_view'])

        if 'var_properties' in self._pdb_state:
            self.sig_var_properties.emit(self._pdb_state['var_properties'])

    # ---- Private API (overrode by us) -------------------------------
    def _handle_input_request(self, msg):
        """
        Reimplemented to refresh the Variable Explorer and the Editor
        after every Pdb command.
        """
        super(DebuggingWidget, self)._handle_input_request(msg)
        self._refresh_from_pdb()
