# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
#

"""Tests for collectionsdelegate.py."""

# Local imports
from spyder.plugins.variableexplorer.widgets.collectionsdelegate import (
    CollectionsDelegate,
)


class MockEditor:
    def __init__(self):
        self.rejected = False

    def reject(self):
        self.rejected = True


def test_close_all_editors():
    """Test all tracked non-modal editors are closed."""
    delegate = CollectionsDelegate()

    editor_1 = MockEditor()
    editor_2 = MockEditor()
    delegate._editors = {
        id(editor_1): {"editor": editor_1},
        id(editor_2): {"editor": editor_2},
    }

    delegate.close_all_editors()

    assert editor_1.rejected
    assert editor_2.rejected
    assert not delegate._editors
