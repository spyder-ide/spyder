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
import os
import os.path as osp
import re
import sys

# Third party imports
from qtpy import API, PYQT5
from qtpy.QtCore import Qt, Slot
from qtpy.QtGui import QKeySequence
from qtpy.QtWidgets import QMenu

# Local imports
from spyder import __docs_url__
from spyder.api.exceptions import SpyderAPIError
from spyder.api.plugins import Plugins, SpyderPluginV2, SpyderDockablePlugin
from spyder.api.widgets.menus import SpyderMenu
from spyder.api.translations import get_translation
from spyder.api.widgets.menus import MENU_SEPARATOR
from spyder.app.utils import get_python_doc_path
from spyder.plugins.mainmenu.api import (
    ApplicationContextMenu, ApplicationMenu, ApplicationMenus,
    HelpMenuSections)
from spyder.plugins.mainmenu.container import (
    MainMenuActions, MainMenuContainer)
from spyder.utils import programs
from spyder.utils.qthelpers import (
    add_actions, create_module_bookmark_actions, create_program_action,
    file_uri, set_menu_icons)

# Localization
_ = get_translation('spyder')


class MainMenu(SpyderPluginV2):
    NAME = 'mainmenu'
    OPTIONAL = [Plugins.Help, Plugins.Shortcuts]
    CONTAINER_CLASS = MainMenuContainer
    CONF_SECTION = NAME
    CONF_FILE = False
    CONF_FROM_OPTIONS = {
        'check_updates_on_startup': ('main', 'check_updates_on_startup'),
    }

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
        create_app_menu = self.create_application_menu
        create_app_menu(ApplicationMenus.File, _("&File"))
        create_app_menu(ApplicationMenus.Edit, _("&Edit"))
        create_app_menu(ApplicationMenus.Search, _("&Search"))
        create_app_menu(ApplicationMenus.Source, _("Sour&ce"))
        create_app_menu(ApplicationMenus.Run, _("&Run"))
        create_app_menu(ApplicationMenus.Debug, _("&Debug"))
        create_app_menu(ApplicationMenus.Consoles, _("C&onsoles"))
        create_app_menu(ApplicationMenus.Projects, _("&Projects"))
        create_app_menu(ApplicationMenus.Tools, _("&Tools"))
        create_app_menu(ApplicationMenus.View, _("&View"))
        create_app_menu(ApplicationMenus.Help, _("&Help"))

    def on_mainwindow_visible(self):
        self._setup_menus()

    # --- Private methods
    # ------------------------------------------------------------------------

    def _populate_help_menu(self):
        """Add base actions and menus to te Help menu."""
        self._populate_help_menu_support_section()
        self._populate_help_menu_about_section()

    def _populate_help_menu_support_section(self):
        """Create Spyder base support actions."""
        help_plugin = self.get_plugin(Plugins.Help)
        help_support_action = None
        if help_plugin:
            from spyder.plugins.help.plugin import HelpActions
            help_support_action = help_plugin.get_action(
                HelpActions.SpyderSupportAction)

        for support_action in [self.dependencies_action,
                               self.check_updates_action]:
            self.add_item_to_application_menu(
                support_action,
                menu_id=ApplicationMenus.Help,
                section=HelpMenuSections.Support,
                before=help_support_action,
                before_section=HelpMenuSections.ExternalDocumentation)

    def _populate_help_menu_about_section(self):
        """Create Spyder base about actions."""
        self.add_item_to_application_menu(
            self.about_action,
            menu_id=ApplicationMenus.Help,
            section=HelpMenuSections.About)

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
            for menu in self._APPLICATION_MENUS:
                if menu is not None:
                    menu.aboutToShow.connect(
                        lambda menu=menu: self.show_shortcuts(menu))
                    menu.aboutToHide.connect(
                        lambda menu=menu: self.hide_shortcuts(menu))
                    menu.aboutToShow.connect(
                        lambda menu=menu: set_menu_icons(menu, False))
                    menu.aboutToShow.connect(self.hide_options_menus)
        self._populate_help_menu()

    # --- Public API
    # ------------------------------------------------------------------------
    def create_application_menu(self, menu_id, title):
        """
        Create a Spyder application menu.

        Paramaters
        ----------
        menu_id: str
            The menu unique identifier string.
        title: str
            The localized menu title to be displayed.
        """
        if menu_id in self._APPLICATION_MENUS:
            raise SpyderAPIError(
                'Menu with id "{}" already added!'.format(menu_id))

        menu = ApplicationMenu(self.main, title)
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
            ApplicationMenus.File: self._main.file_menu_actions,
            ApplicationMenus.Edit: self._main.edit_menu_actions,
            ApplicationMenus.Search: self._main.search_menu_actions,
            ApplicationMenus.Source: self._main.source_menu_actions,
            ApplicationMenus.Run: self._main.run_menu_actions,
            ApplicationMenus.Debug: self._main.debug_menu_actions,
            ApplicationMenus.Consoles: self._main.consoles_menu_actions,
            ApplicationMenus.Projects: self._main.projects_menu_actions,
            ApplicationMenus.Tools: self._main.tools_menu_actions,
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

    def get_application_context_menu(self, parent=None):
        """
        Return menu with the actions to be shown by the Spyder context menu.
        """
        documentation_action = None
        tutorial_action = None
        shortcuts_action = None

        help_plugin = self.get_plugin(Plugins.Help)
        shortcuts = self.get_plugin(Plugins.Shortcuts)
        menu = QMenu(parent=parent)
        actions = []
        # Help actions
        if help_plugin:
            from spyder.plugins.help.plugin import HelpActions
            documentation_action = help_plugin.get_action(
                HelpActions.SpyderDocumentationAction)
            tutorial_action = help_plugin.get_action(
                HelpActions.ShowSpyderTutorialAction)
            actions += [documentation_action, tutorial_action]
        # Shortcuts actions
        if shortcuts:
            from spyder.plugins.shortcuts.plugin import ShortcutActions
            shortcuts_action = shortcuts.get_action(
                ShortcutActions.ShortcutSummaryAction)
            actions.append(shortcuts_action)
        # MainMenu actions
        actions += [MENU_SEPARATOR, self.about_action]

        add_actions(menu, actions)

        return menu

    @property
    def dependencies_action(self):
        """Show Spyder's Dependencies dialog box."""
        return self.get_container().dependencies_action

    @property
    def check_updates_action(self):
        """Check if a new version of Spyder is available."""
        return self.get_container().check_updates_action

    @property
    def about_action(self):
        """Show Spyder's About dialog box."""
        return self.get_container().about_action
