# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright (c) Spyder Project Contributors
#
# Licensed under the terms of the MIT License
# (see LICENSE.txt for details)
# -----------------------------------------------------------------------------

# Third-party imports
import pytest

# Local imports
from spyder.config.manager import CONF
from spyder.plugins.appearance.plugin import Appearance
from spyder.plugins.preferences.api import SpyderConfigPage
from spyder.plugins.preferences.tests.conftest import (
    config_dialog, MainWindowMock)


@pytest.mark.parametrize(
    'config_dialog',
    [[MainWindowMock, [], [Appearance]]],
    indirect=True)
def test_change_ui_theme_and_color_scheme(config_dialog, mocker, qtbot):
    """Test that changing color scheme or UI theme works as expected."""
    # Patch methods whose calls we want to check
    mocker.patch.object(SpyderConfigPage, "prompt_restart_required")
    mocker.patch.object(CONF, "disable_notifications")

    # Get reference to Preferences dialog and widget page to interact with
    dlg = config_dialog
    widget = config_dialog.get_page()

    # List of color schemes
    names = widget.get_option('names')

    # Assert no restarts have been requested so far.
    assert SpyderConfigPage.prompt_restart_required.call_count == 0

    # Assert default UI theme is 'automatic' and interface is dark. The other
    # tests below depend on this.
    assert widget.get_option('ui_theme') == 'automatic'
    assert widget.is_dark_interface()

    # Change to another dark color scheme
    widget.schemes_combobox.setCurrentIndex(names.index('monokai'))
    dlg.apply_btn.click()
    assert SpyderConfigPage.prompt_restart_required.call_count == 0
    assert CONF.disable_notifications.call_count == 0

    # Change to a light color scheme
    widget.schemes_combobox.setCurrentIndex(names.index('pydev'))
    dlg.apply_btn.clicked.emit()
    assert SpyderConfigPage.prompt_restart_required.call_count == 1
    assert CONF.disable_notifications.call_count == 2

    # Change to the 'dark' ui theme
    widget.ui_combobox.setCurrentIndex(2)
    dlg.apply_btn.clicked.emit()
    assert SpyderConfigPage.prompt_restart_required.call_count == 1
    assert CONF.disable_notifications.call_count == 2

    # Change to the 'automatic' ui theme
    widget.ui_combobox.setCurrentIndex(0)
    dlg.apply_btn.clicked.emit()
    assert SpyderConfigPage.prompt_restart_required.call_count == 2
    assert CONF.disable_notifications.call_count == 4

    # Change to the 'light' ui theme
    widget.ui_combobox.setCurrentIndex(1)
    dlg.apply_btn.clicked.emit()
    assert SpyderConfigPage.prompt_restart_required.call_count == 3
    assert CONF.disable_notifications.call_count == 6

    # Change to another dark color scheme
    widget.schemes_combobox.setCurrentIndex(names.index('solarized/dark'))
    dlg.apply_btn.clicked.emit()
    assert SpyderConfigPage.prompt_restart_required.call_count == 4
    assert CONF.disable_notifications.call_count == 8

    # Change to the 'automatic' ui theme again
    widget.ui_combobox.setCurrentIndex(0)
    dlg.apply_btn.clicked.emit()
    assert SpyderConfigPage.prompt_restart_required.call_count == 4
    assert CONF.disable_notifications.call_count == 8
