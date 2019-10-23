# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
#

"""
Tests for the Switcher Widget.
"""

import pytest
from qtpy.QtCore import Qt

from spyder.config.base import _


@pytest.fixture
def dlg_switcher(qtbot):
    """Set up switcher widget."""
    # Local import need to run tests locally
    from spyder.widgets.switcher import (Switcher,
                                         create_options_example_switcher,
                                         create_help_example_switcher,
                                         create_line_example_switcher,
                                         create_symbol_example_switcher,
                                         create_vcs_example_switcher)

    dlg_switcher = Switcher(None, item_styles=None,
                            item_separator_styles=None)
    dlg_switcher.add_mode('>', _('Commands'))
    dlg_switcher.add_mode('?', _('Help'))
    dlg_switcher.add_mode(':', _('Go to Line'))
    dlg_switcher.add_mode('@', _('Go to Symbol in File'))

    def handle_modes(mode):
        if mode == '>':
            create_options_example_switcher(dlg_switcher)
        elif mode == '?':
            create_help_example_switcher(dlg_switcher)
        elif mode == ':':
            create_line_example_switcher(dlg_switcher)
        elif mode == '@':
            create_symbol_example_switcher(dlg_switcher)
        elif mode == '':
            create_vcs_example_switcher(dlg_switcher)

    def item_selected(item, mode, search_text):
        print([item, mode, search_text])  # spyder: test-skip
        print([item.get_title(), mode, search_text])  # spyder: test-skip

    dlg_switcher.sig_mode_selected.connect(handle_modes)
    dlg_switcher.sig_item_selected.connect(item_selected)

    qtbot.addWidget(dlg_switcher)
    create_vcs_example_switcher(dlg_switcher)
    return dlg_switcher


def test_switcher(dlg_switcher, qtbot):
    """Test that shortcut summary is visible and is not empty"""
    # Test that the dialog exists and is shown
    dlg_switcher.show()
    assert dlg_switcher.isVisible()

    # Test that the dialog is closed properly on Esc keypress
    qtbot.keyClick(dlg_switcher.edit, Qt.Key_Escape)
    assert not dlg_switcher.isVisible()


def test_switcher_filter_and_mode(dlg_switcher, qtbot):
    """Test filter and mode change."""
    edit = dlg_switcher.edit

    # Initially cvs mode with five rows
    assert dlg_switcher._visible_rows == 5

    # Match one row by name
    edit.setText("master")
    qtbot.wait(1000)
    assert dlg_switcher._visible_rows == 2

    # Help mode
    edit.setText("")
    edit.setText("?")
    qtbot.wait(1000)
    assert dlg_switcher._visible_rows == 5

    # Symbol mode
    edit.setText("")
    edit.setText("@")
    qtbot.wait(1000)
    assert dlg_switcher._visible_rows == 2

    # Commands mode
    edit.setText("")
    edit.setText(">")
    qtbot.wait(1000)
    assert dlg_switcher._visible_rows == 7

    # Text mode
    edit.setText("")
    edit.setText(":")
    qtbot.wait(1000)
    assert dlg_switcher._visible_rows == 1
