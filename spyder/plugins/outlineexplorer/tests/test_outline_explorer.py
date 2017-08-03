# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
#
"""Tests for outline explorer widget."""

# Test library imports
import pytest

# Local imports
from spyder.plugins.outlineexplorer.widgets import OutlineExplorerWidget
from spyder.plugins.outlineexplorer.api import (OutlineExplorerProxy,
                                                OutlineExplorerData)


class OutlineExplorerProxyTest(OutlineExplorerProxy):
    def __init__(self, fname):
        self.fname = fname

    def get_id(self):
        return id(self)

    def give_focus(self):
        pass

    def get_outlineexplorer_data(self):

        oe_data = [
            [16, 'class Test:', 0, 0, 'Test'],
            [17, '    def __init__(self,fname):', 4, 1, '__init__'],
            [20, '    def get_id(self):', 4, 1, 'get_id'],
            [23, '    def give_focus(self):', 4, 1, 'give_focus'],
            [26, '    def get_data(self):', 4, 1, 'get_data'],
            [31, 'for i in range(10):', 8, 2, 'for i in range(10):'],
            [37, '    def get_line_count(self):', 4, 1, 'get_line_count'],
            [45, '    def parent(self):', 4, 1, 'parent'],
            [50, 'def setup(qtbot):', 0, 1, 'setup'],
            [57, 'def test(qtbot):', 0, 1, 'test'],
            [63, 'if __name__ == "__main__":', 0, 2,
             'if __name__ == "__main__":']
        ]
        oe_dict = {}

        for line_number, text, fold_level, def_type, def_name in oe_data:
            oe_dict[line_number] = OutlineExplorerData(text, fold_level,
                                                       def_type, def_name)
        return oe_dict

    def get_line_count(self):
        return 50

    def parent(self):
        return None


@pytest.fixture
def setup_outline_explorer(qtbot):
    """Set up outline_explorer."""
    oew = OutlineExplorerWidget(None)
    qtbot.addWidget(oew)

    oe_proxy = OutlineExplorerProxyTest('test.py')
    oew.set_current_editor(oe_proxy, update=True, clear=True)

    return oew


def test_outline_explorer(setup_outline_explorer):
    """Run outline_explorer."""
    outline_explorer = setup_outline_explorer
    assert outline_explorer


if __name__ == "__main__":
    pytest.main()
