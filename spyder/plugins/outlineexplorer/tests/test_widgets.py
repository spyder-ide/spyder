# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
#

"""
Tests for editortool.py
"""
# Standard Libray Imports
import json
import os.path as osp
from textwrap import dedent
from unittest.mock import MagicMock

# Third party imports
import pytest
from qtpy.QtCore import Qt

# Local imports
from spyder.plugins.outlineexplorer.editor import OutlineExplorerProxyEditor
from spyder.plugins.outlineexplorer.widgets import (
    OutlineExplorerWidget, FileRootItem, SymbolStatus, TreeItem,
    OutlineExplorerToolbuttons)
from spyder.plugins.editor.widgets.codeeditor import CodeEditor

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

CODE = """# -*- coding: utf-8 -*-

    def function0(x):
        return x

    # %% Top level 1
    def function1(x):
        return x

    x = function1(x)

    # %%% Cell Level 1-1
    q = 3
    w = 'word'

    # %%% Cell Level 1-2
    def function2(x):
        def inside(x):
            return x
        return x

    y = function2(x)

    # %%%% Cell Level 2
    class Class2(x):
        def __init__(x):
            return x
        async def medthod1(x):
            if x:
                return x

    # %%%%%% Cell level 4
    def function4(x):
        return x

    # %%%%% Cell Level 3
    def function5(x):
        return x

    # %%%%%%%% Cell Level 6
    class Class3(x):
        def __init__(x):
            return x
        def medthod1(x):
            if x:
                return x

    # %% Top level 2
    class Class4(x):
        def __init__(x):
            return x
        def medthod1(x):
            if x:
                return x

    z = Class1(x)

    if __name__ == "__main__":

    # %% MGroup3
        def function6(x):
            return x
    # %%% MGroup4
        x = 'test'
    # %% Unnamed Cell

    # %%%

    # %% Unnamed Cell

    # %% Unnamed Cell, #1

    # %%% Unnamed Cell, #1

    # %%

    # %% a

    def a():
        pass

    # %% a

    # %% b

    def b():
        pass
"""


# ---- Qt Test Fixtures
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

        editor.update_outline_info(symbol_info)
        qtbot.addWidget(outlineexplorer)
        return outlineexplorer, expected_tree
    return _create_outlineexplorer


# ---- Test OutlineExplorerWidget
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
    editor = tree_widget.current_editor

    root_item = tree_widget.get_top_level_items()[0]
    root_ref = root_item.ref
    filename = osp.basename(root_ref.name)
    root_tree = {filename: []}
    stack = [(root_tree[filename], node) for node in root_ref.children]

    while len(stack) > 0:
        parent_tree, node = stack.pop(0)
        this_tree = {node.name: []}
        parent_tree.append(this_tree)
        this_stack = [(this_tree[node.name], child) for child in node.children]
        stack = this_stack + stack

    assert root_tree == expected_tree


def test_go_to_cursor_position(create_outlineexplorer, qtbot):
    """
    Test that clicking on the 'Go to cursor position' button located in the
    toolbar of the outline explorer is working as expected.

    Regression test for spyder-ide/spyder#7729.
    """
    outlineexplorer, _ = create_outlineexplorer('text')
    # Move the mouse cursor in the editor to line 31 :
    editor = outlineexplorer.treewidget.current_editor
    editor._editor.go_to_line(15)
    assert editor._editor.get_text_line(15) == "        return 2"

    # Click on the 'Go to cursor position' button of the outline explorer's
    # toolbar :
    assert outlineexplorer.treewidget.currentItem() is None
    qtbot.mouseClick(
        outlineexplorer.get_toolbutton(OutlineExplorerToolbuttons.GoToCursor),
        Qt.LeftButton)
    assert outlineexplorer.treewidget.currentItem().text(0) == 'inner'


def test_follow_cursor(create_outlineexplorer, qtbot):
    """
    Test that the cursor is followed.
    """
    outlineexplorer, _ = create_outlineexplorer('text', follow_cursor=True)
    # Move the mouse cursor in the editor to line 45 :
    editor = outlineexplorer.treewidget.current_editor
    editor._editor.go_to_line(45)
    assert editor._editor.get_text_line(45) == "        self.x = 2"
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
    assert outlineexplorer.treewidget.currentItem().text(0) == 'b'


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
    assert outlineexplorer.treewidget.currentItem() is None
    qtbot.mouseClick(
        outlineexplorer.get_toolbutton(OutlineExplorerToolbuttons.GoToCursor),
        Qt.LeftButton)
    assert outlineexplorer.treewidget.currentItem().text(0) == filename


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
    assert outlineexplorer.treewidget.currentItem() is None
    qtbot.mouseClick(
        outlineexplorer.get_toolbutton(OutlineExplorerToolbuttons.GoToCursor),
        Qt.LeftButton)
    assert outlineexplorer.treewidget.currentItem().text(0) == 'method1'


