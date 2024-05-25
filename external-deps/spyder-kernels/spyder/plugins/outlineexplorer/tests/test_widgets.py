# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
#

"""
Tests for the Outline explorer widgets.
"""

# Standard Libray Imports
import json
import os.path as osp
import sys
from unittest.mock import MagicMock

# Third party imports
from flaky import flaky
import pytest
from qtpy.QtCore import Qt

# Local imports
from spyder.plugins.outlineexplorer.editor import OutlineExplorerProxyEditor
from spyder.plugins.outlineexplorer.main_widget import (
    OutlineExplorerWidget, OutlineExplorerToolbuttons)
from spyder.plugins.editor.widgets.codeeditor import CodeEditor


# ---- Constants
HERE = osp.abspath(osp.dirname(__file__))
ASSETS = osp.join(HERE, 'assets')
SUFFIX = 'test_widgets'

AVAILABLE_CASES = ['text']
CASES = {
    case: {
        'file': osp.join(ASSETS, '{0}_{1}.py'.format(case, SUFFIX)),
        'data': osp.join(ASSETS, '{0}_{1}.json'.format(case, SUFFIX)),
        'tree': osp.join(ASSETS, '{0}_exp_{1}.json'.format(case, SUFFIX))
    }
    for case in AVAILABLE_CASES
}


# ---- Fixtures
@pytest.fixture
def create_outlineexplorer(qtbot):
    def _create_outlineexplorer(case, follow_cursor=False):
        case_info = CASES[case]
        filename = case_info['file']
        with open(case_info['file'], 'r') as f:
            text = f.read()

        symbol_info = json.load(open(case_info['data'], 'r'))
        expected_tree = json.load(open(case_info['tree'], 'r'))

        code_editor = CodeEditor(None)
        code_editor.set_language('py', filename)
        code_editor.show()
        code_editor.set_text(text)

        editor = OutlineExplorerProxyEditor(code_editor, filename)
        plugin_mock = MagicMock()
        plugin_mock.NAME = 'outline_explorer'

        outlineexplorer = OutlineExplorerWidget(
            'outline_explorer', plugin_mock, None)
        outlineexplorer.setup()

        outlineexplorer.set_conf('show_fullpath', True)
        outlineexplorer.set_conf('show_comments', True)
        outlineexplorer.set_conf('group_cells', True)
        outlineexplorer.set_conf('display_variables', True)
        outlineexplorer.set_conf('follow_cursor', follow_cursor)

        outlineexplorer.register_editor(editor)
        outlineexplorer.set_current_editor(editor, False, False)
        outlineexplorer.show()
        outlineexplorer.setFixedSize(400, 350)
        outlineexplorer.treewidget.is_visible = True

        editor.update_outline_info(symbol_info)
        qtbot.addWidget(outlineexplorer)
        qtbot.addWidget(code_editor)
        return outlineexplorer, expected_tree
    return _create_outlineexplorer


# ---- Tests
@pytest.mark.parametrize('case', AVAILABLE_CASES)
def test_outline_explorer(case, create_outlineexplorer):
    """
    Test to assert the outline explorer is initializing correctly and
    is showing the expected number of items, the expected type of items, and
    the expected text for each item.
    """
    outlineexplorer, expected_tree = create_outlineexplorer(case)
    assert outlineexplorer

    outlineexplorer.treewidget.expandAll()
    tree_widget = outlineexplorer.treewidget

    root_item = tree_widget.get_top_level_items()[0]
    root_ref = root_item.ref
    filename = osp.basename(root_ref.name)
    root_tree = {filename: []}
    stack = [(root_tree[filename], node) for node in root_ref.children]

    while len(stack) > 0:
        parent_tree, node = stack.pop(0)
        this_tree = {node.name: [], 'kind': node.kind}
        parent_tree.append(this_tree)
        this_stack = [(this_tree[node.name], child) for child in node.children]
        stack = this_stack + stack

    assert root_tree == expected_tree


@pytest.mark.skipif(sys.platform == 'darwin', reason="Fails on Mac")
def test_go_to_cursor_position(create_outlineexplorer, qtbot):
    """
    Test that clicking on the 'Go to cursor position' button located in the
    toolbar of the outline explorer is working as expected.

    Regression test for spyder-ide/spyder#7729.
    """
    outlineexplorer, _ = create_outlineexplorer('text')

    # Move the mouse cursor in the editor to line 15
    editor = outlineexplorer.treewidget.current_editor
    editor._editor.go_to_line(15)
    assert editor._editor.get_text_line(14) == "    def inner():"

    # Click on the 'Go to cursor position' button of the outline explorer's
    # toolbar :
    assert outlineexplorer.treewidget.currentItem() is None
    qtbot.mouseClick(
        outlineexplorer.get_toolbutton(OutlineExplorerToolbuttons.GoToCursor),
        Qt.LeftButton)
    assert outlineexplorer.treewidget.currentItem().text(0) == 'inner'


