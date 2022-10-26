# -*- coding: utf-8 -*-
#
# Copyright (c) 2009- Spyder Project Contributors
#
# Distributed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""
Pythonpath manager plugin.
"""

from spyder.api.plugins import Plugins, SpyderPluginV2
from spyder.api.plugin_registration.decorators import (
    on_plugin_available, on_plugin_teardown)
from spyder.api.translations import get_translation
from spyder.plugins.application.api import ApplicationActions
from spyder.plugins.mainmenu.api import ApplicationMenus, ToolsMenuSections
from spyder.plugins.toolbar.api import ApplicationToolbars, MainToolbarSections
from spyder.plugins.pythonpath.container import (
    PythonpathActions, PythonpathContainer)

# Localization
_ = get_translation('spyder')


class PythonpathManager(SpyderPluginV2):
    """
    Pythonpath manager plugin.
    """

    NAME = "pythonpath_manager"
    REQUIRES = [Plugins.Toolbar, Plugins.MainMenu]
    CONTAINER_CLASS = PythonpathContainer
    CONF_SECTION = NAME
    CONF_FILE = False

    # ---- SpyderPluginV2 API
    @staticmethod
    def get_name():
        return _("PYTHONPATH manager")

    def get_description(self):
        return _("Manager of additional locations to search for Python "
                 "modules.")

    def get_icon(self):
        return self.create_icon('python')

    def on_initialize(self):
        pass

    @on_plugin_available(plugin=Plugins.MainMenu)
    def on_main_menu_available(self):
        container = self.get_container()
        main_menu = self.get_plugin(Plugins.MainMenu)

        main_menu.add_item_to_application_menu(
            container.path_manager_action,
            menu_id=ApplicationMenus.Tools,
            section=ToolsMenuSections.Tools,
            before=ApplicationActions.SpyderUserEnvVariables,
            before_section=ToolsMenuSections.External
        )

    @on_plugin_available(plugin=Plugins.Toolbar)
    def on_toolbar_available(self):
        container = self.get_container()
        toolbar = self.get_plugin(Plugins.Toolbar)
        toolbar.add_item_to_application_toolbar(
            container.path_manager_action,
            toolbar_id=ApplicationToolbars.Main,
            section=MainToolbarSections.ApplicationSection
        )

    @on_plugin_teardown(plugin=Plugins.MainMenu)
    def on_main_menu_teardown(self):
        main_menu = self.get_plugin(Plugins.MainMenu)
        main_menu.remove_item_from_application_menu(
            PythonpathActions.Manager,
            menu_id=ApplicationMenus.Tools,
        )

    @on_plugin_teardown(plugin=Plugins.Toolbar)
    def on_toolbar_teardown(self):
        toolbar = self.get_plugin(Plugins.Toolbar)
        toolbar.remove_item_from_application_toolbar(
            PythonpathActions.Manager,
            toolbar_id=ApplicationToolbars.Main
        )
