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

from qtpy.QtCore import QEventLoop

from qtconsole.rich_jupyter_widget import RichJupyterWidget

from spyder.py3compat import to_text_string


class DebuggingWidget(RichJupyterWidget):
    """
    Widget with the necessary attributes and methods to handle
    communications between a console in debugging mode and
    Spyder
    """

    _input_reply = None
    _hidden_input = False

    # --- Public API --------------------------------------------------
    def silent_exec_input(self, code):
        """Silently execute code through stdin"""
        self._hidden_input = True

        # Wait until the kernel returns an answer
        wait_loop = QEventLoop()
        self.sig_input_reply.connect(wait_loop.quit)
        self.kernel_client.iopub_channel.flush()
        self.kernel_client.input(code)
        wait_loop.exec_()

        # Remove loop connection and loop
        self.sig_input_reply.disconnect(wait_loop.quit)
        wait_loop = None

    # ---- Private API (overrode by us) ----------------------------
    def _handle_input_request(self, msg):
        """ Handle requests for raw_input.
        """
        if self._hidden_input:
            self._hidden_input = False
        else:
            super(DebuggingWidget, self)._handle_input_request(msg)

    def _handle_stream(self, msg):
        """ Handle stdout, stderr, and stdin.
        """
        if self._hidden_input:
            content = msg.get('content', '')
            if content:
                name = content.get('name', '')
                if name == 'stdout':
                    text = content['text']
                    text = to_text_string(text.replace('\n', ''))
                    reply = ast.literal_eval(text)
                    self._input_reply = reply
                    self.sig_input_reply.emit()
                else:
                    self._input_reply = None
                    self.sig_input_reply.emit()
            else:
                self._input_reply = None
                self.sig_input_reply.emit()
        else:
            super(DebuggingWidget, self)._handle_stream(msg)
