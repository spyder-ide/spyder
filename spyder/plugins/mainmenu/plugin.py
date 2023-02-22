# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""
Main menu Plugin.
"""

# Standard library imports
from collections import OrderedDict
import sys
from typing import Dict, List, Tuple, Optional, Union

# Third party imports
from qtpy.QtGui import QKeySequence

# Local imports
from spyder.api.exceptions import SpyderAPIError
from spyder.api.plugin_registration.registry import PLUGIN_REGISTRY
from spyder.api.plugins import SpyderPluginV2, SpyderDockablePlugin, Plugins
from spyder.api.translations import _
from spyder.api.widgets.menus import MENU_SEPARATOR, SpyderMenu
from spyder.plugins.mainmenu.api import ApplicationMenu, ApplicationMenus
from spyder.utils.qthelpers import set_menu_icons, SpyderAction


# Extended typing definitions
ItemType = Union[SpyderAction, SpyderMenu]
ItemSectionBefore = Tuple[
    ItemType, Optional[str], Optional[str], Optional[str]]
ItemQueue = Dict[str, List[ItemSectionBefore]]


class MainMenu(SpyderPluginV2):
    NAME = 'mainmenu'
    CONF_SECTION = NAME
    CONF_FILE = False
    CAN_BE_DISABLED = False

    @staticmethod
    def get_name():
        return _('Main menus')

    def get_icon(self):
        return self.create_icon('genprefs')

    def get_description(self):
        return _('Provide main application menu management.')

    def on_initialize(self):
        # Reference holder dict for the menus
        self._APPLICATION_MENUS = OrderedDict()

        # Queue that contain items that are pending to add to a non-existing
        # menu
        self._ITEM_QUEUE = {}  # type: ItemQueue

        # Create Application menus using plugin public API
        # FIXME: Migrated menus need to have 'dynamic=True' (default value) to
        # work on Mac. Remove the 'dynamic' kwarg when migrating a menu!
        create_app_menu = self.create_application_menu
        create_app_menu(ApplicationMenus.File, _("&File"))
        create_app_menu(ApplicationMenus.Edit, _("&Edit"), dynamic=False)
        create_app_menu(ApplicationMenus.Search, _("&Search"), dynamic=False)
        create_app_menu(ApplicationMenus.Source, _("Sour&ce"), dynamic=False)
        create_app_menu(ApplicationMenus.Run, _("&Run"), dynamic=False)
        create_app_menu(ApplicationMenus.Debug, _("&Debug"), dynamic=False)
        if self.is_plugin_enabled(Plugins.IPythonConsole):
            create_app_menu(ApplicationMenus.Consoles, _("C&onsoles"))
        if self.is_plugin_enabled(Plugins.Projects):
            create_app_menu(ApplicationMenus.Projects, _("&Projects"))
        create_app_menu(ApplicationMenus.Tools, _("&Tools"))
        create_app_menu(ApplicationMenus.View, _("&View"))
        create_app_menu(ApplicationMenus.Help, _("&Help"))

    def on_mainwindow_visible(self):
        # Pre-render menus so actions with menu roles (like "About Spyder"
        # and "Preferences") are located in the right place in Mac's menu
        # bar.
        # Fixes spyder-ide/spyder#14917
        # This also registers shortcuts for actions that are only in menus.
        # Fixes spyder-ide/spyder#16061
        for menu in self._APPLICATION_MENUS.values():
            menu._render()

    # ---- Private methods
    # ------------------------------------------------------------------------
    def _show_shortcuts(self, menu):
        """
        Show action shortcuts in menu.

        Parameters
        ----------
        menu: SpyderMenu
            Instance of a spyder menu.
        """
        menu_actions = menu.actions()
        for action in menu_actions:
            if getattr(action, '_shown_shortcut', False):
                # This is a SpyderAction
                if action._shown_shortcut is not None:
                    action.setShortcut(action._shown_shortcut)
            elif action.menu() is not None:
                # This is submenu, so we need to call this again
                self._show_shortcuts(action.menu())
            else:
                # We don't need to do anything for other elements
                continue

    def _hide_shortcuts(self, menu):
        """
        Hide action shortcuts in menu.

        Parameters
        ----------
        menu: SpyderMenu
            Instance of a spyder menu.
        """
        menu_actions = menu.actions()
        for action in menu_actions:
            if getattr(action, '_shown_shortcut', False):
                # This is a SpyderAction
                if action._shown_shortcut is not None:
                    action.setShortcut(QKeySequence())
            elif action.menu() is not None:
                # This is submenu, so we need to call this again
                self._hide_shortcuts(action.menu())
            else:
                # We don't need to do anything for other elements
                continue

    def _hide_options_menus(self):
        """Hide options menu when menubar is pressed in macOS."""
        for plugin_name in PLUGIN_REGISTRY:
            plugin_instance = PLUGIN_REGISTRY.get_plugin(plugin_name)
            if isinstance(plugin_instance, SpyderDockablePlugin):
                if plugin_instance.CONF_SECTION == 'editor':
                    editorstack = self.editor.get_current_editorstack()
                    editorstack.menu.hide()
                else:
                    try:
                        # New API
                        plugin_instance.options_menu.hide()
                    except AttributeError:
                        # Old API
                        plugin_instance._options_menu.hide()

    def _setup_menus(self):
        """Setup menus."""
        # Show and hide shortcuts and icons in menus for macOS
        if sys.platform == 'darwin':
            for menu_id in self._APPLICATION_MENUS:
                menu = self._APPLICATION_MENUS[menu_id]
                if menu is not None:
                    menu.aboutToShow.connect(
                        lambda menu=menu: self._show_shortcuts(menu))
                    menu.aboutToHide.connect(
                        lambda menu=menu: self._hide_shortcuts(menu))
                    menu.aboutToShow.connect(
                        lambda menu=menu: set_menu_icons(menu, False))
                    menu.aboutToShow.connect(self._hide_options_menus)

    # ---- Public API
    # ------------------------------------------------------------------------
    def create_application_menu(self, menu_id: str, title: str,
                                dynamic: bool = True):
        """
        Create a Spyder application menu.

        Parameters
        ----------
        menu_id: str
            The menu unique identifier string.
        title: str
            The localized menu title to be displayed.
        """
        if menu_id in self._APPLICATION_MENUS:
            raise SpyderAPIError(
                'Menu with id "{}" already added!'.format(menu_id))

        menu = ApplicationMenu(self.main, title, dynamic=dynamic)
        menu.menu_id = menu_id

        self._APPLICATION_MENUS[menu_id] = menu
        self.main.menuBar().addMenu(menu)

        # Show and hide shortcuts and icons in menus for macOS
        if sys.platform == 'darwin':
            menu.aboutToShow.connect(
                lambda menu=menu: self._show_shortcuts(menu))
            menu.aboutToHide.connect(
                lambda menu=menu: self._hide_shortcuts(menu))
            menu.aboutToShow.connect(
                lambda menu=menu: set_menu_icons(menu, False))
            menu.aboutToShow.connect(self._hide_options_menus)

        if menu_id in self._ITEM_QUEUE:
            pending_items = self._ITEM_QUEUE.pop(menu_id)
            for pending in pending_items:
                (item, section,
                 before_item, before_section) = pending
                self.add_item_to_application_menu(
                    item, menu_id=menu_id, section=section,
                    before=before_item, before_section=before_section)

        return menu

    def add_item_to_application_menu(self, item: ItemType,
                                     menu_id: Optional[str] = None,
                                     section: Optional[str] = None,
                                     before: Optional[str] = None,
                                     before_section: Optional[str] = None,
                                     omit_id: bool = False):
        """
        Add action or widget `item` to given application menu `section`.

        Parameters
        ----------
        item: SpyderAction or SpyderMenu
            The item to add to the `menu`.
        menu_id: str or None
            The application menu unique string identifier.
        section: str or None
            The section id in which to insert the `item` on the `menu`.
        before: str
            Make the item appear before the given object identifier.
        before_section: Section or None
            Make the item section (if provided) appear before another
            given section.
        omit_id: bool
            If True, then the menu will check if the item to add declares an
            id, False otherwise. This flag exists only for items added on
            Spyder 4 plugins. Default: False

        Notes
        -----
        Must provide a `menu` or a `menu_id`.
        """
        if not isinstance(item, (SpyderAction, SpyderMenu)) and not omit_id:
            raise SpyderAPIError('A menu only accepts items objects of type '
                                 'SpyderAction or SpyderMenu')

        # TODO: For now just add the item to the bottom for non-migrated menus.
        #       Temporal solution while migration is complete
        app_menu_actions = {
            ApplicationMenus.Edit: self._main.edit_menu_actions,
            ApplicationMenus.Search: self._main.search_menu_actions,
            ApplicationMenus.Source: self._main.source_menu_actions,
            ApplicationMenus.Run: self._main.run_menu_actions,
            ApplicationMenus.Debug: self._main.debug_menu_actions,
        }

        if menu_id in app_menu_actions:
            actions = app_menu_actions[menu_id]
            actions.append(MENU_SEPARATOR)
            actions.append(item)
        else:
            if menu_id not in self._APPLICATION_MENUS:
                pending_menu_items = self._ITEM_QUEUE.get(menu_id, [])
                pending_menu_items.append((item, section, before,
                                           before_section))
                self._ITEM_QUEUE[menu_id] = pending_menu_items
            else:
                menu = self.get_application_menu(menu_id)
                menu.add_action(item, section=section, before=before,
                                before_section=before_section, omit_id=omit_id)

    def remove_application_menu(self, menu_id: str):
        """
        Remove a Spyder application menu.

        Parameters
        ----------
        menu_id: str
            The menu unique identifier string.
        """
        if menu_id in self._APPLICATION_MENUS:
            menu = self._APPLICATION_MENUS.pop(menu_id)
            self.main.menuBar().removeAction(menu.menuAction())

    def remove_item_from_application_menu(self, item_id: str,
                                          menu_id: Optional[str] = None):
        """
        Remove action or widget from given application menu by id.

        Parameters
        ----------
        item_id: str
            The item identifier to remove from the given menu.
        menu_id: str or None
            The application menu unique string identifier.
        """
        if menu_id not in self._APPLICATION_MENUS:
            raise SpyderAPIError('{} is not a valid menu_id'.format(menu_id))

        # TODO: For now just add the item to the bottom for non-migrated menus.
        #       Temporal solution while migration is complete
        app_menu_actions = {
            ApplicationMenus.Edit: (
                self._main.edit_menu_actions, self._main.edit_menu),
            ApplicationMenus.Search: (
                self._main.search_menu_actions, self._main.search_menu),
            ApplicationMenus.Source: (
                self._main.source_menu_actions, self._main.source_menu),
            ApplicationMenus.Run: (
                self._main.run_menu_actions, self._main.run_menu),
            ApplicationMenus.Debug: (
                self._main.debug_menu_actions, self._main.debug_menu),
        }

        app_menus = {
            ApplicationMenus.Edit: self._main.edit_menu,
            ApplicationMenus.Search: self._main.search_menu,
            ApplicationMenus.Source: self._main.source_menu,
            ApplicationMenus.Run: self._main.run_menu,
            ApplicationMenus.Debug: self._main.debug_menu
        }

        menu = self.get_application_menu(menu_id)

        if menu_id in app_menu_actions:
            actions = app_menu_actions[menu_id]  # type: list
            menu = app_menus[menu_id]
            position = None
            for i, action in enumerate(actions):
                this_item_id = None
                if (isinstance(action, SpyderAction) or
                        hasattr(action, 'action_id')):
                    this_item_id = action.action_id
                elif (isinstance(action, SpyderMenu) or
                        hasattr(action, 'menu_id')):
                    this_item_id = action.menu_id
                if this_item_id is not None and this_item_id == item_id:
                    position = i
                    break
            if position is not None:
                actions.pop(position)
                menu.remove_action(item_id)
        else:
            menu.remove_action(item_id)

    def get_application_menu(self, menu_id: str) -> SpyderMenu:
        """
        Return an application menu by menu unique id.

        Parameters
        ----------
        menu_id: ApplicationMenu
            The menu unique identifier string.
        """
        if menu_id not in self._APPLICATION_MENUS:
            raise SpyderAPIError(
                'Application menu "{0}" not found! Available '
                'menus are: {1}'.format(
                    menu_id, list(self._APPLICATION_MENUS.keys()))
            )

        return self._APPLICATION_MENUS[menu_id]
