# -*- coding: utf-8 -*-
#
# Copyright (c) 2009- Spyder Project Contributors
#
# Distributed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""
Switcher Plugin.
"""

# Third-party imports
from qtpy.QtCore import Qt

# Local imports
from spyder.api.translations import _
from spyder.api.plugins import Plugins, SpyderPluginV2
from spyder.api.plugin_registration.decorators import on_plugin_available, on_plugin_teardown
from spyder.plugins.switcher.confpage import SwitcherConfigPage
from spyder.plugins.switcher.container import SwitcherContainer
from spyder.plugins.mainmenu.api import (ApplicationMenus, FileMenuSections)


# --- Constants
# ----------------------------------------------------------------------------
class SwitcherActions:
    FileSwitcherAction = 'file switcher'
    SymbolFinderAction = 'symbol finder'


# --- Plugin
# ----------------------------------------------------------------------------
class Switcher(SpyderPluginV2):
    """
    Switcher plugin.
    """

    NAME = "switcher"
    REQUIRES = []
    OPTIONAL = [Plugins.MainMenu]
    CONTAINER_CLASS = SwitcherContainer
    CONF_WIDGET_CLASS = SwitcherConfigPage
    CONF_SECTION = NAME
    CONF_FILE = False

    # --- Signals

    # --- SpyderPluginV2 API
    # ------------------------------------------------------------------------
    @staticmethod
    def get_name():
        return _("Switcher")

    def get_description(self):
        return _("A multi purpose switcher.")

    def get_icon(self):
        return self.create_icon('filelist')

    def on_initialize(self):
        container = self.get_container()

         # Switcher shortcuts
        self.create_action(
            SwitcherActions.FileSwitcherAction,
            _('File switcher...'),
            icon= self.get_icon(),
            tip=_('Fast switch between files'),
            triggered=container.open_switcher,
            register_shortcut=True,
            context=Qt.ApplicationShortcut
        )
        
        self.create_action(
            SwitcherActions.SymbolFinderAction,
            _('Symbol finder...'),
            icon=self.create_icon('symbol_find'),
            tip=_('Fast symbol search in file'),
            triggered=container.open_symbolfinder,
            register_shortcut=True,
            context=Qt.ApplicationShortcut
        )
    
    @on_plugin_available(plugin=Plugins.MainMenu)
    def on_main_menu_available(self):
        mainmenu = self.get_plugin(Plugins.MainMenu)
        for switcher_action in [SwitcherActions.FileSwitcherAction, SwitcherActions.SymbolFinderAction]:
            action = self.get_action(switcher_action)
            mainmenu.add_item_to_application_menu(
                action,
                menu_id=ApplicationMenus.File,
                section=FileMenuSections.Switcher,
                before_section=FileMenuSections.Restart
            )

    @on_plugin_teardown(plugin=Plugins.MainMenu)
    def on_main_menu_teardown(self):
        mainmenu = self.get_plugin(Plugins.MainMenu)
        for switcher_action in [SwitcherActions.FileSwitcherAction, SwitcherActions.SymbolFinderAction]:
            action = self.get_action(switcher_action)
            mainmenu.remove_item_from_application_menu(
            action,
            menu_id=ApplicationMenus.File)


    # --- Public API
    # ------------------------------------------------------------------------
