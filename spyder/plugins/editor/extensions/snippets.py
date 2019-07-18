# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""Code snippets editor extension."""

# Standard library imports
import re
from collections import OrderedDict

# Third party imports
from qtpy.QtGui import QTextCursor
from qtpy.QtCore import Qt
from qtpy.QtWidgets import QMenu

# Local imports
from spyder.config.main import CONF
from spyder.py3compat import to_text_string
from spyder.api.editorextension import EditorExtension


class SnippetsExtension(EditorExtension):
    def __init__(self):
        EditorExtension.__init__(self)
        self.is_snippet_active = False
        self.snippet_start = -1
        self.snippet_end = -1

    def on_state_changed(self, state):
        """Connect/disconnect sig_key_pressed signal."""
        if state:
            self.editor.sig_key_pressed.connect(self._on_key_pressed)
        else:
            self.editor.sig_key_pressed.disconnect(self._on_key_pressed)
