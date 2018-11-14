# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
#

"""
Tests for the Shortcut Summary Widget.
"""
import sys

import pytest
from qtpy.QtCore import Qt

from spyder.widgets.shortcutssummary import ShortcutsSummaryDialog
from .helpers import SHORTCUTS


@pytest.fixture
def dlg_shortcuts(qtbot):
    """Set up shortcut summary widget."""
    dlg_shortcuts = ShortcutsSummaryDialog(None)
    qtbot.addWidget(dlg_shortcuts)
    dlg_shortcuts.show()
    yield dlg_shortcuts
    dlg_shortcuts.close()


def test_shortcutssummary_exists(dlg_shortcuts, qtbot):
    """Test that shortcut summary is visible and is not empty"""
    # Test that the dialog exists and is shown
    assert dlg_shortcuts.isVisible()

    # Test that the dialog is not empty
    assert not dlg_shortcuts._layout.isEmpty()

    # Test that the dialog is closed properly on Esc keypress
    qtbot.keyClick(dlg_shortcuts, Qt.Key_Escape)
    assert not dlg_shortcuts.isVisible()


def test_shortcutssummary_texts(dlg_shortcuts, qtbot):
    """Test that each shortcut has platform-specific key names."""
    expected_shortcuts = 124
    found_shortcuts = 0
    for column_layout in dlg_shortcuts.scroll_widget.layout().children():
        for group_idx in range(column_layout.count()):
            try:
                group_layout = (column_layout.itemAt(group_idx)
                                .widget().layout())
            except AttributeError:  # Since some groups are not present
                continue
            for shortcut_idx in range(group_layout.rowCount()):
                try:
                    shortcut_name = (
                        group_layout.itemAtPosition(shortcut_idx, 0)
                        .widget().text())
                    shortcut_keystr = (
                        group_layout.itemAtPosition(shortcut_idx, 1)
                        .widget().text())
                except AttributeError:  # Since some items are not present
                    continue

                print(found_shortcuts, shortcut_name, shortcut_keystr)
                expected = SHORTCUTS[shortcut_name]
                if sys.platform.startswith('darwin'):
                    assert shortcut_keystr == expected[1]
                else:
                    assert shortcut_keystr == expected[0]
                found_shortcuts += 1

    assert found_shortcuts == expected_shortcuts
