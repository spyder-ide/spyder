# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""
Widget that handles communications between a console in debugging
mode and Spyder
"""

import re
import pdb

from IPython.core.history import HistoryManager
from qtpy.QtCore import Qt
from qtconsole.rich_jupyter_widget import RichJupyterWidget

from spyder.config.base import get_conf_path
from spyder.config.manager import CONF
from spyder.widgets.mixins import BrowseHistory


class PdbHistory(HistoryManager):

    def _get_hist_file_name(self, profile=None):
        """
        Get default pdb history file name.

        The profile parameter is ignored, but must exist for compatibility with
        the parent class.
        """
        return get_conf_path('pdb_history.sqlite')


class DebuggingWidget(RichJupyterWidget):
    """
    Widget with the necessary attributes and methods to handle
    communications between a console in debugging mode and
    Spyder
    """
    PDB_HIST_MAX = 400

    def __init__(self, *args, **kwargs):
        super(DebuggingWidget, self).__init__(*args, **kwargs)
        # Adapted from qtconsole/frontend_widget.py
        # This adds 'ipdb> ' as a prompt self._highlighter recognises
        self._highlighter._ipy_prompt_re = re.compile(
            r'^(%s)?([ \t]*ipdb> |[ \t]*In \[\d+\]: |[ \t]*\ \ \ \.\.\.+: )'
            % re.escape(self.other_output_prefix))
        self._previous_prompt = None
        self._pdb_input_queue = []
        self._pdb_input_ready = False
        self._pdb_last_cmd = ''
        self._pdb_line_num = 0
        self._pdb_history_file = PdbHistory()
        self._pdb_history = BrowseHistory()
        self._pdb_history.history = [
            line[-1] for line in self._pdb_history_file.get_tail(
                self.PDB_HIST_MAX, include_latest=True)]
        self._pdb_in_loop = False

    def _handle_debug_state(self, in_debug_loop):
        """Update the debug state."""
        self._pdb_in_loop = in_debug_loop
        # If debugging starts or stops, clear the input queue.
        self._pdb_input_queue = []
        self._pdb_line_num = 0

    def _pdb_update(self):
        """
        Update by sending an input to pdb.
        """
        if self._pdb_in_loop:
            cmd = (u"!get_ipython().kernel.frontend_comm" +
                   ".remote_call(blocking=True).pong()")
            self.pdb_execute(cmd, hidden=True)

    # --- Public API --------------------------------------------------
    def pdb_execute(self, line, hidden=False):
        """Send line to the pdb kernel if possible."""
        if not line.strip():
            # Must get the last genuine command
            line = self._pdb_last_cmd

        if not self.is_waiting_pdb_input():
            # We can't execute this if we are not waiting for pdb input
            if self.in_debug_loop():
                self._pdb_input_queue.append((line, hidden))
            return

        if self._pdb_input_ready:
            # Print the string to the console
            if not hidden:
                if line.strip():
                    self._pdb_last_cmd = line

                # Print the text if it is programatically added.
                if line.strip() != self.input_buffer.strip():
                    self._append_plain_text(line + '\n')

                # Save history to browse it later
                self._pdb_line_num += 1
                self.add_to_pdb_history(self._pdb_line_num, line)

                # Set executing to true and save the input buffer
                self._input_buffer_executing = self.input_buffer
                self._executing = True

                self._finalize_input_request()

            self._pdb_input_ready = False
            return self.kernel_client.input(line)

        self._pdb_input_queue.append((line, hidden))

    def get_spyder_breakpoints(self):
        """Get spyder breakpoints."""
        return CONF.get('run', 'breakpoints', {})

    def set_spyder_breakpoints(self, force=False):
        """Set Spyder breakpoints into a debugging session"""
        self.call_kernel(interrupt=True).set_breakpoints(
            self.get_spyder_breakpoints())

    def dbg_exec_magic(self, magic, args=''):
        """Run an IPython magic while debugging."""
        if not self.is_waiting_pdb_input():
            return
        code = "!get_ipython().kernel.shell.run_line_magic('{}', '{}')".format(
                    magic, args)
        self.pdb_execute(code, hidden=True)

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
            self.set_namespace_view(pdb_state['namespace_view'])

        if 'var_properties' in pdb_state:
            self.set_var_properties(pdb_state['var_properties'])

    def set_pdb_state(self, pdb_state):
        """Set current pdb state."""
        if pdb_state is not None and isinstance(pdb_state, dict):
            self.refresh_from_pdb(pdb_state)

    def pdb_continue(self):
        """Continue debugging."""
        # Run Pdb continue to get to the first breakpoint
        # Fixes 2034
        self.pdb_execute('continue')

    # ---- Private API (overrode by us) ----------------------------
    def _readline_callback(self, line):
        """Callback used when the user inputs text in stdin."""
        if not self.is_waiting_pdb_input():
            # This is a regular input call
            self._finalize_input_request()
            return self.kernel_client.input(line)

        # This is the Spyder addition: add a %plot magic to display
        # plots while debugging
        if line.startswith('%plot '):
            line = line.split()[-1]
            line = "__spy_code__ = get_ipython().run_cell('%s')" % line
            self.pdb_execute(line, hidden=True)
        else:
            self.pdb_execute(line)

    def _handle_input_request(self, msg):
        """Save history and add a %plot magic."""
        if self._hidden:
            raise RuntimeError(
                'Request for raw input during hidden execution.')

        # Make sure that all output from the SUB channel has been processed
        # before entering readline mode.
        self.kernel_client.iopub_channel.flush()

        prompt, password = msg['content']['prompt'], msg['content']['password']

        # Check if this is a duplicate that we shouldn't reprint.
        # This can happen when sending commands to pdb from the frontend.
        print_prompt = (not self._reading
                        or not (prompt, password) == self._previous_prompt)

        self._previous_prompt = (prompt, password)

        if print_prompt:
            # Reset reading in case it was interrupted
            self._reading = False
            self._readline(prompt=prompt, callback=self._readline_callback,
                           password=password)

        if self.is_waiting_pdb_input():
            self._highlighter.highlighting_on = True
            self._pdb_input_ready = True
            self._executing = False

        # While the widget thinks only one input is going on,
        # other functions can be sending messages to the kernel.
        # This must be properly processed to avoid dropping messages.
        # If the kernel was not ready, the messages are queued.
        if self.is_waiting_pdb_input() and len(self._pdb_input_queue) > 0:
            args = self._pdb_input_queue[0]
            del self._pdb_input_queue[0]
            self.pdb_execute(*args)
            return

    def _show_prompt(self, prompt=None, html=False, newline=True):
        """
        Writes a new prompt at the end of the buffer.
        """
        if prompt in ['(Pdb) ', 'ipdb> ']:
            html = True
            prompt = '<span class="in-prompt">%s</span>' % prompt
        super(DebuggingWidget, self)._show_prompt(prompt, html, newline)

    def _event_filter_console_keypress(self, event):
        """Handle Key_Up/Key_Down while debugging."""
        key = event.key()
        if self.is_waiting_pdb_input():
            self._control.current_prompt_pos = self._prompt_pos
            if key == Qt.Key_Up:
                self._pdb_browse_history(backward=True)
                return True
            elif key == Qt.Key_Down:
                self._pdb_browse_history(backward=False)
                return True
            elif key in (Qt.Key_Return, Qt.Key_Enter):
                self._pdb_history.reset_search_pos()
            else:
                self._pdb_history.hist_wholeline = False
            return super(DebuggingWidget,
                         self)._event_filter_console_keypress(event)
        else:
            return super(DebuggingWidget,
                         self)._event_filter_console_keypress(event)

    def _pdb_browse_history(self, backward):
        """Browse history"""
        control = self._control
        # Make sure the cursor is not before the prompt
        if control.get_position('cursor') < control.current_prompt_pos:
            control.set_cursor_position(control.current_prompt_pos)
        old_pos = control.get_position('cursor')
        line = self._get_input_buffer()
        cursor_pos = self._get_input_buffer_cursor_pos()
        text, move_cursor = self._pdb_history.browse_history(
            line, cursor_pos, backward)
        if text is not None:
            control.remove_text(control.current_prompt_pos, 'eof')
            self._insert_plain_text_into_buffer(control.textCursor(), text)
            if not move_cursor:
                control.set_cursor_position(old_pos)

    def in_debug_loop(self):
        """Check if we are debugging."""
        return self._pdb_in_loop

    def is_waiting_pdb_input(self):
        """Check if we are waiting a pdb input."""
        return (self.in_debug_loop() and self._previous_prompt is not None
                and self._previous_prompt[0] == 'ipdb> ')

    def add_to_pdb_history(self, line_num, line):
        """Add command to history"""
        self._pdb_history.histidx = None
        if not line:
            return
        line = line.strip()

        # If repeated line
        history = self._pdb_history.history
        if len(history) > 0 and history[-1] == line:
            return

        cmd = line.split(" ")[0]
        args = line.split(" ")[1:]
        is_pdb_cmd = "do_" + cmd in dir(pdb.Pdb)
        if cmd and (not is_pdb_cmd or len(args) > 0):
            self._pdb_history.history.append(line)
            self._pdb_history_file.store_inputs(line_num, line)
