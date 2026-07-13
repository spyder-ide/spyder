# -*- coding: utf-8 -*-
#
# Copyright © 2009- The Spyder Development Team
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""
Tests for the shortcuts summary widget.
"""

import sys

import pytest
from qtpy.QtCore import Qt

from spyder.plugins.shortcuts.widgets.summary import ShortcutsSummaryDialog


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
    main_layout = dlg_shortcuts.scroll_widget.layout()

    for group_idx in range(main_layout.count()):
        try:
            group_layout = main_layout.itemAt(group_idx).widget().layout()
        except AttributeError:  # Since some groups are not present
            continue

        for shortcut_idx in range(group_layout.rowCount()):
            try:
                shortcut_keystr = (
                    group_layout.itemAtPosition(shortcut_idx, 1)
                    .widget()
                    .text()
                )
            except AttributeError:  # Since some items are not present
                continue

            if not shortcut_keystr:
                continue

            if sys.platform == "darwin":
                keywords = [u'⇧', u'⌃', u'⌘', u'⌥', u'⌦',  u'⎋', 'F']
            else:
                keywords = ["Alt", "Ctrl", "Del", "Esc", "F", "Meta", "Shift"]

            assert any([key in shortcut_keystr for key in keywords])
