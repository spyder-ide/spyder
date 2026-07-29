# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
#

"""
Tests syncing between the EditorStack and OutlineExplorerWidget.
"""

# Standard library imports
import os
import json
import os.path as osp

# Qt imports
from qtpy.QtCore import Qt
from qtpy.QtGui import QTextCursor

# Third party imports
import pytest

# Local imports
from spyder.plugins.editor.widgets.codeeditor.tests.conftest import CASES

def get_tree_elements(treewidget):
    """Get elements present in the Outline tree widget."""
    root_item = treewidget.get_top_level_items()[0]
    root_ref = root_item.ref
    filename = osp.basename(root_ref.name)
    root_tree = {filename: []}
    stack = [(root_tree[filename], node) for node in root_ref.children]

    while len(stack) > 0:
        parent_tree, node = stack.pop(0)
        this_tree = {node.name: []}
        parent_tree.append(this_tree)
        this_stack = [(this_tree[node.name], child)
                      for child in node.children]
        stack = this_stack + stack
    return root_tree


def wait_for_tree(qtbot, treewidget, expected):
    """
    Wait and check that the Outline tree is as `expected`.
    """
    tree_elements = None

    def check_tree():
        nonlocal tree_elements
        tree_elements = get_tree_elements(treewidget)
        return tree_elements == expected

    try:
        qtbot.waitUntil(
            check_tree, timeout=30000
        )
    except Exception:
        assert tree_elements == expected


@pytest.mark.order(2)
def test_editor_outlineexplorer(qtbot, completions_codeeditor_outline):
    """Tests that the outline explorer reacts to editor changes."""
    code_editor, outlineexplorer = completions_codeeditor_outline
    treewidget = outlineexplorer.treewidget
    treewidget.is_visible = True

    case_info = CASES['text']
    filename = case_info['file']
    tree_file = case_info['tree']

    with open(filename, 'r') as f:
        lines = f.read()

    with open(tree_file, 'r') as f:
        trees = json.load(f)

    code_editor.toggle_automatic_completions(False)
    code_editor.toggle_code_snippets(False)

    # Set cursor to start
    code_editor.set_text('')
    code_editor.go_to_line(1)

    # Put example text in editor
    code_editor.set_text(lines)

    # Check that the outline tree was initialized successfully
    tree = trees[0]
    wait_for_tree(qtbot, treewidget, tree)

    # Remove "d" symbol
    code_editor.go_to_line(14)
    cursor = code_editor.textCursor()
    start = code_editor.get_position_line_number(13, -1)
    end = code_editor.get_position_line_number(17, 0)
    cursor.setPosition(start)
    cursor.setPosition(end, QTextCursor.KeepAnchor)
    code_editor.setTextCursor(cursor)
    code_editor.cut()

    tree = trees[1]
    wait_for_tree(qtbot, treewidget, tree)

    # Add "d" symbol elsewhere
    code_editor.go_to_line(36)

    with qtbot.waitSignal(
            code_editor.completions_response_signal, timeout=30000):
        qtbot.keyPress(code_editor, Qt.Key_Return)
        qtbot.keyPress(code_editor, Qt.Key_Return)

    qtbot.keyPress(code_editor, Qt.Key_Up)
    code_editor.paste()

    tree = trees[2]
    wait_for_tree(qtbot, treewidget, tree)

    # Move method1
    code_editor.go_to_line(56)
    cursor = code_editor.textCursor()
    start = code_editor.get_position_line_number(55, -1)
    end = code_editor.get_position_line_number(57, -1)
    cursor.setPosition(start)
    cursor.setPosition(end, QTextCursor.KeepAnchor)
    code_editor.setTextCursor(cursor)
    code_editor.cut()

    tree = trees[3]
    wait_for_tree(qtbot, treewidget, tree)

    # Add method1
    code_editor.go_to_line(49)

    with qtbot.waitSignal(
            code_editor.completions_response_signal, timeout=30000):
        qtbot.keyPress(code_editor, Qt.Key_Return)
        qtbot.keyPress(code_editor, Qt.Key_Return)

    qtbot.keyPress(code_editor, Qt.Key_Up)
    code_editor.paste()

    tree = trees[4]
    wait_for_tree(qtbot, treewidget, tree)

    # Add attribute "y"
    code_editor.go_to_line(48)
    cursor = code_editor.textCursor()
    cursor.movePosition(QTextCursor.EndOfBlock)
    code_editor.setTextCursor(cursor)

    with qtbot.waitSignal(
            code_editor.completions_response_signal, timeout=30000):
        qtbot.keyPress(code_editor, Qt.Key_Return)
        qtbot.keyClicks(code_editor, 'self.y = None')
        qtbot.keyPress(code_editor, Qt.Key_Return)

    with qtbot.waitSignal(treewidget.sig_tree_updated, timeout=30000):
        code_editor.request_symbols()

    tree = trees[5]
    wait_for_tree(qtbot, treewidget, tree)


