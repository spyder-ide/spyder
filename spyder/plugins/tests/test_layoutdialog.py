# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
#

"""
Tests for layoutdialog.py
"""

# Test library imports
import pytest

# Local imports
from spyder.plugins.layoutdialog import LayoutSettingsDialog, LayoutSaveDialog

@pytest.fixture
def setup_layout_settings_dialog(qtbot, parent, names, order, active):
    """Set up LayoutSettingsDialog."""
    widget = LayoutSettingsDialog(parent, names, order, active)
    qtbot.addWidget(widget)
    return widget

@pytest.fixture
def setup_layout_save_dialog(qtbot, parent, order):
    """Set up LayoutSaveDialog."""
    widget = LayoutSaveDialog(parent, order)
    qtbot.addWidget(widget)
    return widget

def test_layout_settings_dialog(qtbot):
    """Run layout settings dialog."""
    names = ['test', 'tester', '20', '30', '40']
    order = ['test', 'tester', '20', '30', '40']
    active = ['test', 'tester']
    layout_settings_dlg = setup_layout_settings_dialog(qtbot, None, names,
                                                 order, active)
    layout_settings_dlg.show()
    assert layout_settings_dlg

def test_layout_save_dialog(qtbot):
    """Run layout save dialog."""
    order = ['test', 'tester', '20', '30', '40']
    layout_save_dlg = setup_layout_save_dialog(qtbot, None, order)
    layout_save_dlg.show()
    assert layout_save_dlg


if __name__ == "__main__":
    pytest.main()
