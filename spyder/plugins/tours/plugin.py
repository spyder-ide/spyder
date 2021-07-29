# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright (c) 2009- Spyder Project Contributors
#
# Distributed under the terms of the MIT License
# (see spyder/__init__.py for details)
# -----------------------------------------------------------------------------

"""
Tours Plugin.
"""

# Local imports
from spyder.api.plugins import Plugins, SpyderPluginV2
from spyder.api.plugin_registration.decorators import on_plugin_available
from spyder.api.translations import get_translation
from spyder.config.base import get_safe_mode, running_under_pytest
from spyder.plugins.application.api import ApplicationActions
from spyder.plugins.tours.container import ToursContainer
from spyder.plugins.tours.tours import INTRO_TOUR, TourIdentifiers
from spyder.plugins.mainmenu.api import ApplicationMenus, HelpMenuSections

# Localization
_ = get_translation('spyder')


# --- Plugin
# ----------------------------------------------------------------------------
class Tours(SpyderPluginV2):
    """
    Tours Plugin.
    """
    NAME = 'tours'
    CONF_SECTION = NAME
    OPTIONAL = [Plugins.MainMenu]
    CONF_FILE = False
    CONTAINER_CLASS = ToursContainer

    # --- SpyderPluginV2 API
    # ------------------------------------------------------------------------
    def get_name(self):
        return _("Interactive tours")

    def get_description(self):
        return _("Provide interactive tours.")

    def get_icon(self):
        return self.create_icon('tour')

    def on_initialize(self):
        self.register_tour(
            TourIdentifiers.IntroductionTour,
            _("Introduction to Spyder"),
            INTRO_TOUR,
        )

    @on_plugin_available(plugin=Plugins.MainMenu)
    def on_main_menu_available(self):
        mainmenu = self.get_plugin(Plugins.MainMenu)

        docs_action = self.get_action(
            ApplicationActions.SpyderDocumentationAction,
            plugin=Plugins.Application)

        mainmenu.add_item_to_application_menu(
            self.get_container().tour_action,
            menu_id=ApplicationMenus.Help,
            section=HelpMenuSections.Documentation,
            before=docs_action)

    def on_mainwindow_visible(self):
        self.show_tour_message()

    # --- Public API
    # ------------------------------------------------------------------------
    def register_tour(self, tour_id, title, tour_data):
        """
        Register a new interactive tour on spyder.

        Parameters
        ----------
        tour_id: str
            Unique tour string identifier.
        title: str
            Localized tour name.
        tour_data: dict
            The tour steps.
        """
        self.get_container().register_tour(tour_id, title, tour_data)

    def show_tour(self, index):
        """
        Show interactive tour.

        Parameters
        ----------
        index: int
            The tour index to display.
        """
        self.main.maximize_dockwidget(restore=True)
        self.get_container().show_tour(index)

    def show_tour_message(self, force=False):
        """
        Show message about starting the tour the first time Spyder starts.

        Parameters
        ----------
        force: bool
            Force the display of the tour message.
        """
        should_show_tour = self.get_conf('show_tour_message')
        if force or (should_show_tour and not running_under_pytest()
                     and not get_safe_mode()):
            self.set_conf('show_tour_message', False)
            self.get_container().show_tour_message()
