# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
#

"""
Tests for EditorStack keyboard shortcuts.
"""

# Standard library imports
import os
import sys
try:
    from unittest.mock import Mock
except ImportError:
    from mock import Mock  # Python 2

# Third party imports
import pytest
from qtpy.QtCore import Qt
from qtpy.QtWidgets import QApplication

# Local imports
from spyder.plugins.editor.widgets.editor import EditorStack
from spyder.config.gui import get_shortcut
from spyder.plugins.editor.widgets.codeeditor import GoToLineDialog


# ---- Qt Test Fixtures
@pytest.fixture
def editor_bot(qtbot):
    """
    Set up EditorStack with CodeEditors containing some Python code.
    The cursor is at the empty line below the code.
    """
    editorstack = EditorStack(None, [])
    editorstack.set_introspector(Mock())
    editorstack.set_find_widget(Mock())
    editorstack.set_io_actions(Mock(), Mock(), Mock(), Mock())
    editorstack.close_action.setEnabled(False)
    editorstack.new('foo.py', 'utf-8', 'Line1\nLine2\nLine3\nLine4')

    qtbot.addWidget(editorstack)
    editorstack.show()
    editorstack.go_to_line(1)

    return editorstack, qtbot


# ---- Tests
def test_default_keybinding_values():
    """
    Assert that the default Spyder keybindings for the keyboard shorcuts
    are as expected. This is required because we do not use the keybindings
    saved in Spyder's config to simulate the user keyboard action, due to
    the fact that it is complicated to convert and pass reliably a sequence
    of key strings to qtbot.keyClicks.
    """
    # Assert default keybindings.
    assert get_shortcut('editor', 'start of document') == 'Ctrl+Home'
    assert get_shortcut('editor', 'end of document') == 'Ctrl+End'
    assert get_shortcut('editor', 'delete') == 'Del'
    assert get_shortcut('editor', 'undo') == 'Ctrl+Z'
    assert get_shortcut('editor', 'redo') == 'Ctrl+Shift+Z'
    assert get_shortcut('editor', 'copy') == 'Ctrl+C'
    assert get_shortcut('editor', 'paste') == 'Ctrl+V'
    assert get_shortcut('editor', 'cut') == 'Ctrl+X'
    assert get_shortcut('editor', 'select all') == 'Ctrl+A'
    assert get_shortcut('editor', 'delete line') == 'Ctrl+D'
    assert get_shortcut('editor', 'transform to lowercase') == 'Ctrl+U'
    assert get_shortcut('editor', 'transform to uppercase') == 'Ctrl+Shift+U'
    assert get_shortcut('editor', 'go to line') == 'Ctrl+L'

