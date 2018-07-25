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
import pdb
import pickle

from qtpy.QtCore import Qt
from qtconsole.rich_jupyter_widget import RichJupyterWidget

from spyder.config.base import PICKLE_PROTOCOL
from spyder.config.main import CONF
from spyder.py3compat import to_text_string


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

    def set_spyder_breakpoints(self, force=False):
        """Set Spyder breakpoints into a debugging session"""
        if self._reading or force:
            breakpoints_dict = CONF.get('run', 'breakpoints', {})

            # We need to enclose pickled values in a list to be able to
            # send them to the kernel in Python 2
            serialiazed_breakpoints = [pickle.dumps(breakpoints_dict,
                                                    protocol=PICKLE_PROTOCOL)]
            breakpoints = to_text_string(serialiazed_breakpoints)

            cmd = u"!get_ipython().kernel._set_spyder_breakpoints({})"
            self.kernel_client.input(cmd.format(breakpoints))

    def dbg_exec_magic(self, magic, args=''):
        """Run an IPython magic while debugging."""
        code = "!get_ipython().kernel.shell.run_line_magic('{}', '{}')".format(
                    magic, args)
        self.kernel_client.input(code)

    def refresh_from_pdb(self, pdb_state):
        """
        Refresh Variable Explorer and Editor from a Pdb session,
        after running any pdb command.

        See publish_pdb_state and notify_spyder in spyder_kernels
        """
        if 'step' in pdb_state and 'fname' in pdb_state['step']:
            fname = pdb_state['step']['fname']
            lineno = pdb_state['step']['lineno']
            self.sig_pdb_step.emit(fname, lineno)

        if 'namespace_view' in pdb_state:
            self.sig_namespace_view.emit(ast.literal_eval(
                    pdb_state['namespace_view']))

        if 'var_properties' in pdb_state:
            self.sig_var_properties.emit(ast.literal_eval(
                    pdb_state['var_properties']))

    # ---- Private API (overrode by us) ----------------------------
    def _handle_input_request(self, msg):
        """Save history and add a %plot magic."""
        if self._hidden:
            raise RuntimeError('Request for raw input during hidden execution.')

        # Make sure that all output from the SUB channel has been processed
        # before entering readline mode.
        self.kernel_client.iopub_channel.flush()

        def callback(line):
            # Save history to browse it later
            if not (len(self._control.history) > 0
                    and self._control.history[-1] == line):
                # do not save pdb commands
                cmd = line.split(" ")[0]
                if "do_" + cmd not in dir(pdb.Pdb):
                    self._control.history.append(line)

            # This is the Spyder addition: add a %plot magic to display
            # plots while debugging
            if line.startswith('%plot '):
                line = line.split()[-1]
                code = "__spy_code__ = get_ipython().run_cell('%s')" % line
                self.kernel_client.input(code)
            else:
                self.kernel_client.input(line)
        if self._reading:
            self._reading = False
        self._readline(msg['content']['prompt'], callback=callback,
                       password=msg['content']['password'])

    def _event_filter_console_keypress(self, event):
        """Handle Key_Up/Key_Down while debugging."""
        key = event.key()
        if self._reading:
            self._control.current_prompt_pos = self._prompt_pos
            if key == Qt.Key_Up:
                self._control.browse_history(backward=True)
                return True
            elif key == Qt.Key_Down:
                self._control.browse_history(backward=False)
                return True
            elif key in (Qt.Key_Return, Qt.Key_Enter):
                self._control.reset_search_pos()
            else:
                self._control.hist_wholeline = False
            return super(DebuggingWidget,
                         self)._event_filter_console_keypress(event)
        else:
            return super(DebuggingWidget,
                         self)._event_filter_console_keypress(event)
