# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License


# Standard library imports
import io
import tokenize

# Third party imports
from qtpy.QtGui import QTextDocument
from qtpy.QtGui import QTextCursor
from qtpy.QtWidgets import QComboBox

import pytest
from pytestqt import qtbot

# Local imports
from spyder.plugins.editor.panels import classfunctiondropdown as cfd
from spyder.plugins.outlineexplorer.api import OutlineExplorerData as OED
from spyder.utils.syntaxhighlighters import PythonSH
from spyder.plugins.editor.utils.folding import FoldScope
from spyder.plugins.editor.utils.editor import TextBlockHelper
from spyder.plugins.editor.utils.folding import IndentFoldDetector


# ---------------------------------------------------------------------------
# Helper Functions
# ---------------------------------------------------------------------------
def create_editor(editor_bot, text):
    _, editor = editor_bot
    editor.set_text(text)
    return editor


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------
@pytest.fixture
def qcombobox_bot(qtbot):
    widget = QComboBox()
    qtbot.addWidget(widget)
    return qtbot, widget

@pytest.fixture
def editor_bot(qtbot):
    from spyder.plugins.editor.widgets.editor import codeeditor
    widget = codeeditor.CodeEditor(None)
    widget.setup_editor(linenumbers=True,
                        markers=True,
                        tab_mode=False,
                        show_blanks=True,
                        color_scheme='Zenburn')
    widget.setup_editor(language='Python')
    qtbot.addWidget(widget)
    widget.show()
    return qtbot, widget


# ---------------------------------------------------------------------------
# Examples to Test Against
# ---------------------------------------------------------------------------
complicated = """# -*- coding: utf-8 -*-            # Line 0
def func1():                                        # Line 1
    pass                                            # Line 2

print("0")                                          # Line 4

def func2():                                        # Line 6
    print("a")                                      # Line 7

    def func3():                                    # Line 9
                    print("b")                      # Line 10
                    print("c")                      # Line 11

                    def func4():                    # Line 13
                        print("d")                  # Line 14
    print("aaa")                                    # Line 15
print("e")                                          # Line 16

print("d")                                          # Line 18

def _goodbye():                                     # Line 20
    print(a)                                        # Line 21
    print(a)                                        # Line 22
"""

simple = """# -*- coding: utf-8 -*-
def my_add():
    a = 1
    b = 2
    return a + b

print("b")

class MyClass():
    def __init__(self):
        a = 1
        b = 2
"""


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------
def test_get_fold_levels(editor_bot):

    editor = create_editor(editor_bot, complicated)

    folds = cfd._get_fold_levels(editor)

    expected = [
        (1, 2),
        (6, 15),
        (9, 14),
        (13, 14),
        (20, 22),
    ]

    for fold, expected_range in zip(folds, expected):
        assert fold.range == expected_range


def test_split_classes_and_methods(editor_bot):
    editor = create_editor(editor_bot, simple)
    folds = cfd._get_fold_levels(editor)
    classes, functions = cfd._split_classes_and_methods(folds)
    assert len(classes) == 1
    assert len(functions) == 2


def test_get_parents(editor_bot):
    editor = create_editor(editor_bot, simple)
    folds = cfd._get_fold_levels(editor)
    assert len(cfd._get_parents(folds, 1)) == 1
    assert len(cfd._get_parents(folds, 2)) == 1
    assert len(cfd._get_parents(folds, 6)) == 0
    assert len(cfd._get_parents(folds, 10)) == 2


class TestFoldScopeHelper(object):

    test_case = """# -*- coding: utf-8 -*-
def my_add():
    a = 1
    b = 2
    return a + b
"""

    doc = QTextDocument(test_case)
    sh = PythonSH(doc, color_scheme='Spyder')
    sh.fold_detector = IndentFoldDetector()
    sh.rehighlightBlock(doc.firstBlock())
    block = doc.firstBlock()
    block = block.next()
    TextBlockHelper.set_fold_trigger(block, True)
    fold_scope = FoldScope(block)
    oed = block.userData().oedata

    def test_fold_scope_helper(self):
        fsh = cfd.FoldScopeHelper(None, None)
        assert isinstance(fsh, cfd.FoldScopeHelper)

    def test_fold_scope_helper_str(self):
        fsh = cfd.FoldScopeHelper(self.fold_scope, self.oed)
        assert "my_add" in str(fsh)

    def test_fold_scope_helper_str_with_parents(self):
        fsh = cfd.FoldScopeHelper(self.fold_scope, self.oed)
        fsh.parents = ["fake parent list!"]
        assert "parents:" in str(fsh)

    def test_fold_scope_helper_repr(self):
        fsh = cfd.FoldScopeHelper(self.fold_scope, self.oed)
        assert "(at 0x" in repr(fsh)

    def test_fold_scope_helper_properties(self):
        fsh = cfd.FoldScopeHelper(self.fold_scope, self.oed)
        assert fsh.range == (1, 4)
        assert fsh.start_line == 1
        assert fsh.end_line == 4
        assert fsh.name == "my_add"
        assert fsh.line == 1
        assert fsh.def_type == OED.FUNCTION_TOKEN
