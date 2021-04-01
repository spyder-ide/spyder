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

# Third party imports
from qtpy.QtGui import QKeySequence
from qtpy.QtWidgets import QMenu

# Local imports
from spyder.api.exceptions import SpyderAPIError
from spyder.api.plugins import Plugins, SpyderPluginV2, SpyderDockablePlugin
from spyder.api.translations import get_translation
from spyder.api.widgets.menus import MENU_SEPARATOR
from spyder.plugins.mainmenu.api import (
    ApplicationMenu, ApplicationMenus, HelpMenuSections)
from spyder.utils.qthelpers import add_actions, set_menu_icons

# Localization
_ = get_translation('spyder')


class MainMenu(SpyderPluginV2):
    NAME = 'mainmenu'
    CONF_SECTION = NAME
    CONF_FILE = False

    def get_name(self):
        return _('Main menus')

    def get_icon(self):
        return self.create_icon('genprefs')

    def get_description(self):
        return _('Provide main application menu management.')

    def register(self):
        # Reference holder dict for the menus
        self._APPLICATION_MENUS = OrderedDict()
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
        create_app_menu(
            ApplicationMenus.Consoles, _("C&onsoles"), dynamic=False)
        create_app_menu(
            ApplicationMenus.Projects, _("&Projects"), dynamic=False)
        create_app_menu(ApplicationMenus.Tools, _("&Tools"))
        create_app_menu(ApplicationMenus.View, _("&View"))
        create_app_menu(ApplicationMenus.Help, _("&Help"))

    # --- Private methods
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
        for _plugin_id, plugin in self.main._PLUGINS.items():
            if isinstance(plugin, SpyderDockablePlugin):
                if plugin.CONF_SECTION == 'editor':
                    editorstack = self.editor.get_current_editorstack()
                    editorstack.menu.hide()
                else:
                    try:
                        # New API
                        plugin.options_menu.hide()
                    except AttributeError:
                        # Old API
                        plugin._options_menu.hide()

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

    # --- Public API
    # ------------------------------------------------------------------------
    def create_application_menu(self, menu_id, title, dynamic=True):
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
        if menu_id == ApplicationMenus.Projects:
            menu.setObjectName('checkbox-padding')

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

        return menu

    def add_item_to_application_menu(self, item, menu=None, menu_id=None,
                                     section=None, before=None,
                                     before_section=None):
        """
        Add action or widget `item` to given application menu `section`.

        Parameters
        ----------
        item: SpyderAction or SpyderMenu
            The item to add to the `menu`.
        menu: ApplicationMenu or None
            Instance of a Spyder application menu.
        menu_id: str or None
            The application menu unique string identifier.
        section: str or None
            The section id in which to insert the `item` on the `menu`.
        before: SpyderAction/SpyderMenu or None
            Make the item appear before another given item.
        before_section: Section or None
            Make the item section (if provided) appear before another
            given section.

        Notes
        -----
        Must provide a `menu` or a `menu_id`.
        """
        if menu and menu_id:
            raise SpyderAPIError('Must provide only menu or menu_id!')

        if menu is None and menu_id is None:
            raise SpyderAPIError('Must provide at least menu or menu_id!')

        if menu and not isinstance(menu, ApplicationMenu):
            raise SpyderAPIError('Not an `ApplicationMenu`!')

        if menu_id and menu_id not in self._APPLICATION_MENUS:
            raise SpyderAPIError('{} is not a valid menu_id'.format(menu_id))

        # TODO: For now just add the item to the bottom for non-migrated menus.
        #       Temporal solution while migration is complete
        app_menu_actions = {
            ApplicationMenus.Edit: self._main.edit_menu_actions,
            ApplicationMenus.Search: self._main.search_menu_actions,
            ApplicationMenus.Source: self._main.source_menu_actions,
            ApplicationMenus.Run: self._main.run_menu_actions,
            ApplicationMenus.Debug: self._main.debug_menu_actions,
            ApplicationMenus.Consoles: self._main.consoles_menu_actions,
            ApplicationMenus.Projects: self._main.projects_menu_actions,
        }

        menu_id = menu_id if menu_id else menu.menu_id
        menu = menu if menu else self.get_application_menu(menu_id)

        if menu_id in app_menu_actions:
            actions = app_menu_actions[menu_id]
            actions.append(MENU_SEPARATOR)
            actions.append(item)
        else:
            menu.add_action(item, section=section, before=before,
                            before_section=before_section)

    def get_application_menu(self, menu_id):
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
