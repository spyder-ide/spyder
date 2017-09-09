# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
#
"""Tests for close quotes."""

# Third party imports
import pytest
from qtpy.QtCore import Qt

# Local imports
from spyder.utils.qthelpers import qapplication
from spyder.widgets.sourcecode.codeeditor import CodeEditor
from spyder.widgets.sourcecode.extensions.snippets import SnippetsExtension

# imports from snippet tests
from spyder.utils.tests.test_snippets import (snippet_manager,
                                              snippet_test_result,
                                              snippets_dir)

# --- Fixtures
# -----------------------------------------------------------------------------
@pytest.fixture
def editor_snippets(snippet_manager):
    """Set up Editor with some test snippets."""
    app = qapplication()
    editor = CodeEditor(parent=None)
    kwargs = {}
    kwargs['language'] = 'Python'
    editor.setup_editor(**kwargs)

    # Replace  snippet manager for a fixture with test snippets
    snippets_extension = editor.editor_extensions.get(SnippetsExtension)
    snippets_extension.snippet_manager = snippet_manager

    return editor


# --- Tests
# -----------------------------------------------------------------------------
def test_snippet(qtbot, editor_snippets):
    """Test insertion of snippet."""
    editor = editor_snippets

    qtbot.keyClicks(editor, 'test')

    # press tab and get completion
    with qtbot.waitSignal(editor.textChanged, timeout=2000):
        qtbot.keyPress(editor, Qt.Key_Tab)

    assert editor.toPlainText().strip() == snippet_test_result

    # replace the variables
    qtbot.keyClicks(editor, '10')
    qtbot.keyPress(editor, Qt.Key_Tab)
    qtbot.keyClicks(editor, 'print(i)')
    assert editor.toPlainText().strip() == "for i in range(10):\n    print(i)"


if __name__ == '__main__':
    pytest.main()
