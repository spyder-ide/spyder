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
from qtconsole.rich_jupyter_widget import RichJupyterWidget

from spyder.config.base import get_conf_path
from spyder.config.manager import CONF
from spyder.py3compat import PY2
if not PY2:
    from IPython.core.inputtransformer2 import TransformerManager
else:
    from IPython.core.inputsplitter import IPythonInputSplitter


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
        self._pdb_in_loop = False
        self._previous_prompt = None
        super(DebuggingWidget, self).__init__(*args, **kwargs)
        # Adapted from qtconsole/frontend_widget.py
        # This adds 'ipdb> ' as a prompt self._highlighter recognises
        self._highlighter._ipy_prompt_re = re.compile(
            r'^(%s)?([ \t]*ipdb> |[ \t]*In \[\d+\]: |[ \t]*\ \ \ \.\.\.+: )'
            % re.escape(self.other_output_prefix))
        # List of tuples containing (code, hidden)
        self._pdb_input_queue = []
        self._pdb_input_ready = False
        self._pdb_last_cmd = ''
        self._pdb_line_num = 0
        self._pdb_history_file = PdbHistory()

        self._pdb_history = [
            line[-1] for line in self._pdb_history_file.get_tail(
                self.PDB_HIST_MAX, include_latest=True)]
        self._pdb_history_edits = {}
        self._pdb_history_index = len(self._pdb_history)

        self._tmp_reading = False

    def handle_debug_state(self, in_debug_loop):
        """Update the debug state."""
        self._pdb_in_loop = in_debug_loop
        # If debugging starts or stops, clear the input queue.
        self._pdb_input_queue = []
        self._pdb_line_num = 0

        # start/stop pdb history session
        if in_debug_loop:
            self._pdb_history_file.new_session()
        else:
            self._pdb_history_file.end_session()

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

        if not hidden:
            if line.strip():
                self._pdb_last_cmd = line

            # Print the text if it is programatically added.
            if line.strip() != self.input_buffer.strip():
                self.input_buffer = line
            self._append_plain_text('\n')
            # Save history to browse it later
            self._pdb_line_num += 1
            self.add_to_pdb_history(self._pdb_line_num, line)

            # Set executing to true and save the input buffer
            self._input_buffer_executing = self.input_buffer
            self._executing = True

            # Disable the console
            self._tmp_reading = False
            self._finalize_input_request()
            hidden = True

        if self._pdb_input_ready:
            # Print the string to the console
            self._pdb_input_ready = False
            return self.kernel_client.input(line)

        self._pdb_input_queue.append((line, hidden))

    def handle_get_pdb_settings(self):
        """Get pdb settings"""
        return {
            "breakpoints": CONF.get('run', 'breakpoints', {}),
            "pdb_ignore_lib": CONF.get(
                'run', 'pdb_ignore_lib', False),
            }

    def set_spyder_breakpoints(self):
        """Set Spyder breakpoints into a debugging session"""
        self.call_kernel(interrupt=True).set_breakpoints(
            CONF.get('run', 'breakpoints', {}))

    def set_pdb_ignore_lib(self):
        """Set pdb_ignore_lib into a debugging session"""
        self.call_kernel(interrupt=True).set_pdb_ignore_lib(
            CONF.get('run', 'pdb_ignore_lib', False))

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

    def in_debug_loop(self):
        """Check if we are debugging."""
        return self._pdb_in_loop

    def is_waiting_pdb_input(self):
        """Check if we are waiting a pdb input."""
        # If the comm is not open, self._pdb_in_loop can not be set
        return ((self.in_debug_loop() or not self.spyder_kernel_comm.is_open())
                and self._previous_prompt is not None
                and self._previous_prompt[0] == 'ipdb> ')

    def add_to_pdb_history(self, line_num, line):
        """Add command to history"""
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
        is_pdb_cmd = "do_" + cmd in dir(pdb.Pdb)
        if cmd and (not is_pdb_cmd or len(args) > 0):
            self._pdb_history.append(line)
            self._pdb_history_index = len(self._pdb_history)
            self._pdb_history_file.store_inputs(line_num, line)

    def redefine_complete_for_dbg(self, client):
        """Redefine kernel client's complete method to work while debugging."""

        original_complete = client.complete

        def complete(code, cursor_pos=None):
            if self.is_waiting_pdb_input() and client.comm_channel:
                shell_channel = client.shell_channel
                client._shell_channel = client.comm_channel
                try:
                    return original_complete(code, cursor_pos)
                finally:
                    client._shell_channel = shell_channel
            else:
                return original_complete(code, cursor_pos)

        client.complete = complete

    # --- Private API --------------------------------------------------
    def _is_pdb_complete(self, source):
        """
        Check if the pdb input is ready to be executed.
        """
        if source and source[0] == '!':
            source = source[1:]
        if PY2:
            tm = IPythonInputSplitter()
        else:
            tm = TransformerManager()
        complete, indent = tm.check_complete(source)
        if indent is not None:
            indent = indent * ' '
        return complete != 'incomplete', indent

    # ---- Public API (overrode by us) ----------------------------
    def execute(self, source=None, hidden=False, interactive=False):
        """ Executes source or the input buffer, possibly prompting for more
        input.

        Do not use to run pdb commands. Use pdb_execute instead.
        This will add a '!' in front of the code.
        """
        if self.is_waiting_pdb_input():
            if source is None:
                if hidden:
                    # Nothing to execute
                    return
                else:
                    source = self.input_buffer
            else:
                source = '!' + source
                if not hidden:
                    self.input_buffer = source

            if interactive:
                # Add a continuation propt if not complete
                complete, indent = self._is_pdb_complete(source)
                if not complete:
                    self.do_execute(source, complete, indent)
                    return
            if hidden:
                self.pdb_execute(source, hidden)
            else:
                if self._reading_callback:
                    self._reading_callback()

            return
        if not self._executing:
            # Only execute if not executing
            return super(DebuggingWidget, self).execute(
                source, hidden, interactive)

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
            self.set_pdb_echo_code(True)
            self.pdb_execute(line)

    def set_pdb_echo_code(self, state):
        """Choose if the code should echo in the console."""
        self.call_kernel(interrupt=True).set_pdb_echo_code(state)

    def _handle_input_request(self, msg):
        """Save history and add a %plot magic."""
        if self._hidden:
            raise RuntimeError(
                'Request for raw input during hidden execution.')

        # Make sure that all output from the SUB channel has been processed
        # before entering readline mode.
        self.kernel_client.iopub_channel.flush()

        prompt, password = msg['content']['prompt'], msg['content']['password']

        self._previous_prompt = (prompt, password)

        # Check if the prompt should be printed
        if not self.is_waiting_pdb_input():
            print_prompt = True
        else:
            # This is pdb. The prompt should be printed unless:
            # 1. The prompt is already printed (self._reading is True)
            # 2. A hidden commad is in the queue
            print_prompt = (not self._reading
                            and (len(self._pdb_input_queue) == 0
                                 or not self._pdb_input_queue[0][1]))

        if print_prompt:
            # Reset reading in case it was interrupted
            self._reading = False
            self._readline(prompt=prompt, callback=self._readline_callback,
                           password=password)
            if self.is_waiting_pdb_input():
                self._executing = False
                self._highlighter.highlighting_on = True

        if self.is_waiting_pdb_input():
            self._pdb_input_ready = True

        # While the widget thinks only one input is going on,
        # other functions can be sending messages to the kernel.
        # This must be properly processed to avoid dropping messages.
        # If the kernel was not ready, the messages are queued.
        if self.is_waiting_pdb_input() and len(self._pdb_input_queue) > 0:
            args = self._pdb_input_queue.pop(0)
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
        if self.is_waiting_pdb_input():
            self._control.current_prompt_pos = self._prompt_pos
            # Pretend this is a regular prompt
            self._tmp_reading = self._reading
            self._reading = False
            try:
                ret = super(DebuggingWidget,
                            self)._event_filter_console_keypress(event)
                return ret
            finally:
                self._reading = self._tmp_reading
        else:
            return super(DebuggingWidget,
                         self)._event_filter_console_keypress(event)

    def _register_is_complete_callback(self, source, callback):
        """Call the callback with the result of is_complete."""
        # Add a continuation propt if not complete
        if self.is_waiting_pdb_input():
            complete, indent = self._is_pdb_complete(source)
            callback(complete, indent)
        else:
            return super(DebuggingWidget, self)._register_is_complete_callback(
                source, callback)

    @property
    def _history(self):
        """Get history."""
        if self.is_waiting_pdb_input():
            return self._pdb_history
        else:
            return self.__history

    @_history.setter
    def _history(self, history):
        """Set history."""
        if self.is_waiting_pdb_input():
            self._pdb_history = history
        else:
            self.__history = history

    @property
    def _history_edits(self):
        """Get edited history."""
        if self.is_waiting_pdb_input():
            return self._pdb_history_edits
        else:
            return self.__history_edits

    @_history_edits.setter
    def _history_edits(self, history_edits):
        """Set edited history."""
        if self.is_waiting_pdb_input():
            self._pdb_history_edits = history_edits
        else:
            self.__history_edits = history_edits

    @property
    def _history_index(self):
        """Get history index."""
        if self.is_waiting_pdb_input():
            return self._pdb_history_index
        else:
            return self.__history_index

    @_history_index.setter
    def _history_index(self, history_index):
        """Set history index."""
        if self.is_waiting_pdb_input():
            self._pdb_history_index = history_index
        else:
            self.__history_index = history_index
