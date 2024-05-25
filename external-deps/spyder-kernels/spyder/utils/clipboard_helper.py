# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""
Clipboard helper module.
"""
from qtpy.QtWidgets import QApplication

from spyder.py3compat import to_text_string


class ClipboardHelper:
    # Clipboard metadata
    metadata_hash = None
    metadata_indent = None
    metadata_tab_stop_width_spaces = None

    def get_current_hash(self):
        clipboard = QApplication.clipboard()
        return hash(to_text_string(clipboard.text()))

    def get_line_indentation(self, text, tab_stop_width_spaces=None):
        """Get indentation for given line."""
        if tab_stop_width_spaces:
            text = text.replace("\t", " " * tab_stop_width_spaces)
        return len(text)-len(text.lstrip())

    def save_indentation(self, preceding_text, tab_stop_width_spaces=None):
        """
        Save the indentation corresponding to the clipboard data.

        Must be called right after copying.
        """
        self.metadata_hash = self.get_current_hash()
        self.metadata_indent = self.get_line_indentation(
            preceding_text, tab_stop_width_spaces)
        self.metadata_tab_stop_width_spaces = tab_stop_width_spaces

    def remaining_lines_adjustment(self, preceding_text):
        """
        Get remaining lines adjustments needed to keep multiline
        pasted text consistant.
        """
        if self.get_current_hash() == self.metadata_hash:
            return (
                self.get_line_indentation(
                    preceding_text,
                    self.metadata_tab_stop_width_spaces)
                - self.metadata_indent)
        return 0


CLIPBOARD_HELPER = ClipboardHelper()
