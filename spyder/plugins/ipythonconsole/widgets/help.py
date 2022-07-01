# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""
Widget that handles communications between the IPython Console and
the Help plugin
"""

# Standard library imports
from __future__ import absolute_import

import re

# Third party imports
from pickle import UnpicklingError
from qtconsole.ansi_code_processor import ANSI_OR_SPECIAL_PATTERN, ANSI_PATTERN
from qtconsole.rich_jupyter_widget import RichJupyterWidget
from qtpy.QtCore import QEventLoop

# Local imports
from spyder.py3compat import TimeoutError
from spyder_kernels.utils.dochelpers import (getargspecfromtext,
                                             getsignaturefromtext)
from spyder_kernels.comms.commbase import CommError


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
        """Get documentation from inspect reply content."""
        data = content.get('data', {})
        text = data.get('text/plain', '')
        if text:
            if (self.language_name is not None
                    and self.language_name == 'python'):
                text = re.compile(ANSI_PATTERN).sub('', text)
                signature = self.get_signature(content).split('(')[-1]

                # Base value for the documentation
                documentation = (text.split('Docstring:')[-1].
                                 split('Type:')[0].split('File:')[0])

                if signature:
                    # Check if the signature is in the Docstring
                    doc_from_signature = documentation.split(signature)
                    if len(doc_from_signature) > 1:
                        return (doc_from_signature[-1].split('Docstring:')[-1].
                                split('Type:')[0].
                                split('File:')[0]).strip('\r\n')

                return documentation.strip('\r\n')
            else:
                text = re.compile(ANSI_PATTERN).sub('', text)
                return text.strip('\r\n')
        else:
            return ''

    def _get_signature(self, name, text):
        """Get signature from text using a given function name."""
        signature = ''
        argspec = getargspecfromtext(text)
        if argspec:
            # This covers cases like np.abs, whose docstring is
            # the same as np.absolute and because of that a proper
            # signature can't be obtained correctly
            signature = name + argspec
        else:
            signature = getsignaturefromtext(text, name)
        return signature

    def get_signature(self, content):
        """Get signature from inspect reply content"""
        data = content.get('data', {})
        text = data.get('text/plain', '')
        if text:
            if (self.language_name is not None
                    and self.language_name == 'python'):
                self._control.current_prompt_pos = self._prompt_pos
                line = self._control.get_current_line_to_cursor()
                name = line[:-1].split('(')[-1]   # Take last token after a (
                name = name.split('.')[-1]   # Then take last token after a .

                # Clean name from invalid chars
                try:
                    name = self.clean_invalid_var_chars(name)
                except Exception:
                    pass

                text = text.split('Docstring:')

                # Try signature from text before 'Docstring:'
                before_text = text[0]
                before_signature = self._get_signature(name, before_text)

                # Try signature from text after 'Docstring:'
                after_text = text[-1]
                after_signature = self._get_signature(name, after_text)

                # Stay with the longest signature
                if len(before_signature) > len(after_signature):
                    signature = before_signature
                else:
                    signature = after_signature

                # Prevent special characters. Applied here to ensure
                # recognizing the signature in the logic above.
                signature = ANSI_OR_SPECIAL_PATTERN.sub('', signature)

                return signature.strip('\r\n')
            else:
                text = re.compile(ANSI_PATTERN).sub('', text)
                return text.strip('\r\n')
        else:
            return ''

    def is_defined(self, objtxt, force_import=False):
        """Return True if object is defined"""
        try:
            return self.call_kernel(
                blocking=True
                ).is_defined(objtxt, force_import=force_import)
        except (TimeoutError, UnpicklingError, RuntimeError, CommError):
            return None

    def get_doc(self, objtxt):
        """Get object documentation dictionary"""
        try:
            return self.call_kernel(blocking=True).get_doc(objtxt)
        except (TimeoutError, UnpicklingError, RuntimeError, CommError):
            return None

    def get_source(self, objtxt):
        """Get object source"""
        try:
            return self.call_kernel(blocking=True).get_source(objtxt)
        except (TimeoutError, UnpicklingError, RuntimeError, CommError):
            return None

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
                new_line = (self.language_name is not None
                            and self.language_name == 'python')
                self._control.show_calltip(
                    signature,
                    documentation=documentation,
                    language=self.language_name,
                    max_lines=7,
                    text_new_line=new_line
                )
