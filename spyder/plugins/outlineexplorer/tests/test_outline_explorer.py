# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
#
"""Tests for outline explorer widget."""

# Test library imports
import pytest

# Third party imports
from qtpy.QtCore import Qt

# Local imports
from spyder.plugins.outlineexplorer.widgets import OutlineExplorerWidget
from spyder.plugins.outlineexplorer.api import (OutlineExplorerProxy,
                                                OutlineExplorerData)

oe_data = [
    [16, 'class Test:', 0, 0, 'Test'],
    [17, '    def __init__(self,fname):', 4, 1, '__init__'],
    [20, '    def get_id(self):', 4, 1, 'get_id'],
    [23, '    def give_focus(self):', 4, 1, 'give_focus'],
    [26, '    def get_data(self):', 4, 1, 'get_data'],
    [31, 'for i in range(10):', 8, 2, 'get_line_count'],
    [37, '    def get_line_count(self):', 4, 1, 'get_line_count'],
    [45, '    def parent(self):', 4, 1, 'get_line_count'],
    [50, 'def setup(qtbot):', 0, 1, 'setup'],
    [57, 'def test(qtbot):', 0, 1, 'test'],
    [63, 'if __name__ == "__main__":', 0, 2, 'if __name__ == "__main__":']
]

oe_data_filtered = oe_data[:5] + oe_data[6:10]


class testBlock():
    def __init__(self, line_number):
        self._line = line_number - 1

    def firstLineNumber(self):
        return self._line


class OutlineExplorerProxyTest(OutlineExplorerProxy):
    def __init__(self, fname, oe_data):
        super(OutlineExplorerProxyTest, self).__init__()
        self.fname = fname
        self.oe_data = oe_data

    def is_python(self):
        return True

    def get_id(self):
        return id(self)

    def give_focus(self):
        pass

    def get_line_count(self):
        return max([oe[0] for oe in self.oe_data]) + 1

    def parent(self):
        return None

    def get_cursor_line_number(self):
        return 1

    def outlineexplorer_data_list(self):
        oe_list = []
        for block_number, text, fold_level, def_type, def_name in self.oe_data:
            oe_list.append(OutlineExplorerData(
                testBlock(block_number),
                text, fold_level, def_type, def_name))
        return oe_list


def click_item(treewidget, item, qtbot):
    """Click an item in a treewidget."""
    index = treewidget.indexFromItem(item)
    # Make sure item is visible
    treewidget.scrollTo(index)
    item_rect = treewidget.visualRect(index)
    qtbot.mouseClick(treewidget.viewport(), Qt.LeftButton, Qt.NoModifier,
                     item_rect.center())


@pytest.fixture
def setup_outline_explorer(qtbot):
    """Set up outline_explorer."""
    oew = OutlineExplorerWidget(None)
    qtbot.addWidget(oew)

    oe_proxy = OutlineExplorerProxyTest('test.py', oe_data)
    oew.set_current_editor(oe_proxy, update=True, clear=False)

    return oew, oe_proxy


def test_outline_explorer(setup_outline_explorer):
    """Test outline_explorer widget."""
    outline_explorer, oe_proxy = setup_outline_explorer
    assert outline_explorer

    # Assert proxy
    assert oe_proxy == outline_explorer.treewidget.current_editor
    assert len(outline_explorer.treewidget.editor_items) == 1

    # Assert root item
    file_root = outline_explorer.treewidget.editor_items[id(oe_proxy)]
    assert file_root.text(0) == oe_proxy.fname

    # Assert Items
    items = outline_explorer.treewidget.get_items()
    oedata_texts = [oe[4] for oe in oe_data_filtered]
    for item, oe_item in zip(items, oedata_texts):
        assert item.text(0) == oe_item


@pytest.mark.skipif(True, reason="It's failing")
def test_go_to(setup_outline_explorer, qtbot):
    """Test clicking in an item."""
    outline_explorer, oe_proxy = setup_outline_explorer

    item = outline_explorer.treewidget.get_items()[1]

    with qtbot.waitSignal(outline_explorer.edit_goto) as sig_edit_goto:
        click_item(outline_explorer.treewidget, item, qtbot)

    # It sends line_number (block_number+1)
    assert sig_edit_goto.args == ['test.py', 18, '__init__']


if __name__ == "__main__":
    pytest.main()