@pytest.mark.order(2)
def test_outline_ignores_superseded_symbols(qtbot,
                                            completions_codeeditor_outline):
    """
    Test that the tree is not updated with symbols of a partially typed
    statement.

    Typing `=` requests a signature, which sends the text typed so far to the
    server. If symbols are requested for that text (i.e. while the statement is
    still incomplete), its response must not overwrite the tree because a newer
    request was sent in the meantime.
    """
    code_editor, outlineexplorer = completions_codeeditor_outline
    treewidget = outlineexplorer.treewidget
    treewidget.is_visible = True

    code_editor.toggle_automatic_completions(False)
    code_editor.toggle_code_snippets(False)

    code_editor.set_text(
        "class Class1:\n"
        "    def __init__(self):\n"
        "        self.x = 2\n"
    )
    qtbot.wait(3000)

    # Set cursor at the end of `self.x = 2`
    code_editor.go_to_line(3)
    cursor = code_editor.textCursor()
    cursor.movePosition(QTextCursor.EndOfBlock)
    code_editor.setTextCursor(cursor)

    with qtbot.waitSignal(
            code_editor.completions_response_signal, timeout=30000):
        qtbot.keyPress(code_editor, Qt.Key_Return)
        qtbot.keyClicks(code_editor, 'self.y =')

        # Request symbols for the incomplete statement, which is what the
        # timer to sync symbols and folding does when it times out here.
        code_editor.sync_symbols_and_folding()

        qtbot.keyClicks(code_editor, ' None')
        qtbot.keyPress(code_editor, Qt.Key_Return)

    with qtbot.waitSignal(treewidget.sig_tree_updated, timeout=30000):
        code_editor.request_symbols()

    root_tree = get_tree_elements(treewidget)
    assert root_tree == {
        'test.py': [
            {'Class1': [{'__init__': [{'x': []}, {'y': []}]}]}
        ]
    }


@pytest.mark.order(2)
def test_empty_file(qtbot, completions_codeeditor_outline):
    """
    Test that the outline explorer is updated correctly when
    it's associated file is empty.
    """
    code_editor, outlineexplorer = completions_codeeditor_outline
    treewidget = outlineexplorer.treewidget
    treewidget.is_visible = True

    code_editor.toggle_automatic_completions(False)
    code_editor.toggle_code_snippets(False)

    # Set empty contents
    code_editor.set_text('')
    code_editor.go_to_line(1)
    qtbot.wait(3000)

    # Assert the spinner is not shown.
    assert not outlineexplorer._spinner.isSpinning()

    # Add some content
    code_editor.set_text("""
def foo():
    a = 10
    return a
""")

    tree = {'test.py': [{'foo': [{'a': []}]}]}
    wait_for_tree(qtbot, treewidget, tree)

    # Remove content
    code_editor.selectAll()

    qtbot.keyPress(code_editor, Qt.Key_Delete)

    # Assert the tree is empty and the spinner is not shown.
    tree = {'test.py': []}
    wait_for_tree(qtbot, treewidget, tree)
    assert not outlineexplorer._spinner.isSpinning()


if __name__ == "__main__":
    pytest.main([os.path.basename(__file__), '-vv', '-rw'])
