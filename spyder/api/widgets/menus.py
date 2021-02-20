# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""
Spyder API menu widgets.
"""

# Standard library imports
import sys

# Third party imports
from qtpy.QtWidgets import QAction, QMenu

# Local imports
from spyder.utils.qthelpers import add_actions


# --- Constants
# ----------------------------------------------------------------------------
MENU_SEPARATOR = None


class OptionsMenuSections:
    Top = 'top_section'
    Bottom = 'bottom_section'


class PluginMainWidgetMenus:
    Context = 'context_menu'
    Options = 'options_menu'


# --- Widgets
# ----------------------------------------------------------------------------
class SpyderMenu(QMenu):
    """
    A QMenu subclass to implement additional functionality for Spyder.
    """
    MENUS = []

    def __init__(self, parent=None, title=None, dynamic=True):
        self._parent = parent
        self._title = title
        self._sections = []
        self._actions = []
        self._ordered_actions = []
        self._dirty = False

        if title is None:
            super().__init__(parent)
        else:
            super().__init__(title, parent)

        self.MENUS.append((parent, title, self))
        if sys.platform == 'darwin' and dynamic:
            # Needed to enable the dynamic population of actions in menus
            # in the aboutToShow signal
            # See spyder-ide/spyder#14612
            self.addAction(QAction(self))
        self.aboutToShow.connect(self._render)

    def add_action(self, action, section=None, before=None,
                   before_section=None):
        """
        Add action to a given menu section.
        """
        if before is None:
            self._actions.append((section, action))
        else:
            new_actions = []
            for sec, act in self._actions:
                if act == before:
                    new_actions.append((section, action))

                new_actions.append((sec, act))

            self._actions = new_actions

        if before_section is not None and before_section in self._sections:
            new_sections = []
            for sec in self._sections:
                if sec == before_section:
                    new_sections.append(section)
                if sec != section:
                    new_sections.append(sec)
            self._sections = new_sections
        elif section not in self._sections:
            self._sections.append(section)

        # Track state of menu to avoid re-rendering if menu has not changed
        self._dirty = True
        self._ordered_actions = []

    def get_title(self):
        """
        Return the title for menu.
        """
        return self._title

    def get_actions(self):
        """
        Return a parsed list of menu actions.

        Includes MENU_SEPARATOR taking into account the sections defined.
        """
        actions = []
        for section in self._sections:
            for (sec, action) in self._actions:
                if sec == section:
                    actions.append(action)

            actions.append(MENU_SEPARATOR)
        return actions

    def get_sections(self):
        """
        Return a tuple of menu sections.
        """
        return tuple(self._sections)

    def _render(self):
        """
        Create the menu prior to showing it. This takes into account sections
        and location of menus.
        """
        if self._dirty:
            self.clear()
            actions = self.get_actions()
            add_actions(self, actions)
            self._ordered_actions = actions
            self._dirty = False


class MainWidgetMenu(SpyderMenu):
    """
    This menu fixes the bottom section of the options menu.
    """

    def _render(self):
        """
        Create the menu prior to showing it. This takes into account sections
        and location of menus. It also hides consecutive separators if found.
        """
        if self._dirty:
            self.clear()
            bottom = OptionsMenuSections.Bottom
            actions = []
            for section in self._sections:
                for (sec, action) in self._actions:
                    if sec == section and sec != bottom:
                        actions.append(action)

                actions.append(MENU_SEPARATOR)

            # Add bottom actions
            for (sec, action) in self._actions:
                if sec == bottom:
                    actions.append(action)

            add_actions(self, actions)

            self._ordered_actions = actions
            self._dirty = False
