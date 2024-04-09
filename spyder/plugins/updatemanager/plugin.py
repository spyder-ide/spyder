# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""
Update Manager Plugin.
"""

# Local imports
from spyder.api.plugins import Plugins, SpyderPluginV2
from spyder.api.translations import _
from spyder.api.plugin_registration.decorators import (
    on_plugin_available,
    on_plugin_teardown
)
from spyder.plugins.updatemanager.container import (
    UpdateManagerActions,
    UpdateManagerContainer
)
from spyder.plugins.mainmenu.api import ApplicationMenus, HelpMenuSections


class UpdateManager(SpyderPluginV2):
    NAME = 'update_manager'
    REQUIRES = [Plugins.Preferences]
    OPTIONAL = [Plugins.MainMenu, Plugins.StatusBar]
    CONTAINER_CLASS = UpdateManagerContainer
    CONF_SECTION = 'update_manager'
    CONF_FILE = False
    CAN_BE_DISABLED = False

    # ---- SpyderPluginV2 API
    # -------------------------------------------------------------------------
    @staticmethod
    def get_name():
        return _('Update Manager')

    @classmethod
    def get_icon(cls):
        return cls.create_icon('genprefs')

    @staticmethod
    def get_description():
        return _('Manage application updates.')

    # ---- Plugin initialization
    def on_initialize(self):
        pass

    @on_plugin_available(plugin=Plugins.Preferences)
    def on_preferences_available(self):
        # Register conf page
        preferences = self.get_plugin(Plugins.Preferences)
        preferences.register_plugin_preferences(self)

    @on_plugin_available(plugin=Plugins.MainMenu)
    def on_main_menu_available(self):
        if self.is_plugin_enabled(Plugins.Shortcuts):
            if self.is_plugin_available(Plugins.Shortcuts):
                self._populate_help_menu()
        else:
            self._populate_help_menu()

    @on_plugin_available(plugin=Plugins.StatusBar)
    def on_statusbar_available(self):
        # Add status widget
        statusbar = self.get_plugin(Plugins.StatusBar)
        statusbar.add_status_widget(self.update_manager_status)

    # ---- Plugin teardown
    @on_plugin_teardown(plugin=Plugins.StatusBar)
    def on_statusbar_teardown(self):
        # Remove status widget if created
        statusbar = self.get_plugin(Plugins.StatusBar)
        statusbar.remove_status_widget(self.update_manager_status.ID)

    @on_plugin_teardown(plugin=Plugins.Preferences)
    def on_preferences_teardown(self):
        preferences = self.get_plugin(Plugins.Preferences)
        preferences.deregister_plugin_preferences(self)

    @on_plugin_teardown(plugin=Plugins.MainMenu)
    def on_main_menu_teardown(self):
        self._depopulate_help_menu()

    def on_close(self, _unused=True):
        # The container is closed directly in the plugin registry
        pass

    def on_mainwindow_visible(self):
        """Actions after the mainwindow in visible."""
        container = self.get_container()

        # Initialize status.
        # Note that NO_STATUS also hides the statusbar widget.
        container.update_manager_status.set_no_status()

        # Check for updates on startup
        if self.get_conf('check_updates_on_startup'):
            container.start_check_update(startup=True)

    # ---- Private API
    # ------------------------------------------------------------------------
    def _populate_help_menu(self):
        """Add update action and menu to the Help menu."""
        mainmenu = self.get_plugin(Plugins.MainMenu)
        mainmenu.add_item_to_application_menu(
            self.check_update_action,
            menu_id=ApplicationMenus.Help,
            section=HelpMenuSections.Support,
            before_section=HelpMenuSections.ExternalDocumentation)

    @property
    def _window(self):
        return self.main.window()

    def _depopulate_help_menu(self):
        """Remove update action from the Help main menu."""
        mainmenu = self.get_plugin(Plugins.MainMenu)
        mainmenu.remove_item_from_application_menu(
            UpdateManagerActions.SpyderCheckUpdateAction,
            menu_id=ApplicationMenus.Help)

    # ---- Public API
    # ------------------------------------------------------------------------
    @property
    def check_update_action(self):
        """Check if a new version of Spyder is available."""
        return self.get_container().check_update_action

    @property
    def update_manager_status(self):
        """Get Update manager statusbar widget"""
        return self.get_container().update_manager_status
