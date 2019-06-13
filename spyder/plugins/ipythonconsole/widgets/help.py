# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""
Widget that handles communications between the IPython Console and
the Help plugin
"""

from __future__ import absolute_import

import re

from qtconsole.ansi_code_processor import ANSI_OR_SPECIAL_PATTERN
from qtconsole.rich_jupyter_widget import RichJupyterWidget
from qtpy.QtCore import QEventLoop
from spyder_kernels.utils.dochelpers import (getargspecfromtext,
                                             getsignaturefromtext)

from spyder.config.base import _
from spyder.py3compat import PY3


class HelpWidget(RichJupyterWidget):
    """
    Widget with the necessary attributes and methods to handle communications
    between the IPython Console and the Help plugin
    """

    def clean_invalid_var_chars(self, var):
        """
        Replace invalid variable chars in a string by underscores

        Taken from https://stackoverflow.com/a/3305731/438386
        """
        return re.sub(r'\W|^(?=\d)', '_', var)

    def get_documentation(self, content):
        """Get documentation fron inspect reply content."""
        data = content.get('data', {})
        text = data.get('text/plain', '')
        signature = self.get_signature(content).split('(')[-1]
        if text:
            documentation = text.split(signature)
            if len(documentation) > 1:
                return documentation[-1]

    def get_signature(self, content):
        """Get signature from inspect reply content"""
        data = content.get('data', {})
        text = data.get('text/plain', '')
        if text:
            text = ANSI_OR_SPECIAL_PATTERN.sub('', text)
            self._control.current_prompt_pos = self._prompt_pos
            line = self._control.get_current_line_to_cursor()
            name = line[:-1].split('(')[-1]   # Take last token after a (
            name = name.split('.')[-1]        # Then take last token after a .
            # Clean name from invalid chars
            try:
                name = self.clean_invalid_var_chars(name)
            except:
                pass
            text = text.split('Docstring:')[-1]
            argspec = getargspecfromtext(text)
            if argspec:
                # This covers cases like np.abs, whose docstring is
                # the same as np.absolute and because of that a proper
                # signature can't be obtained correctly
                signature = name + argspec
            else:
                signature = getsignaturefromtext(text, name)
            # Remove docstring for uniformity with editor
            signature = signature.split('Docstring:')[0]

            return signature
        else:
            return ''

    def is_defined(self, objtxt, force_import=False):
        """Return True if object is defined"""
        if self._reading:
            return
        wait_loop = QEventLoop()
        self.sig_got_reply.connect(wait_loop.quit)
        self.silent_exec_method(
            "get_ipython().kernel.is_defined('%s', force_import=%s)"
            % (objtxt, force_import))
        wait_loop.exec_()

        # Remove loop connection and loop
        self.sig_got_reply.disconnect(wait_loop.quit)
        wait_loop = None

        return self._kernel_reply

    def get_doc(self, objtxt):
        """Get object documentation dictionary"""
        if self._reading:
            return
        wait_loop = QEventLoop()
        self.sig_got_reply.connect(wait_loop.quit)
        self.silent_exec_method("get_ipython().kernel.get_doc('%s')" % objtxt)
        wait_loop.exec_()

        # Remove loop connection and loop
        self.sig_got_reply.disconnect(wait_loop.quit)
        wait_loop = None

        return self._kernel_reply

    def get_source(self, objtxt):
        """Get object source"""
        if self._reading:
            return
        wait_loop = QEventLoop()
        self.sig_got_reply.connect(wait_loop.quit)
        self.silent_exec_method("get_ipython().kernel.get_source('%s')" % objtxt)
        wait_loop.exec_()

        # Remove loop connection and loop
        self.sig_got_reply.disconnect(wait_loop.quit)
        wait_loop = None

        return self._kernel_reply

    #---- Private methods (overrode by us) ---------------------------------
    def _handle_inspect_reply(self, rep):
        """
        Reimplement call tips to only show signatures, using the same
        style from our Editor and External Console too
        """
        cursor = self._get_cursor()
        info = self._request_info.get('call_tip')
        if (info and info.id == rep['parent_header']['msg_id'] and
                info.pos == cursor.position()):
            content = rep['content']
            if content.get('status') == 'ok' and content.get('found', False):
                signature = self.get_signature(content)
                documentation = self.get_documentation(content)
                if signature:
                    self._control.show_calltip(
                        signature,
                        documentation=documentation,
                        language=self.language_name,
                        max_lines=5
                    )