@flaky(max_runs=10)
def test_follow_cursor(create_outlineexplorer, qtbot):
    """
    Test that the cursor is followed.
    """
    outlineexplorer, _ = create_outlineexplorer('text', follow_cursor=True)

    # Move the mouse cursor in the editor to line 52
    editor = outlineexplorer.treewidget.current_editor
    editor._editor.go_to_line(52)
    assert editor._editor.get_text_line(51) == \
           "        super(Class1, self).__init__()"

    # __init__ is collapsed
    assert outlineexplorer.treewidget.currentItem().text(0) == '__init__'

    # Go to cursor to open the cursor
    qtbot.mouseClick(
        outlineexplorer.get_toolbutton(OutlineExplorerToolbuttons.GoToCursor),
        Qt.LeftButton)

    # Check if follows
    editor._editor.go_to_line(1)
    text = outlineexplorer.treewidget.currentItem().text(0)
    assert text == CASES['text']['file']

    editor._editor.go_to_line(37)
    assert editor._editor.get_text_line(36) == "# %%%% cell level 3"
    assert outlineexplorer.treewidget.currentItem().text(0) == 'cell level 3'


@flaky(max_runs=10)
def test_go_to_cursor_position_with_new_file(create_outlineexplorer, qtbot):
    """
    Test that clicking on the 'Go to cursor position' button located in the
    toolbar of the outline explorer is working as expected for newly created
    files.

    Regression test for spyder-ide/spyder#8510.
    """
    # text = "# -*- coding: utf-8 -*-\nSome newly created\nPython file."
    outlineexplorer, _ = create_outlineexplorer('text')

    # Click on the 'Go to cursor position' button of the outline explorer's
    # toolbar :
    filename = CASES['text']['file']
    qtbot.mouseClick(
        outlineexplorer.get_toolbutton(OutlineExplorerToolbuttons.GoToCursor),
        Qt.LeftButton)
    assert outlineexplorer.treewidget.currentItem().text(0) == filename


@flaky(max_runs=10)
def test_go_to_last_item(create_outlineexplorer, qtbot):
    """
    Test that clicking on the 'Go to cursor position' button located in the
    toolbar of the outline explorer is working as expected when the cursor
    is located in the editor under the last item of the outline tree widget.

    Regression test for spyder-ide/spyder#7744.
    """
    outlineexplorer, _ = create_outlineexplorer('text')

    # Move the mouse cursor in the editor to the last line :
    editor = outlineexplorer.treewidget.current_editor
    line_count = editor._editor.document().blockCount() - 2
    editor._editor.go_to_line(line_count)
    assert editor._editor.get_text_line(line_count) == "        pass"

    # Click on the 'Go to cursor position' button of the outline explorer's
    # toolbar :
    qtbot.mouseClick(
        outlineexplorer.get_toolbutton(OutlineExplorerToolbuttons.GoToCursor),
        Qt.LeftButton)
    assert outlineexplorer.treewidget.currentItem().text(0) == 'method1'


@flaky(max_runs=10)
def test_display_variables(create_outlineexplorer, qtbot):
    """
    Test that clicking on the 'Display variables and attributes' button located in the
    toolbar of the outline explorer is working as expected by updating the tree widget.

    Regression test for spyder-ide/spyder#21456.
    """
    outlineexplorer, _ = create_outlineexplorer('text')

    editor = outlineexplorer.treewidget.current_editor
    state = outlineexplorer.treewidget.display_variables

    editor_id = editor.get_id()

    initial_tree = outlineexplorer.treewidget.editor_tree_cache[editor_id]

    outlineexplorer.treewidget.toggle_variables(not state)

    first_toggle_tree = outlineexplorer.treewidget.editor_tree_cache[editor_id]

    assert first_toggle_tree != initial_tree

    outlineexplorer.treewidget.toggle_variables(state)

    second_toggle_tree = outlineexplorer.treewidget.editor_tree_cache[editor_id]

    assert (second_toggle_tree != first_toggle_tree) and (
        second_toggle_tree == initial_tree)


if __name__ == "__main__":
    import os
    pytest.main(['-x', os.path.basename(__file__), '-v', '-rw'])
