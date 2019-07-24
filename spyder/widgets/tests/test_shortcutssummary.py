# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
#

"""
Tests for the Shortcut Summary Widget.
"""
import sys
from random import sample

import pytest
from qtpy.QtCore import Qt

from spyder.widgets.shortcutssummary import ShortcutsSummaryDialog


@pytest.fixture
def dlg_shortcuts(qtbot):
    """Set up shortcut summary widget."""
    dlg_shortcuts = ShortcutsSummaryDialog(None)
    qtbot.addWidget(dlg_shortcuts)
    dlg_shortcuts.show()
    yield dlg_shortcuts
    dlg_shortcuts.close()


def test_shortcutssummary(dlg_shortcuts, qtbot):
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
    children = dlg_shortcuts.scroll_widget.layout().children()
    for column_layout in sample(children, 3):
        for group_idx in range(column_layout.count()):
            try:
                group_layout = (column_layout.itemAt(group_idx)
                                .widget().layout())
            except AttributeError:  # Since some groups are not present
                continue
            for shortcut_idx in range(group_layout.rowCount()):
                try:
                    shortcut_keystr = (
                        group_layout.itemAtPosition(shortcut_idx, 1)
                        .widget().text())
                except AttributeError:  # Since some items are not present
                    continue

                if sys.platform.startswith('darwin'):
                    keywords = [u'⇧', u'⌃', u'⌘', u'⌥', u'⌦',  u'⎋', 'F']
                else:
                    keywords = ['Alt', 'Ctrl', 'Del', 'Esc', 'F', 'Meta',
                                'Shift']
                assert any([key in shortcut_keystr for key in keywords])