@pytest.mark.skip(reason='Cell support is disabled temporarily')
def test_code_cell_grouping(create_outlineexplorer):
    """
    Test to assert the outline explorer is initializing correctly and
    is showing the expected number of items, the expected type of items, and
    the expected text for each item. In addition this tests ancestry, code
    cells comments, code cell grouping and disabling this feature.
    """
    outlineexplorer = create_outlineexplorer(dedent(CODE), 'test_file.py')
    assert outlineexplorer

    expected_results = [
        ('test_file.py', FileRootItem),
        ('function0', FunctionItem, 'test_file.py', 'test_file.py', False),
        ('Top level 1', CellItem, 'test_file.py', 'test_file.py'),
        ('function1', FunctionItem, 'Top level 1', 'test_file.py', False),
        ('Cell Level 1-1', CellItem, 'Top level 1', 'test_file.py'),
        ('Cell Level 1-2', CellItem, 'Top level 1', 'test_file.py'),
        ('function2', FunctionItem, 'Cell Level 1-2', 'test_file.py', False),
        ('inside', FunctionItem, 'function2', 'function2', False),
        ('Cell Level 2', CellItem, 'Cell Level 1-2', 'test_file.py'),
        ('Class2', ClassItem, 'Cell Level 2', 'test_file.py'),
        ('__init__', FunctionItem, 'Class2', 'Class2', True),
        ('medthod1', FunctionItem, 'Class2', 'Class2', True),
        ('Cell level 4', CellItem, 'Cell Level 2', 'test_file.py'),
        ('function4', FunctionItem, 'Cell level 4', 'test_file.py', False),
        ('Cell Level 3', CellItem, 'Cell Level 1-2', 'test_file.py'),
        ('function5', FunctionItem, 'Cell Level 3', 'test_file.py', False),
        ('Cell Level 6', CellItem, 'Cell Level 3', 'test_file.py'),
        ('Class3', ClassItem, 'Cell Level 6', 'test_file.py'),
        ('__init__', FunctionItem, 'Class3', 'Class3', True),
        ('medthod1', FunctionItem, 'Class3', 'Class3', True),
        ('Top level 2', CellItem, 'test_file.py', 'test_file.py'),
        ('Class4', ClassItem, 'Top level 2', 'test_file.py'),
        ('__init__', FunctionItem, 'Class4', 'Class4', True),
        ('medthod1', FunctionItem, 'Class4', 'Class4', True),
        ('MGroup3', CellItem, 'test_file.py', 'test_file.py'),
        ('function6', FunctionItem, 'MGroup3', 'MGroup3', False),
        ('MGroup4', CellItem, 'MGroup3', 'test_file.py'),
        ('Unnamed Cell, #2', CellItem, 'test_file.py', 'test_file.py'),
        ('Unnamed Cell, #3', CellItem, 'Unnamed Cell, #2', 'test_file.py'),
        ('Unnamed Cell, #4', CellItem, 'test_file.py', 'test_file.py'),
        ('Unnamed Cell, #1, #1', CellItem, 'test_file.py', 'test_file.py'),
        ('Unnamed Cell, #1, #2', CellItem, 'Unnamed Cell, #1, #1',
         'test_file.py'),
        ('Unnamed Cell, #5', CellItem, 'test_file.py', 'test_file.py'),
        ('a, #1', CellItem, 'test_file.py', 'test_file.py'),
        ('a', FunctionItem, 'a, #1', 'test_file.py', False),
        ('a, #2', CellItem, 'test_file.py', 'test_file.py'),
        ('b', CellItem, 'test_file.py', 'test_file.py'),
        ('b', FunctionItem, 'b', 'test_file.py', False),
        ]

    outlineexplorer.treewidget.expandAll()
    tree_widget = outlineexplorer.treewidget
    cell_items = tree_widget.get_top_level_items() + tree_widget.get_items()

    # Assert that the expected number, text, ancestry and type of cell items is
    # displayed in the tree.
    assert len(cell_items) == len(expected_results)
    for item, expected_result in zip(cell_items, expected_results):
        assert item.text(0) == expected_result[0]
        assert type(item) == expected_result[1]
        if type(item) != FileRootItem:
            assert item.parent().text(0) == expected_result[2]
        if type(item) == FunctionItem:
            assert item.is_method() == expected_result[4]

    # Disable cell groups
    tree_widget.toggle_group_cells(False)
    tree_widget.expandAll()
    flat_items = tree_widget.get_top_level_items() + tree_widget.get_items()

    # Assert that the expected number, text, ancestry and type of flat items is
    # displayed in the tree.
    assert len(flat_items) == len(expected_results)
    for item, expected_result in zip(flat_items, expected_results):
        assert item.text(0) == expected_result[0]
        assert type(item) == expected_result[1]
        if type(item) != FileRootItem:
            assert item.parent().text(0) == expected_result[3]
        if type(item) == FunctionItem:
            assert item.is_method() == expected_result[4]

    # Change back to cell groups
    tree_widget.toggle_group_cells(True)
    tree_widget.expandAll()
    cell_items2 = tree_widget.get_top_level_items() + tree_widget.get_items()

    # Assert that the expected number, text, ancestry and type of flat items is
    # displayed in the tree.
    assert len(cell_items2) == len(expected_results)
    for item, expected_result in zip(cell_items2, expected_results):
        assert item.text(0) == expected_result[0]
        assert type(item) == expected_result[1]
        if type(item) != FileRootItem:
            assert item.parent().text(0) == expected_result[2]
        if type(item) == FunctionItem:
            assert item.is_method() == expected_result[4]

# Code used to create expected_results
# =============================================================================
#     for item in cell_items2:
#         if type(item) == FunctionItem:
#             print(f"('{item.text(0)}', {type(item).__name__}, "
#                   f"'{item.parent().text(0)}', {item.is_method()}),")
#         elif type(item) == FileRootItem:
#             print(f"('{item.text(0)}', {type(item).__name__}),")
#         else:
#             print(f"('{item.text(0)}', {type(item).__name__}, "
#                   f"'{item.parent().text(0)}'),")
# =============================================================================


if __name__ == "__main__":
    import os
    pytest.main(['-x', os.path.basename(__file__), '-v', '-rw'])
