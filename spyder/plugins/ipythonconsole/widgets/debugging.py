# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""
Widget that handles communications between a console in debugging
mode and Spyder
"""

import pdb
import re

from IPython.core.history import HistoryManager
from IPython import __version__ as ipy_version
from IPython.core.inputtransformer2 import TransformerManager
from IPython.lib.lexers import IPythonLexer, IPython3Lexer
from pygments.lexer import bygroups
from pygments.token import Keyword, Operator, Text
from pygments.util import ClassNotFound
from qtconsole.rich_jupyter_widget import RichJupyterWidget
from qtpy.QtCore import Qt
from qtpy.QtGui import QTextCursor

from spyder.config.base import _, get_conf_path
from spyder.config.manager import CONF


class SpyderIPy3Lexer(IPython3Lexer):
    # Detect !cmd command and highlight them
    tokens = IPython3Lexer.tokens
    tokens['root'].insert(
        0, (r'(!)(\w+)(.*\n)', bygroups(Operator, Keyword, Text)))


class SpyderIPy2Lexer(IPythonLexer):
    tokens = IPython3Lexer.tokens
    tokens['root'].insert(
        0, (r'(!)(\w+)(.*\n)', bygroups(Operator, Keyword, Text)))


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
    Widget with the necessary attributes and methods to override the pdb
    history mechanism while debugging.
    """
    PDB_HIST_MAX = 400

    def __init__(self, *args, **kwargs):
        # History
        self._pdb_history_input_number = 0  # Input number for current session
        self._saved_pdb_history_input_number = []  # for recursive debugging
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
                cmd.strip() and cmd[0] != '!' and "do_" + cmd in dir(pdb.Pdb))
        if self.is_pdb_using_exclamantion_mark():
            is_pdb_cmd = is_pdb_cmd or (
                cmd.strip() and cmd[0] == '!'
                and "do_" + cmd[1:] in dir(pdb.Pdb))

        if cmd and (not is_pdb_cmd or len(args) > 0):
            self._pdb_history.append(line)
            self._pdb_history_index = len(self._pdb_history)
            self._pdb_history_file.store_inputs(line_num, line)

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


