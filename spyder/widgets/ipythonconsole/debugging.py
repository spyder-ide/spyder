# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""
Widget that handles communications between a console in debugging
mode and Spyder
"""

from qtpy.QtCore import Qt

from qtconsole.rich_jupyter_widget import RichJupyterWidget


class DebuggingWidget(RichJupyterWidget):
    """
    Widget with the necessary attributes and methods to handle
    communications between a console in debugging mode and
    Spyder
    """

    history = []
    histidx = None
    hist_wholeline = False

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

    # ---- Private API (defined by us) ----------------------------
    def __clear_line(self):
        """Clear current line (without clearing console prompt)"""
        self._control.remove_text(self._control.current_prompt_pos, 'eof')

    def __browse_history(self, backward):
        """Browse history"""
        self._control.current_prompt_pos = self._prompt_pos
        if self._control.is_cursor_before('eol') and self.hist_wholeline:
            self.hist_wholeline = False
        tocursor = self._control.get_current_line_to_cursor()
        text, self.histidx = self.__find_in_history(tocursor,
                                                    self.histidx, backward)
        if text is not None:
            if self.hist_wholeline:
                self.__clear_line()
                self._control.insert_text(text)
            else:
                cursor_position = self._control.get_position('cursor')
                # Removing text from cursor to the end of the line
                self._control.remove_text('cursor', 'eol')
                # Inserting history text
                self._control.insert_text(text)
                self._control.set_cursor_position(cursor_position)

    def __find_in_history(self, tocursor, start_idx, backward):
        """Find text 'tocursor' in history, from index 'start_idx'"""
        if start_idx is None:
            start_idx = len(self.history)
        # Finding text in history
        step = -1 if backward else 1
        idx = start_idx
        if len(tocursor) == 0 or self.hist_wholeline:
            idx += step
            if idx >= len(self.history) or len(self.history) == 0:
                return "", len(self.history)
            elif idx < 0:
                idx = 0
            self.hist_wholeline = True
            return self.history[idx], idx
        else:
            for index in range(len(self.history)):
                idx = (start_idx+step*(index+1)) % len(self.history)
                entry = self.history[idx]
                if entry.startswith(tocursor):
                    return entry[len(tocursor):], idx
            else:
                return None, start_idx

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
            self.history.append(line)

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
            if key == Qt.Key_Up:
                self.__browse_history(backward=True)
                return True
            elif key == Qt.Key_Down:
                self.__browse_history(backward=False)
                return True
            else:
                return super(DebuggingWidget,
                             self)._event_filter_console_keypress(event)
        else:
            return super(DebuggingWidget,
                         self)._event_filter_console_keypress(event)

