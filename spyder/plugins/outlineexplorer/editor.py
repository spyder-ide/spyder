# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""Outline explorer editor server"""

from spyder.plugins.outlineexplorer.api import OutlineExplorerProxy


class OutlineExplorerProxyEditor(OutlineExplorerProxy):
    def __init__(self, editor, fname):
        super(OutlineExplorerProxyEditor, self).__init__()
        self._editor = editor
        self.fname = fname
        editor.sig_cursor_position_changed.connect(
            self.sig_cursor_position_changed)
        editor.highlighter.sig_outline_explorer_data_changed.connect(
            self.sig_outline_explorer_data_changed)
        editor.blockCountChanged.connect(
            self.sig_outline_explorer_data_changed)

    def is_python(self):
        return self._editor.is_python()

    def get_id(self):
        return self._editor.get_document_id()

    def give_focus(self):
        self._editor.clearFocus()
        self._editor.setFocus()

    def get_cursor_line_number(self):
        return self._editor.get_cursor_line_number()

    def get_line_count(self):
        return self._editor.get_line_count()

    def parent(self):
        return self._editor.parent()

    def outlineexplorer_data_list(self):
        """Get outline explorer data list."""
        return self._editor.outlineexplorer_data_list()
