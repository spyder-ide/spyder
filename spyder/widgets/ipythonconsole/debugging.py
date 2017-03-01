# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""
Widget that handles communications between a console in debugging
mode and Spyder
"""

from qtconsole.rich_jupyter_widget import RichJupyterWidget


class DebuggingWidget(RichJupyterWidget):
    """
    Widget with the necessary attributes and methods to handle
    communications between a console in debugging mode and
    Spyder
    """

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

    def refresh_from_pdb(self, pdb_state):
        """
        Refresh Variable Explorer and Editor from a Pdb session,
        after running any pdb command.

        See publish_pdb_state in utils/ipython/spyder_kernel.py and
        notify_spyder in utils/site/sitecustomize.py and
        """
        if 'step' in pdb_state and 'fname' in pdb_state['step']:
            fname = pdb_state['step']['fname']
            lineno = pdb_state['step']['lineno']
            self.sig_pdb_step.emit(fname, lineno)

        if 'namespace_view' in pdb_state:
            self.sig_namespace_view.emit(pdb_state['namespace_view'])

        if 'var_properties' in pdb_state:
            self.sig_var_properties.emit(pdb_state['var_properties'])
