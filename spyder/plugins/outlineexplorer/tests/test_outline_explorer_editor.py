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

text = ('# test file\n'
        'class a():\n'
        '    self.b = 1\n'
        '    print(self.b)\n'
        '    \n'
        '    def some_method(self):\n'
        '        self.b = 3')

expected_oe_data = {
    1: OutlineExplorerData('class a():', 0, OutlineExplorerData.CLASS, 'a'),
    5: OutlineExplorerData('    def some_method(self):', 4,
                           OutlineExplorerData.FUNCTION, 'some_method')
}


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
    oedata = oe_proxy.get_outlineexplorer_data()

    for index, oeitem in expected_oe_data.items():
        a = oeitem.__dict__
        b = oedata.get(index).__dict__
        b['color'] = None
        assert a == b

    # Assert Treewidget Items
    items = outline_explorer.treewidget.get_items()
    oedata_texts = [l
                    for k, l in sorted([[i, j.def_name] for i, j in
                                        expected_oe_data.items()])]
    for item, oe_item in zip(items, oedata_texts):
        assert item.text(0) == oe_item


if __name__ == "__main__":
    pytest.main()
