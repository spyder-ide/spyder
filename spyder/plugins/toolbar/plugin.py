# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""
Toolbar Plugin.
"""

# Local imports
from spyder.api.exceptions import SpyderAPIError
from spyder.api.plugins import SpyderPluginV2, Plugins
from spyder.api.translations import get_translation
from spyder.plugins.mainmenu.api import ApplicationMenus, ViewMenuSections
from spyder.plugins.toolbar.api import ApplicationToolbars
from spyder.plugins.toolbar.container import ToolbarContainer

# Localization
_ = get_translation('spyder')


class Toolbar(SpyderPluginV2):
    """
    Docstrings viewer widget.
    """
    NAME = 'toolbar'
    OPTIONAL = [Plugins.MainMenu]
    CONF_SECTION = NAME
    CONF_FILE = False
    CONTAINER_CLASS = ToolbarContainer

    # --- SpyderDocakblePlugin API
    #  -----------------------------------------------------------------------
    def get_name(self):
        return _('Toolbar')

    def get_description(self):
        return _('Application toolbars management.')

    def get_icon(self):
        return self.create_icon('help')

    def register(self):
        create_app_toolbar = self.create_application_toolbar
        create_app_toolbar(ApplicationToolbars.File, _("File toolbar"))
        create_app_toolbar(ApplicationToolbars.Run, _("Run toolbar"))
        create_app_toolbar(ApplicationToolbars.Debug, _("Debug toolbar"))
        create_app_toolbar(ApplicationToolbars.Main, _("Main toolbar"))

        mainmenu = self.get_plugin(Plugins.MainMenu)
        if mainmenu:
            # View menu Toolbar section
            mainmenu.add_item_to_application_menu(
                    self.toolbars_menu,
                    menu_id=ApplicationMenus.View,
                    section=ViewMenuSections.Toolbar)
            mainmenu.add_item_to_application_menu(
                    self.show_toolbars_action,
                    menu_id=ApplicationMenus.View,
                    section=ViewMenuSections.Toolbar)

    def on_mainwindow_visible(self):
        container = self.get_container()

        # TODO: Until all core plugins are migrated, this is needed.
        ACTION_MAP = {
            ApplicationToolbars.File: self._main.file_toolbar_actions,
            ApplicationToolbars.Debug: self._main.debug_toolbar_actions,
            ApplicationToolbars.Run: self._main.run_toolbar_actions,
        }
        for toolbar in container.get_application_toolbars():
            toolbar_id = toolbar.ID
            if toolbar_id in ACTION_MAP:
                section = 0
                for item in ACTION_MAP[toolbar_id]:
                    if item is None:
                        section += 1
                        continue

                    self.add_item_to_application_toolbar(
                        item,
                        toolbar_id=toolbar_id,
                        section=str(section),
                    )

            toolbar._render()

        container.create_toolbars_menu()
        container.load_last_visible_toolbars()

    def on_close(self):
        container = self.get_container()
        if container._toolbars_visible:
            self.save_visible_toolbars()

    # --- Public API
    # ------------------------------------------------------------------------
    def create_application_toolbar(self, toolbar_id, title):
        """
        Create a Spyder application toolbar.

        Parameters
        ----------
        toolbar_id: str
            The toolbar unique identifier string.
        title: str
            The localized toolbar title to be displayed.

        Returns
        -------
        spyder.api.widgets.toolbar.ApplicationToolbar
            The created application toolbar.
        """
        toolbar = self.get_container().create_application_toolbar(
            toolbar_id, title)
        self.add_application_toolbar(toolbar)
        return toolbar

    def add_application_toolbar(self, toolbar):
        """
        Add toolbar to application toolbars.

        This can be used to add a custom toolbar. The `WorkingDirectory`
        plugin is an example of this.

        Parameters
        ----------
        toolbar: spyder.api.widgets.toolbars.ApplicationToolbar
            The application toolbar to add to the main window.
        """
        self.get_container().add_application_toolbar(toolbar, self._main)

    def add_item_to_application_toolbar(self, item, toolbar=None,
                                        toolbar_id=None, section=None,
                                        before=None, before_section=None):
        """
        Add action or widget `item` to given application menu `section`.

        Parameters
        ----------
        item: SpyderAction or QWidget
            The item to add to the `toolbar`.
        toolbar: ApplicationToolbar or None
            Instance of a Spyder application toolbar.
        toolbar_id: str or None
            The application toolbar unique string identifier.
        section: str or None
            The section id in which to insert the `item` on the `toolbar`.
        before: str or None
            Make the item appear before another given item.
        before_section: str or None
            Make the item defined section appear before another given section
            (must be already defined).

        Notes
        -----
        Must provide a `toolbar` or a `toolbar_id`.
        """
        return self.get_container().add_item_to_application_toolbar(
                item,
                toolbar=toolbar,
                toolbar_id=toolbar_id,
                section=section,
                before=before,
                before_section=before_section
            )

    def get_application_toolbar(self, toolbar_id):
        """
        Return an application toolbar by toolbar_id.

        Parameters
        ----------
        toolbar_id: str
            The toolbar unique string identifier.

        Returns
        -------
        spyder.api.widgets.toolbars.ApplicationToolbar
            The application toolbar.
        """
        return self.get_container().get_application_toolbar(toolbar_id)

    def toggle_lock(self, value=None):
        """Lock/Unlock toolbars."""
        for toolbar in self.toolbarslist:
            toolbar.setMovable(not value)

    # --- Convenience properties, while all plugins migrate.
    @property
    def toolbars_menu(self):
        return self.get_container().get_menu("toolbars_menu")

    @property
    def show_toolbars_action(self):
        return self.get_action("show toolbars")

    @property
    def toolbarslist(self):
        return self.get_container()._toolbarslist
