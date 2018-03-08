# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
#

"""
Tests for editortool.py
"""

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


if __name__ == "__main__":
    import os
    pytest.main(['-x', os.path.basename(__file__), '-v', '-rw'])
