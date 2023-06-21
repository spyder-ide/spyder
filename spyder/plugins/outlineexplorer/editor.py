# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""Outline explorer editor proxy."""

# Standard library imports
import logging

# Local imports
from spyder.plugins.outlineexplorer.api import OutlineExplorerProxy


# Logging
logger = logging.getLogger(__name__)


class OutlineExplorerProxyEditor(OutlineExplorerProxy):
    def __init__(self, editor, fname):
        super(OutlineExplorerProxyEditor, self).__init__()
        self._editor = editor
        self.fname = fname
        editor.sig_cursor_position_changed.connect(
            self.sig_cursor_position_changed)

        # This saves the symbols info that comes from the server.
        self.info = None

        # This is used to tell if the associated tree is updated with the
        # latest info available here
        self.is_tree_updated = False

    def update_outline_info(self, info):
        logger.debug(
            f"Updating info for proxy {id(self)} of file {self.fname}"
        )
        self.sig_outline_explorer_data_changed.emit(info)
        self.info = info
        self.is_tree_updated = False

    def emit_request_in_progress(self):
        self.sig_start_outline_spinner.emit()

    def is_python(self):
        return self._editor.is_python()

    def is_python_or_ipython(self):
        return self._editor.is_python_or_ipython()

    def get_id(self):
        return self._editor.get_document_id()

    def get_language(self):
        return self._editor.language

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

    def request_symbols(self):
        """Request current editor symbols."""
        self._editor.request_symbols()

    @property
    def is_cloned(self):
        """Check if the associated editor is cloned."""
        return self._editor.is_cloned
