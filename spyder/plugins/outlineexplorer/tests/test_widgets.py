# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
#

"""
Tests for editortool.py
"""
# Standard Libray Imports
from textwrap import dedent

# Third party imports
import pytest

# Local imports
from spyder.plugins.outlineexplorer.editor import OutlineExplorerProxyEditor
from spyder.plugins.outlineexplorer.widgets import (OutlineExplorerWidget,
    FileRootItem, FunctionItem, CommentItem, CellItem, ClassItem)
from spyder.plugins.editor.widgets.codeeditor import CodeEditor


text = ("# -*- coding: utf-8 -*-\n"
        "\n"
        "# %% functions\n"
        "\n"
        "\n"
        "# ---- func 1 and 2\n"
        "\n"
        "def func1():\n"
        "    for i in range(3):\n"
        "        print(i)\n"
        "\n"
        "\n"
        "def func2():\n"
        "    if True:\n"
        "        pass\n"
        "\n"
        "\n"
        "# ---- func 3\n"
        "\n"
        "def func3():\n"
        "    pass\n"
        "\n"
        "\n"
        "# %% classes\n"
        "\n"
        "class class1(object):\n"
        "\n"
        "    def __ini__(self):\n"
        "        super(class1, self).__init__()\n"
        "\n"
        "    def method1(self):\n"
        "        if False:\n"
        "            pass\n"
        "\n"
        "    def method2(self):\n"
        "        try:\n"
        "            assert 2 == 3\n"
        "        except AssertionError:\n"
        "            pass")

code = """# -*- coding: utf-8 -*-

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
        def medthod1(x):
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
"""

# Qt Test Fixtures
# --------------------------------

@pytest.fixture
def outline_explorer_bot(qtbot):
    code_editor = CodeEditor(None)
    code_editor.set_language('py', 'test_outline_explorer.py')
    code_editor.set_text(text)

    editor = OutlineExplorerProxyEditor(code_editor,
                                        'test_outline_explorer.py')

    outline_explorer = OutlineExplorerWidget()
    outline_explorer.set_current_editor(editor, False, False)

    qtbot.addWidget(outline_explorer)

    return outline_explorer, qtbot


# Test OutlineExplorerWidget
# -------------------------------

def test_outline_explorer(outline_explorer_bot):
    """
    Test to assert the outline explorer is initializing correctly and
    is showing the expected number of items, the expected type of items, and
    the expected text for each item.
    """
    outline_explorer, qtbot = outline_explorer_bot
    outline_explorer.show()
    outline_explorer.setFixedSize(400, 350)
    assert outline_explorer

    outline_explorer.treewidget.expandAll()
    tree_widget = outline_explorer.treewidget
    all_items = tree_widget.get_top_level_items() + tree_widget.get_items()

    # Assert that the expected number, text and type of items is displayed in
    # the tree.
    expected_results = [('test_outline_explorer.py', FileRootItem),
                        ('functions', CellItem),
                        ('---- func 1 and 2', CommentItem),
                        ('func1', FunctionItem, False),
                        ('func2', FunctionItem, False),
                        ('---- func 3', CommentItem),
                        ('func3', FunctionItem, False),
                        ('classes', CellItem),
                        ('class1', ClassItem),
                        ('__ini__', FunctionItem, True),
                        ('method1', FunctionItem, True),
                        ('method2', FunctionItem, True)]

    assert len(all_items) == len(expected_results)
    for item, expected_result in zip(all_items, expected_results):
        assert item.text(0) == expected_result[0]
        assert type(item) == expected_result[1]
        if type(item) == FunctionItem:
            assert item.is_method() == expected_result[2]


# Qt Test Fixtures
# --------------------------------
@pytest.fixture
def outline_explorer_bot2(qtbot):
    editor = CodeEditor()
    editor = CodeEditor(None)
    editor.set_language('py', 'test_file.py')
    editor.set_text(dedent(code))

    outline_explorer = OutlineExplorerWidget()
    outline_explorer.set_current_editor(
            editor, 'test_file.py', False, False)

    qtbot.addWidget(outline_explorer)

    return outline_explorer, qtbot


# Test OutlineExplorerWidget
# -------------------------------
def test_code_cell_grouping(outline_explorer_bot2):
    """
    Test to assert the outline explorer is initializing correctly and
    is showing the expected number of items, the expected type of items, and
    the expected text for each item. In addition this tests ancestry, code
    cells comments, code cell grouping and disabling this feature.
    """
    outline_explorer, qtbot = outline_explorer_bot2
    outline_explorer.show()
    outline_explorer.setFixedSize(400, 350)
    assert outline_explorer

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
        ('MGroup4', CellItem, 'MGroup3', 'test_file.py')
        ]

    outline_explorer.treewidget.expandAll()
    tree_widget = outline_explorer.treewidget
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