class DebuggingWidget(DebuggingHistoryWidget):
    """
    Widget with the necessary attributes and methods to handle
    communications between a console in debugging mode and
    Spyder
    """

    def __init__(self, *args, **kwargs):
        # Communication state
        self._pdb_in_loop = 0  # NUmber of debbuging loop we are in
        self._pdb_input_ready = False  # Can we send a command now
        self._waiting_pdb_input = False  # Are we waiting on the user
        # Other state
        self._pdb_prompt = (None, None)  # prompt, password
        self._pdb_last_cmd = ''  # last command sent to pdb
        self._pdb_frame_loc = (None, None)  # fname, lineno
        # Command queue
        self._pdb_input_queue = []  # List of (code, hidden, echo_stack_entry)
        # Temporary flags
        self._tmp_reading = False
        # super init
        super(DebuggingWidget, self).__init__(*args, **kwargs)

    # --- Public API --------------------------------------------------

    def will_close(self, externally_managed):
        """
        Close the save thread and database file.
        """
        try:
            self._pdb_history_file.save_thread.stop()
        except AttributeError:
            pass
        try:
            self._pdb_history_file.db.close()
        except AttributeError:
            pass

    # --- Comm API --------------------------------------------------

    def set_debug_state(self, is_debugging):
        """Update the debug state."""
        if is_debugging:
            # Start debugging
            if self._pdb_in_loop > 0:
                # Recursive debugging
                self._saved_pdb_history_input_number.append(
                    self._pdb_history_input_number)
                self.end_history_session()
            self.new_history_session()
            self._pdb_in_loop += 1
        elif self._pdb_in_loop > 0:
            # Stop debugging
            self._pdb_in_loop -= 1
            self.end_history_session()
            if self._pdb_in_loop > 0:
                # Still debugging
                self.new_history_session()
                self._pdb_history_input_number = (
                    self._saved_pdb_history_input_number.pop())

        # If debugging starts or stops, clear the input queue.
        self._pdb_input_queue = []
        self._pdb_frame_loc = (None, None)

    def _pdb_cmd_prefix(self):
        """Return the command prefix"""
        prefix = ''
        if (self.spyder_kernel_comm.is_open() and
                self.is_pdb_using_exclamantion_mark()):
            prefix = '!'
        return prefix

    def pdb_execute_command(self, command):
        """
        Execute a pdb command
        """
        self.pdb_execute(
            self._pdb_cmd_prefix() + command, hidden=False,
            echo_stack_entry=False, add_history=False)

    def _handle_input_request(self, msg):
        """Process an input request."""
        if (not self.spyder_kernel_comm.is_open() and
                msg['content']['prompt'] == "ipdb> "):
            # Check if we can guess a path from the shell content:
            self._flush_pending_stream()
            cursor = self._get_end_cursor()
            cursor.setPosition(self._prompt_pos, QTextCursor.KeepAnchor)
            text = cursor.selection().toPlainText()
            match = re.search(r"> (.*\.py)\((\d+)\)", text)
            if match:
                fname, lineno = match.groups()
                self.sig_pdb_step.emit(fname, int(lineno))
        return super(DebuggingWidget, self)._handle_input_request(msg)

    def pdb_execute(self, line, hidden=False, echo_stack_entry=True,
                    add_history=True):
        """
        Send line to the pdb kernel if possible.

        Parameters
        ----------
        line: str
            the line to execute

        hidden: bool
            If the line should be hidden

        echo_stack_entry: bool
            If not hidden, if the stack entry should be printed

        add_history: bool
            If not hidden, wether the line should be added to history
        """
        # Send line to input if no comm
        if not self.spyder_kernel_comm.is_open():
            if not hidden:
                self._append_plain_text(line + '\n')
            self._finalize_input_request()
            self.kernel_client.input(line)
            return

        if not self.is_debugging():
            return

        if not line.strip():
            # Must get the last genuine command
            line = self._pdb_last_cmd

        if hidden:
            # Don't show stack entry if hidden
            echo_stack_entry = False
        else:
            if not self.is_waiting_pdb_input():
                # We can't execute this if we are not waiting for pdb input
                self._pdb_input_queue.append(
                    (line, hidden, echo_stack_entry, add_history))
                return

            if line.strip():
                self._pdb_last_cmd = line

            # Print the text if it is programatically added.
            if line.strip() != self.input_buffer.strip():
                self.input_buffer = line
            self._append_plain_text('\n')

            if add_history:
                # Save history to browse it later
                self.add_to_pdb_history(line)

            # Set executing to true and save the input buffer
            self._input_buffer_executing = self.input_buffer
            self._executing = True
            self._waiting_pdb_input = False

            # Disable the console
            self._tmp_reading = False
            self._finalize_input_request()
            hidden = True

            # Emit executing
            self.executing.emit(line)
            self.sig_pdb_state.emit(
                False, self.get_pdb_last_step())

        if self._pdb_input_ready:
            # Print the string to the console
            self._pdb_input_ready = False
            return self.call_kernel(interrupt=True).pdb_input_reply(
                line, echo_stack_entry=echo_stack_entry)

        self._pdb_input_queue.append(
            (line, hidden, echo_stack_entry, add_history))

    def get_pdb_settings(self):
        """Get pdb settings"""
        return {
            "breakpoints": CONF.get('run', 'breakpoints', {}),
            "pdb_ignore_lib": CONF.get('ipython_console', 'pdb_ignore_lib'),
            "pdb_execute_events": CONF.get(
                'ipython_console', 'pdb_execute_events'),
            "pdb_use_exclamation_mark": self.is_pdb_using_exclamantion_mark(),
            "pdb_stop_first_line": CONF.get(
                'ipython_console', 'pdb_stop_first_line'),
        }

    # --- To Sort --------------------------------------------------
    def stop_debugging(self):
        """Stop debugging."""
        if (self.spyder_kernel_comm.is_open() and
                not self.is_waiting_pdb_input()):
            self.interrupt_kernel()
        self.pdb_execute_command("exit")

    def set_spyder_breakpoints(self):
        """Set Spyder breakpoints into a debugging session"""
        self.call_kernel(interrupt=True).set_breakpoints(
            CONF.get('run', 'breakpoints', {}))

    def set_pdb_ignore_lib(self, pdb_ignore_lib):
        """Set pdb_ignore_lib into a debugging session"""
        self.call_kernel(interrupt=True).set_pdb_ignore_lib(
            pdb_ignore_lib)

    def set_pdb_execute_events(self, pdb_execute_events):
        """Set pdb_execute_events into a debugging session"""
        self.call_kernel(interrupt=True).set_pdb_execute_events(
            pdb_execute_events)

    def set_pdb_use_exclamation_mark(self, pdb_use_exclamation_mark):
        """Set pdb_use_exclamation_mark into a debugging session"""
        self.call_kernel(interrupt=True).set_pdb_use_exclamation_mark(
            pdb_use_exclamation_mark)

    def is_pdb_using_exclamantion_mark(self):
        return CONF.get('ipython_console', 'pdb_use_exclamation_mark')

    def do_where(self):
        """Where was called, go to the current location."""
        fname, lineno = self._pdb_frame_loc
        if fname:
            self.sig_pdb_step.emit(fname, lineno)

    def refresh_from_pdb(self, pdb_state):
        """
        Refresh Variable Explorer and Editor from a Pdb session,
        after running any pdb command.

        See publish_pdb_state and notify_spyder in spyder_kernels
        """
        if 'step' in pdb_state and 'fname' in pdb_state['step']:
            fname = pdb_state['step']['fname']
            lineno = pdb_state['step']['lineno']

            last_pdb_loc = self._pdb_frame_loc
            self._pdb_frame_loc = (fname, lineno)

            # Only step if the location changed
            if (fname, lineno) != last_pdb_loc:
                self.sig_pdb_step.emit(fname, lineno)

        if 'namespace_view' in pdb_state:
            self.set_namespace_view(pdb_state['namespace_view'])

        if 'var_properties' in pdb_state:
            self.set_var_properties(pdb_state['var_properties'])

    def set_pdb_state(self, pdb_state):
        """Set current pdb state."""
        if pdb_state is not None and isinstance(pdb_state, dict):
            self.refresh_from_pdb(pdb_state)

    def get_pdb_last_step(self):
        """Get last pdb step retrieved from a Pdb session."""
        fname, lineno = self._pdb_frame_loc
        if fname is None:
            return {}
        return {'fname': fname,
                'lineno': lineno}

    def is_debugging(self):
        """Check if we are debugging."""
        return self._pdb_in_loop > 0

    def is_waiting_pdb_input(self):
        """Check if we are waiting a pdb input."""
        # If the comm is not open, self._pdb_in_loop can not be set
        return self.is_debugging() and self._waiting_pdb_input

    # ---- Public API (overrode by us) ----------------------------
    def reset(self, clear=False):
        """
        Resets the widget to its initial state if ``clear`` parameter
        is True
        """
        super(DebuggingWidget, self).reset(clear)
        # Make sure the prompt is printed
        if clear and self.is_waiting_pdb_input():
            prompt, password = self._pdb_prompt
            self.kernel_client.iopub_channel.flush()
            self._reading = False
            self._readline(prompt=prompt, callback=self._pdb_readline_callback,
                           password=password)

    # --- Private API --------------------------------------------------
    def _current_prompt(self):
        prompt = "IPdb [{}]".format(self._pdb_history_input_number + 1)
        for i in range(self._pdb_in_loop - 1):
            # Add recursive debugger prompt
            prompt = "({})".format(prompt)
        return prompt + ": "

    def _handle_kernel_info_reply(self, rep):
        """Handle kernel info replies."""
        super(DebuggingWidget, self)._handle_kernel_info_reply(rep)
        pygments_lexer = rep['content']['language_info'].get(
            'pygments_lexer', '')
        try:
            # add custom lexer
            if pygments_lexer == 'ipython3':
                lexer = SpyderIPy3Lexer()
            elif pygments_lexer == 'ipython2':
                lexer = SpyderIPy2Lexer()
            else:
                return
            self._highlighter._lexer = lexer
        except ClassNotFound:
            pass

    def _redefine_complete_for_dbg(self, client):
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

    def _update_pdb_prompt(self, prompt, password=None):
        """Update the prompt that is recognised as a pdb prompt."""
        if prompt == self._pdb_prompt[0]:
            # Nothing to do
            return
        # Adapted from qtconsole/frontend_widget.py
        # This adds `prompt` as a prompt self._highlighter recognises
        self._highlighter._ipy_prompt_re = re.compile(
            r'^({})?([ \t]*{}|[ \t]*In \[\d+\]: |[ \t]*\ \ \ \.\.\.+: )'
            .format(re.escape(self.other_output_prefix), re.escape(prompt)))
        if password is None:
            password = self._pdb_prompt[1]
        self._pdb_prompt = (prompt, password)

        # Update continuation prompt to reflect (possibly) new prompt length.
        self._set_continuation_prompt(
            self._make_continuation_prompt(prompt), html=True)

    def _is_pdb_complete(self, source):
        """
        Check if the pdb input is ready to be executed.
        """
        if source and source[0] == '!':
            source = source[1:]
        tm = TransformerManager()
        complete, indent = tm.check_complete(source)
        if indent is not None:
            indent = indent * ' '
        return complete != 'incomplete', indent

    def execute(self, source=None, hidden=False, interactive=False):
        """
        Executes source or the input buffer, possibly prompting for more
        input.

        Do not use to run pdb commands (such as `continue`).
        Use pdb_execute instead. This will add a '!' in front of the code.
        """
        if self.is_waiting_pdb_input():
            if source is None:
                if hidden:
                    # Nothing to execute
                    return
                else:
                    source = self.input_buffer
            else:
                if not self.is_pdb_using_exclamantion_mark():
                    source = '!' + source
                if not hidden:
                    self.input_buffer = source

            if interactive:
                # Add a continuation prompt if not complete
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

        return super(DebuggingWidget, self).execute(
            source, hidden, interactive)

    def _pdb_readline_callback(self, line):
        """Callback used when the user inputs text in pdb."""
        self.pdb_execute(line)

    def pdb_input(self, prompt, password=None):
        """Get input for a command."""
        if self._hidden:
            raise RuntimeError(
                'Request for pdb input during hidden execution.')

        # Replace with numbered prompt
        prompt = self._current_prompt()
        self._update_pdb_prompt(prompt, password)

        # The prompt should be printed unless:
        # 1. The prompt is already printed (self._reading is True)
        # 2. A hidden command is in the queue
        print_prompt = (not self._reading
                        and (len(self._pdb_input_queue) == 0
                             or not self._pdb_input_queue[0][1]))

        if print_prompt:
            # Make sure that all output from the SUB channel has been processed
            # before writing a new prompt.
            self.kernel_client.iopub_channel.flush()
            self._waiting_pdb_input = True
            self._readline(prompt=prompt, callback=self._pdb_readline_callback,
                           password=password)
            self._executing = False
            self._highlighter.highlighting_on = True
            # The previous code finished executing
            self.executed.emit(self._pdb_prompt)
            self.sig_pdb_prompt_ready.emit()
            self.sig_pdb_state.emit(True, self.get_pdb_last_step())

        self._pdb_input_ready = True

        start_line = CONF.get('ipython_console', 'startup/pdb_run_lines', '')
        # Only run these lines when printing a new prompt
        if start_line and print_prompt and self.is_waiting_pdb_input():
            # Send a few commands
            self.pdb_execute(start_line, hidden=True)
            return

        # While the widget thinks only one input is going on,
        # other functions can be sending messages to the kernel.
        # This must be properly processed to avoid dropping messages.
        # If the kernel was not ready, the messages are queued.
        if len(self._pdb_input_queue) > 0:
            args = self._pdb_input_queue.pop(0)
            self.pdb_execute(*args)
            return

    # --- Private API (overrode by us) ----------------------------------------
    def _show_prompt(self, prompt=None, html=False, newline=True):
        """
        Writes a new prompt at the end of the buffer.
        """
        if prompt == self._pdb_prompt[0]:
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
        # Add a continuation prompt if not complete
        if self.is_waiting_pdb_input():
            # As the work is done on this side, check syncronously.
            complete, indent = self._is_pdb_complete(source)
            callback(complete, indent)
        else:
            return super(DebuggingWidget, self)._register_is_complete_callback(
                source, callback)
