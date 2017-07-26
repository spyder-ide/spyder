# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""Outline explorer editor server"""

from spyder.plugins.outlineexplorer.api import OutlineExplorerProxy


class OutlineExplorerProxyEditor(OutlineExplorerProxy):
    def __init__(self, editor, fname):
        self._editor = editor
        self.fname = fname

    def get_id(self):
        return self._editor.get_document_id()

    def give_focus(self):
        self._editor.clearFocus()
        self._editor.setFocus()

    def get_outlineexplorer_data(self):
        return self._editor.get_outlineexplorer_data()

    def get_line_count(self):
        return self._editor.get_line_count()

    def parent(self):
        return self._editor.parent()
