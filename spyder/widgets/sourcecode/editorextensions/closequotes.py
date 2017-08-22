# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""
This module contains the quote select editor extension
"""

from spyder.api.editorextension import EditorExtension


class QuoteEditorExtension(EditorExtension):
    """"""
    def on_state_changed(self, state):
        """"""
        self.editor.key_pressed.connect(self._on_key_pressed)

    def _on_key_pressed(self, event):
        pass
