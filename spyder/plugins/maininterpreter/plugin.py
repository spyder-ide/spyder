# -*- coding: utf-8 -*-
#
# Copyright (c) 2009- Spyder Project Contributors
#
# Distributed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""
Main interpreter Plugin.
"""

# Standard library imports
import os.path as osp

# Third-party imports
from qtpy.QtCore import Slot

# Local imports
from spyder.api.plugins import Plugins, SpyderPluginV2
from spyder.api.plugin_registration.decorators import (
    on_plugin_available, on_plugin_teardown)
from spyder.api.translations import _
from spyder.plugins.maininterpreter.confpage import MainInterpreterConfigPage
from spyder.plugins.maininterpreter.container import MainInterpreterContainer
from spyder.utils.misc import get_python_executable


class MainInterpreter(SpyderPluginV2):
    """
    Main interpreter Plugin.
    """

    NAME = "main_interpreter"
    REQUIRES = [Plugins.Preferences]
    OPTIONAL = [Plugins.StatusBar]
    CONTAINER_CLASS = MainInterpreterContainer
    CONF_WIDGET_CLASS = MainInterpreterConfigPage
    CONF_SECTION = NAME
    CONF_FILE = False
    CAN_BE_DISABLED = False

    # ---- SpyderPluginV2 API
    @staticmethod
    def get_name():
        return _("Python interpreter")

    def get_description(self):
        return _("Main Python interpreter to open consoles.")

    def get_icon(self):
        return self.create_icon('python')

    def on_initialize(self):
        container = self.get_container()

        # Connect signal to open preferences
        container.sig_open_preferences_requested.connect(
            self._open_interpreter_preferences
        )

        # Add custom interpreter to list of saved ones
        container.sig_add_to_custom_interpreters_requested.connect(
            self._add_to_custom_interpreters
        )

        # Validate that the custom interpreter from the previous session
        # still exists
        if self.get_conf('custom'):
            interpreter = self.get_conf('custom_interpreter')
            if not osp.isfile(interpreter):
                self.set_conf('custom', False)
                self.set_conf('default', True)
                self.set_conf('executable', get_python_executable())

    @on_plugin_available(plugin=Plugins.Preferences)
    def on_preferences_available(self):
        # Register conf page
        preferences = self.get_plugin(Plugins.Preferences)
        preferences.register_plugin_preferences(self)

    @on_plugin_available(plugin=Plugins.StatusBar)
    def on_statusbar_available(self):
        # Add status widget
        statusbar = self.get_plugin(Plugins.StatusBar)
        statusbar.add_status_widget(self.interpreter_status)

    @on_plugin_teardown(plugin=Plugins.Preferences)
    def on_preferences_teardown(self):
        # Deregister conf page
        preferences = self.get_plugin(Plugins.Preferences)
        preferences.deregister_plugin_preferences(self)

    @on_plugin_teardown(plugin=Plugins.StatusBar)
    def on_statusbar_teardown(self):
        # Add status widget
        statusbar = self.get_plugin(Plugins.StatusBar)
        statusbar.remove_status_widget(self.interpreter_status.ID)

    @property
    def interpreter_status(self):
        return self.get_container().interpreter_status

    # ---- Private API
    def _open_interpreter_preferences(self):
        """Open the Preferences dialog in the main interpreter section."""
        self._main.show_preferences()
        preferences = self._main.preferences
        container = preferences.get_container()
        dlg = container.dialog
        index = dlg.get_index_by_name("main_interpreter")
        dlg.set_current_index(index)

    @Slot(str)
    def _add_to_custom_interpreters(self, interpreter):
        """Add a new interpreter to the list of saved ones."""
        custom_list = self.get_conf('custom_interpreters_list')
        if interpreter not in custom_list:
            custom_list.append(interpreter)
            self.set_conf('custom_interpreters_list', custom_list)
