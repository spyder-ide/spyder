# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright (c) 2009- Spyder Project Contributors
#
# Distributed under the terms of the MIT License
# (see spyder/__init__.py for details)
# -----------------------------------------------------------------------------

"""
Tours Container.
"""

from collections import OrderedDict

# Local imports
from spyder.api.exceptions import SpyderAPIError
from spyder.api.translations import get_translation
from spyder.api.widgets.main_container import PluginMainContainer
from spyder.plugins.tours.tours import TourIdentifiers
from spyder.plugins.tours.widgets import AnimatedTour, OpenTourDialog

# Localization
_ = get_translation('spyder')

# Set the index for the default tour
DEFAULT_TOUR = TourIdentifiers.IntroductionTour


class TourActions:
    """
    Tours actions.
    """
    ShowTour = "show tour"


class ToursContainer(PluginMainContainer):
    """
    Tours container.
    """

    def __init__(self, name, plugin, parent=None):
        super().__init__(name, plugin, parent=parent)

        self._main = plugin.main
        self._tours = OrderedDict()
        self._tour_titles = OrderedDict()
        self._tour_widget = AnimatedTour(self._main)
        self._tour_dialog = OpenTourDialog(
            self, lambda: self.show_tour(DEFAULT_TOUR))
        self.tour_action = self.create_action(
            TourActions.ShowTour,
            text=_("Show tour"),
            icon=self.create_icon('tour'),
            triggered=lambda: self.show_tour(DEFAULT_TOUR)
        )

    # --- PluginMainContainer API
    # ------------------------------------------------------------------------
    def setup(self):
        self.tours_menu = self.create_menu(
            "tours_menu", _("Interactive tours"))

    def update_actions(self):
        pass

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
        if tour_id in self._tours:
            raise SpyderAPIError(
                "Tour with id '{}' has already been registered!".format(
                    tour_id))

        self._tours[tour_id] = tour_data
        self._tour_titles[tour_id] = title
        action = self.create_action(
            tour_id,
            text=title,
            triggered=lambda: self.show_tour(tour_id),
        )
        self.add_item_to_menu(action, menu=self.tours_menu)

    def show_tour(self, tour_id):
        """
        Show interactive tour.

        Parameters
        ----------
        tour_id: str
            Unique tour string identifier.
        """
        tour_data = self._tours[tour_id]
        dic = {'last': 0, 'tour': tour_data}
        self._tour_widget.set_tour(tour_id, dic, self._main)
        self._tour_widget.start_tour()

    def show_tour_message(self):
        """
        Show message about starting the tour the first time Spyder starts.
        """
        self._tour_dialog.show()
        self._tour_dialog.raise_()
