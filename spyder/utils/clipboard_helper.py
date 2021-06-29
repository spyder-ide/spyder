# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""
Clipboard helper module.
"""
from qtpy.QtWidgets import QApplication
from qtpy.QtGui import QTextCursor

from spyder.py3compat import to_text_string


class _ClipboardHelp:
    # Clipboard metadata
    metadata_hash = None
    metadata_indent = None
    metadata_tab_stop_width_spaces = None


def get_current_hash():
    clipboard = QApplication.clipboard()
    return hash(to_text_string(clipboard.text()))


def get_line_indentation(text, tab_stop_width_spaces=None):
    """Get indentation for given line."""
    if tab_stop_width_spaces:
        text = text.replace("\t", " " * tab_stop_width_spaces)
    return len(text)-len(text.lstrip())


def save_indentation(preceding_text, tab_stop_width_spaces=None):
    """
    Save the indentation corresponding to the clipboard data.

    Must be called right after copying.
    """
    _ClipboardHelp.metadata_hash = get_current_hash()
    _ClipboardHelp.metadata_indent = get_line_indentation(
        preceding_text, tab_stop_width_spaces)
    _ClipboardHelp.metadata_tab_stop_width_spaces = tab_stop_width_spaces


def remaining_lines_adjustment(preceding_text):
    """
    Get remaining lines adjustments needed to keep multiline
    pasted text consistant.
    """
    if get_current_hash() == _ClipboardHelp.metadata_hash:
        return (
            get_line_indentation(
                preceding_text,
                _ClipboardHelp.metadata_tab_stop_width_spaces)
            - _ClipboardHelp.metadata_indent)
    return 0
