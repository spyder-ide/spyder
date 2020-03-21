# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""
Spyder API menu widgets.
"""

# Third party imports
from qtpy.QtWidgets import QMenu

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

    def __init__(self, parent=None, title=None):
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
        self.aboutToShow.connect(self._render)

    def add_action(self, action, section=None, before=None):
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

        if section not in self._sections:
            self._sections.append(section)

        # Track state of menu to avoid re-rendering if menu has not changed
        self._dirty = True
        self._ordered_actions = []

    def get_title(self):
        """
        Return the title for menu.
        """
        return self._title

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
            actions = []
            for section in self._sections:
                for (sec, action) in self._actions:
                    if sec == section:
                        actions.append(action)

                actions.append(MENU_SEPARATOR)

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


class ApplicationMenu(SpyderMenu):
    """
    Spyder Main Window application Menu.

    This class provides application menus with some predefined functionality
    and section definition.
    """
