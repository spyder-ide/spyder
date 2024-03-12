# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""
Widget that handles communications between a console in debugging
mode and Spyder
"""

# Standard library imports
import atexit
import pdb
import re

# Third-party imports
from IPython.core.history import HistoryManager
from IPython.core.inputtransformer2 import TransformerManager
from IPython.lib.lexers import (
    IPython3Lexer, Python3Lexer, bygroups, using
)
from pygments.token import Keyword, Operator
from pygments.util import ClassNotFound
from qtconsole.rich_jupyter_widget import RichJupyterWidget
from qtpy.QtCore import QEvent
from qtpy.QtGui import QTextCursor

# Local imports
from spyder.api.config.mixins import SpyderConfigurationAccessor
from spyder.config.base import get_conf_path


class SpyderIPy3Lexer(IPython3Lexer):
    # Detect !cmd command and highlight them
    tokens = IPython3Lexer.tokens
    spyder_tokens = [
        (r'(!)(\w+)(.*\n)', bygroups(Operator, Keyword, using(Python3Lexer))),
        (r'(%)(\w+)(.*\n)', bygroups(Operator, Keyword, using(Python3Lexer))),
    ]
    tokens['root'] = spyder_tokens + tokens['root']


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
        self._saved_pdb_history_input_number = {}  # for recursive debugging

        # Catch any exception that prevents to create or access the history
        # file to avoid errors.
        # Fixes spyder-ide/spyder#18531
        try:
            self._pdb_history_file = PdbHistory()
            self._pdb_history = [
                line[-1] for line in self._pdb_history_file.get_tail(
                    self.PDB_HIST_MAX, include_latest=True)
            ]
        except Exception:
            self._pdb_history_file = None
            self._pdb_history = []

        self._pdb_history_edits = {}  # Temporary history edits
        self._pdb_history_index = len(self._pdb_history)

        # super init
        super(DebuggingHistoryWidget, self).__init__(*args, **kwargs)

    # --- Public API --------------------------------------------------
    def new_history_session(self):
        """Start a new history session."""
        self._pdb_history_input_number = 0
        if self._pdb_history_file is not None:
            self._pdb_history_file.new_session()

    def end_history_session(self):
        """End an history session."""
        self._pdb_history_input_number = 0
        if self._pdb_history_file is not None:
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
            cmd.strip() and cmd[0] != '!' and "do_" + cmd in dir(pdb.Pdb)
        )
        if self.is_pdb_using_exclamantion_mark():
            is_pdb_cmd = is_pdb_cmd or (
                cmd.strip() and cmd[0] == '!'
                and "do_" + cmd[1:] in dir(pdb.Pdb))

        if cmd and (not is_pdb_cmd or len(args) > 0):
            self._pdb_history.append(line)
            self._pdb_history_index = len(self._pdb_history)
            if self._pdb_history_file is not None:
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


class DebuggingWidget(DebuggingHistoryWidget, SpyderConfigurationAccessor):
    """
    Widget with the necessary attributes and methods to handle
    communications between a console in debugging mode and
    Spyder
    """

    CONF_SECTION = 'ipython_console'

    def __init__(self, *args, **kwargs):
        # Communication state
        self._pdb_recursion_level = 0  # Number of debbuging loop we are in
        self._pdb_input_ready = False  # Can we send a command now
        self._waiting_pdb_input = False  # Are we waiting on the user
        # Other state
        self._pdb_prompt = None  # prompt
        self._pdb_prompt_input = False  # wether pdb waits for input or comm
        self._pdb_last_cmd = ''  # last command sent to pdb
        self._pdb_frame_loc = (None, None)  # fname, lineno
        self._pdb_take_focus = True  # Focus to shell after command execution
        # Command queue
        self._pdb_input_queue = []  # List of (code, hidden, echo_stack_entry)
        # Temporary flags
        self._tmp_reading = False
        # super init
        super(DebuggingWidget, self).__init__(*args, **kwargs)

        # Adapted from qtconsole/frontend_widget.py
        # This adds the IPdb as a prompt self._highlighter recognises
        self._highlighter._ipy_prompt_re = re.compile(
            r'^({})?('.format(re.escape(self.other_output_prefix)) +
            r'[ \t]*\(*IPdb \[\d+\]\)*: |' +
            r'[ \t]*In \[\d+\]: |[ \t]*\ \ \ \.\.\.+: )')

        # Reset debug state when debugging is done
        self.sig_prompt_ready.connect(self.reset_debug_state)

    # --- Public API --------------------------------------------------

    def shutdown(self):
        """
        Close the save thread and database file.
        """
        try:
            # Make sure the database will not be called after closing
            self.sig_prompt_ready.disconnect(self.reset_debug_state)
        except (TypeError, RuntimeError):
            # Already disconnected
            pass

        if self._pdb_history_file is not None:
            try:
                self._pdb_history_file.save_thread.stop()
                # Now that it was called, no need to call it at exit
                atexit.unregister(self._pdb_history_file.save_thread.stop)
            except AttributeError:
                pass

            try:
                self._pdb_history_file.db.close()
            except AttributeError:
                pass

    # --- Comm API --------------------------------------------------

    def set_debug_state(self, recursion_level):
        """Update the debug state."""
        if recursion_level == self._pdb_recursion_level:
            # Nothing to change
            return

        if recursion_level > self._pdb_recursion_level:
            # Start debugging
            if self._pdb_recursion_level > 0:
                # Recursive debugging, save state
                self._saved_pdb_history_input_number[
                    self._pdb_recursion_level] = self._pdb_history_input_number
                self.end_history_session()
            self.new_history_session()
        elif recursion_level < self._pdb_recursion_level:
            # Stop debugging
            self.end_history_session()
            if recursion_level > 0:
                # Still debugging, restore state
                self.new_history_session()
                self._pdb_history_input_number = (
                    self._saved_pdb_history_input_number.pop(
                        recursion_level, 0))

        # If debugging starts or stops, clear the input queue.
        self._pdb_recursion_level = recursion_level
        self._pdb_input_queue = []
        self._pdb_frame_loc = (None, None)

    def _pdb_cmd_prefix(self):
        """Return the command prefix"""
        prefix = ''
        if self.spyder_kernel_ready and self.is_pdb_using_exclamantion_mark():
            prefix = '!'
        return prefix

    def pdb_execute_command(self, command):
        """
        Execute a pdb command
        """
        self._pdb_take_focus = False
        self.pdb_execute(
            self._pdb_cmd_prefix() + command, hidden=False,
            echo_stack_entry=False, add_history=False)

    def _handle_input_request(self, msg):
        """Process an input request."""
        if not self.is_spyder_kernel and "ipdb>" in msg['content']['prompt']:
            # Check if we can guess a path from the shell content:
            self._flush_pending_stream()
            cursor = self._get_end_cursor()
            cursor.setPosition(self._prompt_pos, QTextCursor.KeepAnchor)
            text = cursor.selection().toPlainText()
            match = re.search(r"> (.*\.py)\((\d+)\)", text)
            state = None

            if match:
                fname, lineno = match.groups()
                state = {
                    'step': {
                        'fname': fname,
                        'lineno': int(lineno)
                    }
                }

            prompt = msg['content']['prompt']
            password = msg['content']['password']
            self.pdb_input(prompt, password, state, from_input=True)
            return
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
            self.sig_pdb_state_changed.emit(False)

        if self._pdb_input_ready:
            # Print the string to the console
            self._pdb_input_ready = False
            self.pdb_input_reply(line, echo_stack_entry)
            return

        self._pdb_input_queue.append(
            (line, hidden, echo_stack_entry, add_history))

    def reset_debug_state(self):
        """Reset debug state if the debugger crashed."""
        self.set_debug_state(0)

    # --- To Sort --------------------------------------------------
    def stop_debugging(self):
        """Stop debugging."""
        if self.spyder_kernel_ready and not self.is_waiting_pdb_input():
            self.interrupt_kernel()
        self.pdb_execute_command("exit")

    def is_pdb_using_exclamantion_mark(self):
        return self.get_conf('pdb_use_exclamation_mark', section='debugger')

    def refresh_from_pdb(self, pdb_state):
        """
        Refresh Variable Explorer and Editor from a Pdb session,
        after running any pdb command.

        See publish_pdb_state and notify_spyder in spyder_kernels
        """
        pdb_step = pdb_state.pop('step', None)
        if pdb_step and 'fname' in pdb_step:
            fname = pdb_step['fname']
            lineno = pdb_step['lineno']

            last_pdb_loc = self._pdb_frame_loc
            self._pdb_frame_loc = (fname, lineno)

            # Only step if the location changed
            if (fname, lineno) != last_pdb_loc:
                self.sig_pdb_step.emit(fname, lineno)

        if "do_where" in pdb_state:
            fname, lineno = self._pdb_frame_loc
            if fname:
                self.sig_pdb_step.emit(fname, lineno)

        pdb_stack = pdb_state.pop('stack', None)
        if pdb_stack:
            pdb_stack, pdb_index = pdb_stack
            self.sig_pdb_stack.emit(pdb_stack, pdb_index)

        request_pdb_input =  pdb_state.pop('request_pdb_input', None)
        if request_pdb_input:
            self.pdb_execute(request_pdb_input)

        self.update_state(pdb_state)

    def show_pdb_output(self, text):
        """Show Pdb output."""
        self._append_plain_text(self.output_sep, before_prompt=True)
        prompt = self._current_out_prompt()
        self._append_html(
            '<span class="out-prompt">%s</span>' % prompt,
            before_prompt=True
        )
        # If the repr is multiline, make sure we start on a new line,
        # so that its lines are aligned.
        if "\n" in text and not self.output_sep.endswith("\n"):
            self._append_plain_text('\n', before_prompt=True)
        self._append_plain_text(text + self.output_sep2, before_prompt=True)
        self._append_plain_text('\n', before_prompt=True)

    def get_pdb_last_step(self):
        """Get last pdb step retrieved from a Pdb session."""
        return self._pdb_frame_loc

    def is_debugging(self):
        """Check if we are debugging."""
        return self._pdb_recursion_level > 0

    def debugging_depth(self):
        """Debugging depth"""
        return self._pdb_recursion_level

    def is_waiting_pdb_input(self):
        """Check if we are waiting a pdb input."""
        # If the comm is not open, self._pdb_recursion_level can not be set
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
            prompt = self._pdb_prompt

            try:
                # This is necessary to avoid an error when the iopub channel is
                # closed.
                # See jupyter/qtconsole#574
                if not self.kernel_client.iopub_channel.closed():
                    self.kernel_client.iopub_channel.flush()
            except AttributeError:
                self.kernel_client.iopub_channel.flush()

            self._reading = False
            self._readline(prompt=prompt, callback=self.pdb_execute)

    # --- Private API --------------------------------------------------
    def _current_prompt(self):
        prompt = "IPdb [{}]".format(self._pdb_history_input_number + 1)
        for i in range(self._pdb_recursion_level - 1):
            # Add recursive debugger prompt
            prompt = "({})".format(prompt)
        return prompt + ": "

    def _current_out_prompt(self):
        """Get current out prompt."""
        prompt = "Out\u00A0\u00A0[{}]".format(self._pdb_history_input_number)
        for i in range(self._pdb_recursion_level - 1):
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
            else:
                return
            self._highlighter._lexer = lexer
        except ClassNotFound:
            pass

    def _redefine_complete_for_dbg(self, client):
        """Redefine kernel client's complete method to work while debugging."""

        original_complete = client.complete

        def complete(code, cursor_pos=None):
            if self.is_waiting_pdb_input():
                shell_channel = client.shell_channel
                client._shell_channel = client.control_channel
                try:
                    return original_complete(code, cursor_pos)
                finally:
                    client._shell_channel = shell_channel
            else:
                return original_complete(code, cursor_pos)

        client.complete = complete

    def _update_pdb_prompt(self, prompt):
        """Update the prompt that is recognised as a pdb prompt."""
        if prompt == self._pdb_prompt:
            # Nothing to do
            return

        self._pdb_prompt = prompt

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

    def pdb_input(self, prompt, password=None, state=None, from_input=False):
        """Get input for a command."""

        self.set_debug_state(1 + prompt.count("("))

        if state is not None and isinstance(state, dict):
            self.refresh_from_pdb(state)

        # Replace with numbered prompt
        prompt = self._current_prompt()
        self._update_pdb_prompt(prompt)
        self._pdb_prompt_input = from_input

        # The prompt should be printed unless:
        # 1. The prompt is already printed (self._reading is True)
        # 2. A hidden command is in the queue
        print_prompt = (not self._reading
                        and (len(self._pdb_input_queue) == 0
                             or not self._pdb_input_queue[0][1]))

        if print_prompt:
            # Make sure that all output from the SUB channel has been processed
            # before writing a new prompt.
            try:
                # This is necessary to avoid an error when the iopub channel is
                # closed.
                # See jupyter/qtconsole#574
                if not self.kernel_client.iopub_channel.closed():
                    self.kernel_client.iopub_channel.flush()
            except AttributeError:
                self.kernel_client.iopub_channel.flush()

            self._waiting_pdb_input = True
            self._readline(prompt=prompt,
                           callback=self.pdb_execute,
                           password=password)
            self._executing = False
            self._highlighter.highlighting_on = True
            # The previous code finished executing
            self.executed.emit(self._pdb_prompt)
            self.sig_pdb_prompt_ready.emit()
            self.sig_pdb_state_changed.emit(True)

        self._pdb_input_ready = True

        start_line = self.get_conf('startup/pdb_run_lines', default='')
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

    def pdb_input_reply(self, line, echo_stack_entry):
        """Send a pdb input to the kernel."""
        if self._pdb_prompt_input:
            # Send line to input
            self.kernel_client.input(line)
            return

        self.call_kernel(interrupt=True).pdb_input_reply(
            line, echo_stack_entry=echo_stack_entry)

    # --- Private API (overrode by us) ----------------------------------------
    def _show_prompt(self, prompt=None, html=False, newline=True,
                     separator=True):
        """
        Writes a new prompt at the end of the buffer.
        """
        if prompt == self._pdb_prompt:
            html = True
            prompt = '<span class="in-prompt">%s</span>' % prompt
        super(DebuggingWidget, self)._show_prompt(prompt, html, newline,
                                                  separator)

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
            # As the work is done on this side, check synchronously.
            complete, indent = self._is_pdb_complete(source)
            callback(complete, indent)
        else:
            return super(DebuggingWidget, self)._register_is_complete_callback(
                source, callback)

    # ---- Qt methods ---------------------------------------------------------
    def eventFilter(self, obj, event):
        # When using PySide, it can happen that "event" is of type QWidgetItem
        # (reason unknown). This causes an exception in eventFilter() in
        # console_widget.py in the QtConsole package: Therein event.type() is
        # accessed which fails due to an AttributeError. Catch this here and
        # ignore the event.
        if not isinstance(event, QEvent):
            # Note for debugging: event.layout() or event.widget() SEGFAULTs
            return True

        return super().eventFilter(obj, event)
