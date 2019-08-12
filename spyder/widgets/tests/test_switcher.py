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
from qtpy.QtWidgets import QLineEdit


from spyder.config.base import _
from spyder.widgets.switcher import (Switcher, create_options_example_switcher,
                                     create_help_example_switcher,
                                     create_line_example_switcher,
                                     create_symbol_example_switcher,
                                     create_vcs_example_switcher)


@pytest.fixture
def dlg_switcher(qtbot):
    """Set up switcher widget."""
    dlg_switcher = Switcher(None)
    main = QLineEdit()
    dlg_switcher = Switcher(main)
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

    create_vcs_example_switcher(dlg_switcher)
    qtbot.addWidget(dlg_switcher)
    dlg_switcher.show()
    yield dlg_switcher
    dlg_switcher.close()


def test_switcher(dlg_switcher, qtbot):
    """Test that switcher is visible and is not empty"""
    # Test that the dialog exists and is shown
    assert dlg_switcher.isVisible()

    # Test that the dialog is not empty
    assert not dlg_switcher._layout.isEmpty()

    # Test that the dialog is closed properly on Esc keypress
    qtbot.keyClick(dlg_switcher, Qt.Key_Escape)
    assert not dlg_switcher.isVisible()


def test_switcher_filter_and_mode(dlg_switcher, qtbot):
    """Test filter and mode change."""
    switcher_list = dlg_switcher.list

    # Initially cvs mode with three rows
    assert switcher_list.model().rowCount() == 5

    # Match one row by name
    dlg_switcher.edit.setText("master")
    assert switcher_list.model().rowCount() == 2

    # Symbol mode
    dlg_switcher.edit.setText("@")
    assert switcher_list.model().rowCount() == 2

    # Commands mode
    switcher_list.edit.setText(">")
    assert switcher_list.model().rowCount() == 7

    # Help mode
    switcher_list.edit.setText("?")
    assert switcher_list.model().rowCount() == 5

    # Text mode
    switcher_list.edit.setText(":")
    assert switcher_list.model().rowCount() == 1
