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
from spyder.preferences.layoutdialog import LayoutSettingsDialog, LayoutSaveDialog


@pytest.fixture
def layout_settings_dialog(qtbot, request):
    """Set up LayoutSettingsDialog."""
    names, order, active = request.param
    widget = LayoutSettingsDialog(None, names, order, active)
    qtbot.addWidget(widget)
    return widget


@pytest.fixture
def layout_save_dialog(qtbot, request):
    """Set up LayoutSaveDialog."""
    order = request.param
    widget = LayoutSaveDialog(None, order)
    qtbot.addWidget(widget)
    return widget


@pytest.mark.parametrize('layout_settings_dialog',
                         [(['test', 'tester', '20', '30', '40'],
                           ['test', 'tester', '20', '30', '40'],
                           ['test', 'tester'])],
                         indirect=True)
def test_layout_settings_dialog(layout_settings_dialog):
    """Run layout settings dialog."""
    layout_settings_dialog.show()
    assert layout_settings_dialog


@pytest.mark.parametrize('layout_save_dialog',
                         [['test', 'tester', '20', '30', '40']],
                         indirect=True)
def test_layout_save_dialog(layout_save_dialog):
    """Run layout save dialog."""
    layout_save_dialog.show()
    assert layout_save_dialog


if __name__ == "__main__":
    pytest.main()
