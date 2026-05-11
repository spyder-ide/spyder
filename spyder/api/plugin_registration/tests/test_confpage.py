# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright (c) Spyder Project Contributors
#
# Licensed under the terms of the MIT License
# (see LICENSE.txt for details)
# -----------------------------------------------------------------------------

# Standard library imports
import sys

# Third-party imports
import pytest
from qtpy.QtGui import QIcon
from qtpy.QtWidgets import QMessageBox

# Local imports
from spyder.api.plugins import Plugins, SpyderPluginV2
from spyder.api.plugin_registration.registry import (
    _PluginRegistryPreferencesAdapter,
    PLUGIN_REGISTRY,
)
from spyder.config.base import running_in_ci
from spyder.plugins.preferences.tests.conftest import MainWindowMock


class Plugin1(SpyderPluginV2):

    NAME = "plugin_1"
    CONF_SECTION = NAME

    @staticmethod
    def get_name():
        return "Plugin 1"

    @staticmethod
    def get_description():
        return "This is Plugin 1"

    @staticmethod
    def get_icon():
        return QIcon()

    def on_initialize(self):
        pass


class Plugin2(SpyderPluginV2):

    NAME = "plugin_2"
    CONF_SECTION = NAME

    REQUIRES = [Plugin1.NAME]

    @staticmethod
    def get_name():
        return "Plugin 2"

    @staticmethod
    def get_description():
        return "This is Plugin 2"

    @staticmethod
    def get_icon():
        return QIcon()

    def on_initialize(self):
        pass


class Plugin3(SpyderPluginV2):

    NAME = "plugin_3"
    CONF_SECTION = NAME

    REQUIRES = [Plugin2.NAME]

    @staticmethod
    def get_name():
        return "Plugin 3"

    @staticmethod
    def get_description():
        return "This is Plugin 3"

    @staticmethod
    def get_icon():
        return QIcon()

    def on_initialize(self):
        pass

@pytest.mark.skipif(
    sys.platform.startswith("linux") and running_in_ci(),
    reason="Sometimes fails on Linux and CIs"
)
def test_plugins_confpage(mocker, qtbot):
    mocker.patch(
        "spyder.api.plugin_registration.registry.find_internal_plugins",
        return_value={
            Plugin1.NAME: Plugin1,
            Plugin2.NAME: Plugin2,
            Plugin3.NAME: Plugin3,
        }
    )
    mocker.patch(
        "spyder.api.plugin_registration.registry.find_external_plugins",
        return_value={}
    )

    # Create main window
    main = MainWindowMock(None)

    # Register dummy plugins
    PLUGIN_REGISTRY.main = main
    PLUGIN_REGISTRY._load_and_register_plugins()

    # Check dependencies and dependents
    for name, result in [
        (Plugin1.NAME, set()),
        (Plugin2.NAME, {Plugin1.NAME}),
        (Plugin3.NAME, {Plugin1.NAME, Plugin2.NAME})
    ]:
        assert (
            PLUGIN_REGISTRY.get_plugin_required_dependencies(name) == result
        )

    for name, result in [
        (Plugin1.NAME, {Plugin2.NAME, Plugin3.NAME}),
        (Plugin2.NAME, {Plugin3.NAME}),
        (Plugin3.NAME, set()),
    ]:
        assert (
            PLUGIN_REGISTRY.get_plugin_required_dependents(name) == result
        )

    # Create Preferences dialog
    preferences = main.get_plugin(Plugins.Preferences)
    preferences.config_pages = {
        _PluginRegistryPreferencesAdapter.NAME: (
            "new",
            _PluginRegistryPreferencesAdapter.CONF_WIDGET_CLASS,
            PLUGIN_REGISTRY,
        )
    }

    preferences.open_dialog()

    # Get reference to plugins conf page
    dlg = preferences.get_container().dialog
    dlg.set_current_index(1)
    page = dlg.get_page()

    # Say Yes to warning and keep count of its calls
    mocker.patch.object(QMessageBox, "warning", return_value=QMessageBox.Yes)
    warning_calls = 0
    expected_warning_calls = 0

    # Disable Plugin1. Plugin2 and 3 should be disabled too
    page.plugins_checkboxes[Plugin1.NAME][0].click()
    expected_warning_calls += 1

    for plugin in [Plugin2, Plugin3]:
        assert not page.plugins_checkboxes[plugin.NAME][0].isChecked()

    # Enable Plugin3. Plugin1 and 2 should be enabled too
    page.plugins_checkboxes[Plugin3.NAME][0].click()
    expected_warning_calls += 1

    for plugin in [Plugin1, Plugin2]:
       assert page.plugins_checkboxes[plugin.NAME][0].isChecked()

    # Disable Plugin1 again to check what happens when we say No to warning
    page.plugins_checkboxes[Plugin1.NAME][0].click()
    expected_warning_calls += 1

    for plugin in [Plugin1, Plugin2, Plugin3]:
        assert not page.plugins_checkboxes[plugin.NAME][0].isChecked()

    warning_calls += len(QMessageBox.warning.mock_calls)

    mocker.patch.object(QMessageBox, "warning", return_value=QMessageBox.No)
    page.plugins_checkboxes[Plugin3.NAME][0].click()
    expected_warning_calls += 1
    warning_calls += len(QMessageBox.warning.mock_calls)

    for plugin in [Plugin1, Plugin2, Plugin3]:
        assert not page.plugins_checkboxes[plugin.NAME][0].isChecked()

    # Say Yes to warning again
    mocker.patch.object(QMessageBox, "warning", return_value=QMessageBox.Yes)

    # Enable Plugin1 and check 2 and 3 are still disabled because they are not
    # dependents of 1. No dialog should be shown either.
    page.plugins_checkboxes[Plugin1.NAME][0].click()

    assert page.plugins_checkboxes[Plugin1.NAME][0].isChecked()
    for plugin in [Plugin2, Plugin3]:
        assert not page.plugins_checkboxes[plugin.NAME][0].isChecked()

    # Disable Plugin1 and enable 2. Plugin1 should be enabled but not 3
    page.plugins_checkboxes[Plugin1.NAME][0].click()
    page.plugins_checkboxes[Plugin2.NAME][0].click()
    expected_warning_calls += 1

    assert page.plugins_checkboxes[Plugin1.NAME][0].isChecked()
    assert not page.plugins_checkboxes[Plugin3.NAME][0].isChecked()

    # Enable Plugin 3. This shouldn't show the warning dialog because its two
    # dependents are already enabled
    page.plugins_checkboxes[Plugin3.NAME][0].click()

    # Check expected and detected number of warnings
    warning_calls += len(QMessageBox.warning.mock_calls)
    assert expected_warning_calls == warning_calls

    # Reset main window to not affect other tests
    PLUGIN_REGISTRY.main = None
