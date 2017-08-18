# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
#

"""
Tests for the autoindent features
"""

# Third party imports
from qtpy.QtGui import QTextCursor
import pytest

# Local imports
from spyder.utils.qthelpers import qapplication
from spyder.plugins.editor.widgets.codeeditor import CodeEditor
from spyder.plugins.editor.api.folding import print_tree


# --- Fixtures
# -----------------------------------------------------------------------------
@pytest.fixture()
def get_fold_levels():
    """setup editor and return fold levels."""
    app = qapplication()
    editor = CodeEditor(parent=None)
    editor.setup_editor(language='Python')

    text = ('# dummy test file\n'
            'class a():\n'  # fold-block level-0
            '    self.b = 1\n'
            '    print(self.b)\n'
            '    \n'
            '    def some_method(self):\n'  # fold-block level-1
            '        self.b = 3\n'
            '\n'
            '    def other_method(self):\n'  # fold-block level-1
            '\n' # a blank line (should be ignored)
            '  # a comment with arbitrary indentation\n' # should be ignored
            '         a = (1,\n'  # fold-block level-2
            '              2,\n'
            '              3)\n'
            )

    editor.set_text(text)
    return print_tree(editor, return_list=True)

# --- Tests
# -----------------------------------------------------------------------------
def test_simple_folding(get_fold_levels):
    assert get_fold_levels == [[2, 0, 'V'], 
                                 [6, 1, 'V'],
                                 [9, 1, 'V'],
                                 [12, 2, 'V']]


