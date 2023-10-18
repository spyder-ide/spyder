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
import re

# Third party imports
from pickle import UnpicklingError
from qtconsole.ansi_code_processor import ANSI_PATTERN
from qtconsole.rich_jupyter_widget import RichJupyterWidget

# Local imports
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

    def get_documentation(self, content, signature):
        """Get documentation from inspect reply content."""
        data = content.get('data', {})
        text = data.get('text/plain', '')

        if text:
            # Remove ANSI characters from text
            text = re.compile(ANSI_PATTERN).sub('', text)

            if (
                self.language_name is not None
                and self.language_name == 'python'
            ):
                # Base value for the documentation
                documentation = (
                    text.split('Docstring:')[-1].
                    split('Type:')[0].
                    split('File:')[0]
                ).strip()

                # Check if the signature is at the beginning of the docstring
                # to remove it
                if signature:
                    signature_and_doc = documentation.split("\n\n")

                    if (
                        len(signature_and_doc) > 1
                        and signature_and_doc[0].replace('\n', '') == signature
                    ):
                        return "\n\n".join(signature_and_doc[1:]).strip('\r\n')

                return documentation.strip('\r\n')
            else:
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
            signature = name + getsignaturefromtext(text, name)

        return signature

    def get_signature(self, content):
        """Get signature from inspect reply content"""
        data = content.get('data', {})
        text = data.get('text/plain', '')

        if text:
            # Remove ANSI characters from text
            text = re.compile(ANSI_PATTERN).sub('', text)

            if (
                self.language_name is not None
                and self.language_name == 'python'
            ):
                signature = ''
                self._control.current_prompt_pos = self._prompt_pos

                # Get object's name
                line = self._control.get_current_line_to_cursor()
                name = line[:-1].split('(')[-1]   # Take last token after a (
                name = name.split('.')[-1]   # Then take last token after a .

                # Clean name from invalid chars
                try:
                    name = self.clean_invalid_var_chars(name)
                except Exception:
                    pass

                # Split between docstring and text before it
                if 'Docstring:' in text:
                    before_text, after_text = text.split('Docstring:')
                else:
                    before_text, after_text = '', text

                if before_text:
                    # This is the case for objects for which IPython was able
                    # to get a signature (e.g. np.vectorize)
                    before_text = before_text.strip().replace('\n', '')
                    signature = self._get_signature(name, before_text)

                # Default signatures returned by IPython
                default_sigs = [
                    name + '(*args, **kwargs)',
                    name + '(self, /, *args, **kwargs)'
                ]

                # This is the case for objects without signature (e.g.
                # np.where). For them, we try to find it from their docstrings.
                if not signature or signature in default_sigs:
                    after_signature = self._get_signature(
                        name, after_text.strip()
                    )
                    if after_signature:
                        signature = after_signature

                    signature = signature.replace('\n', '')

                return signature.strip('\r\n')
            else:
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

        if (
            info
            and info.id == rep['parent_header']['msg_id']
            and info.pos == cursor.position()
        ):
            content = rep['content']
            if content.get('status') == 'ok' and content.get('found', False):
                signature = self.get_signature(content)
                documentation = self.get_documentation(content, signature)
                new_line = (self.language_name is not None
                            and self.language_name == 'python')

                self._control.show_calltip(
                    signature,
                    documentation=documentation,
                    language=self.language_name,
                    max_lines=7,
                    text_new_line=new_line
                )
