# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
#
"""Tests for editor and outline explorer interaction."""

# Test library imports
import pytest


# Local imports
from spyder.plugins.outlineexplorer.widgets import OutlineExplorerWidget
from spyder.plugins.outlineexplorer.editor import OutlineExplorerProxyEditor
from spyder.plugins.outlineexplorer.api import OutlineExplorerData

from spyder.utils.qthelpers import qapplication
from spyder.plugins.editor.widgets.codeeditor import CodeEditor


class testBlock():
    def __init__(self, line_number):
        self._line = line_number - 1

    def firstLineNumber(self):
        return self._line


text = ('# test file\n'
        'class a():\n'
        '    self.b = 1\n'
        '    print(self.b)\n'
        '    \n'
        '    def some_method(self):\n'
        '        self.b = 3')

expected_oe_list = [
    OutlineExplorerData(
        testBlock(2), 'class a():', 0,
        OutlineExplorerData.CLASS, 'a'),
    OutlineExplorerData(
        testBlock(6), '    def some_method(self):', 4,
        OutlineExplorerData.FUNCTION, 'some_method')
]


@pytest.fixture()
def editor_outline_explorer_bot():
    """setup editor and outline_explorer."""
    app = qapplication()
    editor = CodeEditor(parent=None)
    editor.setup_editor(language='Python')
    outlineexplorer = OutlineExplorerWidget(editor)

    editor.set_text(text)

    editor.oe_proxy = OutlineExplorerProxyEditor(editor, "test.py")
    outlineexplorer.set_current_editor(editor.oe_proxy,
                                       update=False,
                                       clear=False)
    outlineexplorer.setEnabled(True)

    return editor, outlineexplorer, editor.oe_proxy


def test_editor_outline_explorer(editor_outline_explorer_bot):
    """Test basic interaction between outline_explorer and editor."""
    editor, outline_explorer, oe_proxy = editor_outline_explorer_bot
    assert outline_explorer

    # Assert proxy
    assert oe_proxy == outline_explorer.treewidget.current_editor
    assert len(outline_explorer.treewidget.editor_items) == 1

    # Assert root item
    file_root = outline_explorer.treewidget.editor_items[id(editor)]
    assert file_root.text(0) == oe_proxy.fname

    # Assert OEData
    oedata = oe_proxy.outlineexplorer_data_list()

    for left, right in zip(oedata, expected_oe_list):
        a = right.__dict__
        b = left.__dict__
        b['color'] = None
        assert a['block'].firstLineNumber() == b['block'].firstLineNumber()
        a['block'] = None
        b['block'] = None
        assert a == b

    # Assert Treewidget Items
    items = outline_explorer.treewidget.get_items()
    oedata_texts = [oe.def_name for oe in expected_oe_list]
    for item, oe_item in zip(items, oedata_texts):
        assert item.text(0) == oe_item


if __name__ == "__main__":
    pytest.main()
