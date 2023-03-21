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
from qtpy.QtGui import QIcon

# Local imports
from spyder.api.translations import _
from spyder.api.plugins import Plugins, SpyderPluginV2
from spyder.api.plugin_registration.decorators import on_plugin_available, on_plugin_teardown
from spyder.plugins.switcher.confpage import SwitcherConfigPage
from spyder.plugins.switcher.container import SwitcherContainer
from spyder.plugins.mainmenu.api import (ApplicationMenus, FileMenuSections)
from spyder.utils.qthelpers import (create_action)


# --- Constants
# ----------------------------------------------------------------------------
class SwitcherActions:
    FileSwitcherAction = 'file_switcher_action'
    SymbolFinderAction = 'symbol_finder_action'


class Switcher(SpyderPluginV2):
    """
    Switcher plugin.
    """

    NAME = "switcher"
    REQUIRES = []
    OPTIONAL = [Plugins.MainMenu, Plugins.Shortcuts]
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
        print('Switcher initialized!')

         # Switcher shortcuts
        self.create_action(
            SwitcherActions.FileSwitcherAction,
            _('File switcher...'),
            icon= self.get_icon(),
            tip=_('Fast switch between files'),
            triggered=self.open_switcher,
        )
        
        self.create_action(
            SwitcherActions.SymbolFinderAction,
            _('Symbol finder...'),
            icon=self.create_icon('symbol_find'),
            tip=_('Fast symbol search in file'),
            triggered=self.open_symbolfinder,
        )
    
    @on_plugin_available(plugin=Plugins.MainMenu)
    def on_main_menu_available(self):
        mainmenu = self.get_plugin(Plugins.MainMenu)
        for switcher_action in [SwitcherActions.FileSwitcherAction, SwitcherActions.SymbolFinderAction]:
            switcher_action = self.get_action(switcher_action)
            mainmenu.add_item_to_application_menu(
                switcher_action,
                menu_id=ApplicationMenus.File,
                section=FileMenuSections.Switcher,
                before_section=FileMenuSections.Restart
            )

    @on_plugin_teardown(plugin=Plugins.MainMenu)
    def on_main_menu_teardown(self):
        mainmenu = self.get_plugin(Plugins.MainMenu)
        for switcher_action in [SwitcherActions.FileSwitcherAction, SwitcherActions.SymbolFinderAction]:
            mainmenu.remove_item_from_application_menu(
            switcher_action,
            menu_id=ApplicationMenus.File)

    @on_plugin_available(plugin=Plugins.Shortcuts)
    def on_shortcuts_available(self):
        shortcuts = self.get_plugin(Plugins.Shortcuts)
        shortcuts.register_shortcut(SwitcherActions.FileSwitcherAction, context="_",
                            name="File switcher")
        shortcuts.register_shortcut(SwitcherActions.SymbolFinderAction, context="_",
                            name="symbol finder", add_shortcut_to_tip=True)

    @on_plugin_teardown(plugin=Plugins.Shortcuts)
    def on_shortcuts_teardown(self):
        shortcuts = self.get_plugin(Plugins.Shortcuts)
        shortcuts.unregister_shortcut(SwitcherActions.FileSwitcherAction, context="_",
                            name="File switcher")
        shortcuts.register_shortcut(SwitcherActions.SymbolFinderAction, context="_",
                            name="symbol finder", add_shortcut_to_tip=True)


    def check_compatibility(self):
        valid = True
        message = ""  # Note: Remember to use _("") to localize the string
        return valid, message

    def on_close(self, cancellable=True):
        return True


    def open_switcher(self, symbol=False):
        """Open switcher dialog box."""
        switcher = self.get_container().switcher
        if switcher is not None and switcher.isVisible():
            switcher.clear()
            switcher.hide()
            return
        if symbol:
            switcher.set_search_text('@')
        else:
            switcher.set_search_text('')
            switcher.setup()
        switcher.show()

        # Note: The +6 pixel on the top makes it look better
        # FIXME: Why is this using the toolbars menu? A: To not be on top of
        # the toolbars.
        # Probably toolbars should be taken into account for this 'delta' only
        # when are visible
        mainwindow = self.get_main()
        delta_top = (mainwindow.toolbar.toolbars_menu.geometry().height() +
                        mainwindow.menuBar().geometry().height() + 6)

        switcher.set_position(delta_top)

    def open_symbolfinder(self):
        """Open symbol list management dialog box."""
        self.open_switcher(symbol=True)

    # --- Public API
    # ------------------------------------------------------------------------
