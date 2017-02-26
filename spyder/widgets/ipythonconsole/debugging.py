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

    _input_reply = {}
    _input_reply_failed = False
    _pdb_state = {}

    # --- Public API --------------------------------------------------
    def silent_exec_input(self, code):
        """Silently execute code through stdin"""
        self._hidden = True

        # Wait until the kernel returns an answer
        wait_loop = QEventLoop()
        self.sig_input_reply.connect(wait_loop.quit)
        self.kernel_client.iopub_channel.flush()
        self.kernel_client.input(code)
        wait_loop.exec_()

        # Remove loop connection and loop
        self.sig_input_reply.disconnect(wait_loop.quit)
        wait_loop = None

        # Restore hidden state
        self._hidden = False

        # Emit signal
        if isinstance(self._input_reply, dict):
            if 'pdb_step' in code and 'fname' in self._input_reply:
                fname = self._input_reply['fname']
                lineno = self._input_reply['lineno']
                self.sig_pdb_step.emit(fname, lineno)
            elif 'get_namespace_view' in code:
                if 'fname' not in self._input_reply:
                    view = self._input_reply
                else:
                    view = None
                self.sig_namespace_view.emit(view)
            elif 'get_var_properties' in code:
                if 'fname' not in self._input_reply:
                    properties = self._input_reply
                else:
                    properties = None
                self.sig_var_properties.emit(properties)
        else:
            self.kernel_client.iopub_channel.flush()
            self._input_reply = {}
            self._input_reply_failed = True
            self.sig_dbg_kernel_restart.emit()

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
        with open(filename, 'rb') as f:
            self._pdb_state = pickle.load(f)

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

    def _handle_stream(self, msg):
        """
        Reimplemented to handle input replies in hidden mode
        """
        if not self._hidden:
            self.flush_clearoutput()
            self.append_stream(msg['content']['text'])
            # This signal is a clear indication that all stdout
            # has been handled at this point. Then Spyder can
            # proceed to request other inputs
            self.sig_prompt_ready.emit()
        else:
            # This allows Spyder to receive, transform and save the
            # contents of a silent execution
            content = msg.get('content', '')
            if content:
                name = content.get('name', '')
                if name == 'stdout':
                    text = content['text']
                    text = to_text_string(text.replace('\n', ''))
                    try:
                        reply = ast.literal_eval(text)
                    except:
                        reply = None
                    if not isinstance(reply, dict):
                        self._input_reply = None
                    else:
                        self._input_reply = reply
                    self.sig_input_reply.emit()
                else:
                    self._input_reply = None
                    self.sig_input_reply.emit()
            else:
                self._input_reply = None
                self.sig_input_reply.emit()
