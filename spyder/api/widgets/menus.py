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
from typing import Optional, Union, TypeVar

# Third party imports
from qtpy.QtWidgets import QAction, QMenu

# Local imports
from spyder.api.exceptions import SpyderAPIError
from spyder.utils.qthelpers import add_actions, SpyderAction


# --- Constants
# ----------------------------------------------------------------------------
MENU_SEPARATOR = None


# Generic type annotations
T = TypeVar('T', bound='SpyderMenu')


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

    def __init__(self, parent=None, title=None, dynamic=True,
                 menu_id=None):
        self._parent = parent
        self._title = title
        self._sections = []
        self._actions = []
        self._actions_map = {}
        self.unintroduced_actions = {}
        self.unintroduced_sections = []
        self._dirty = False
        self.menu_id = menu_id

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

    def clear_actions(self):
        """
        Remove actions from the menu (including custom references)

        Returns
        -------
        None.
        """
        self.clear()
        self._sections = []
        self._actions = []
        self._actions_map = {}
        self.unintroduced_actions = {}
        self.unintroduced_sections = []

    def add_action(self: T,
                   action: Union[SpyderAction, T],
                   section: Optional[str] = None,
                   before: Optional[str] = None,
                   before_section: Optional[str] = None,
                   check_before: bool = True,
                   omit_id: bool = False):
        """
        Add action to a given menu section.

        Parameters
        ----------
        action: SpyderAction
            The action to add.
        section: str or None
            The section id in which to insert the `action`.
        before: str
            Make the action appear before the given action identifier.
        before_section: str or None
            Make the item section (if provided) appear before another
            given section.
        check_before: bool
            Check if the `before` action is part of the menu. This is
            necessary to avoid an infinite recursion when adding
            unintroduced actions with this method again.
        omit_id: bool
            If True, then the menu will check if the item to add declares an
            id, False otherwise. This flag exists only for items added on
            Spyder 4 plugins. Default: False
        """
        item_id = None
        if isinstance(action, SpyderAction) or hasattr(action, 'action_id'):
            item_id = action.action_id
        elif isinstance(action, SpyderMenu) or hasattr(action, 'menu_id'):
            item_id = action.menu_id

        if not omit_id and item_id is None and action is not None:
            raise AttributeError(f'Item {action} must declare an id.')

        if before is None:
            self._actions.append((section, action))
        else:
            new_actions = []
            added = False
            before_item = self._actions_map.get(before, None)

            for sec, act in self._actions:
                if before_item is not None and act == before_item:
                    added = True
                    new_actions.append((section, action))

                new_actions.append((sec, act))

            # Actions can't be added to the menu if the `before` action is
            # not part of it yet. That's why we need to save them in the
            # `unintroduced_actions` dict, so we can add them again when
            # the menu is rendered.
            if not added and check_before:
                before_actions = self.unintroduced_actions.get(before, [])
                before_actions.append((section, action))
                self.unintroduced_actions[before] = before_actions

            self._actions = new_actions

        if before_section is not None:
            if before_section in self._sections:
                self._update_sections(section, before_section)
            else:
                # If `before_section` has not been introduced yet to the menu,
                # we save `section` to introduce it when the menu is rendered.
                if (section, before_section) not in self.unintroduced_sections:
                    self.unintroduced_sections.append(
                        (section, before_section)
                    )
        elif section not in self._sections:
            self._sections.append(section)

        # Track state of menu to avoid re-rendering if menu has not changed
        self._dirty = True
        self._actions_map[item_id] = action

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

            # Iterate over unintroduced sections until all of them have been
            # introduced.
            try:
                iter_sections = iter(self.unintroduced_sections)
                while len(self.unintroduced_sections) > 0:
                    section, before_section = next(iter_sections)
                    self._update_sections(section, before_section)

                    # If section was introduced, remove it from the list and
                    # update iterator.
                    if section in self._sections:
                        self.unintroduced_sections.remove(
                            (section, before_section)
                        )
                        iter_sections = iter(self.unintroduced_sections)
            except StopIteration:
                # Internally, this should only happen in the Tools menu because
                # the External section can be empty if Kite is not available.
                # Fixes spyder-ide/spyder#16287
                # Note: We can't use the ToolsMenuSections enum here to prevent
                # a circular import.
                left_sections = [('tools_section', 'external_section')]

                if self.unintroduced_sections == left_sections:
                    self._update_sections('tools_section', 'extras_section')
                else:
                    raise SpyderAPIError(
                        f"You're trying to introduce some sections before "
                        f"others that don't have any actions. This is the "
                        f"list of (section, before_section) that's failing to "
                        f"be added:\n\n{self.unintroduced_sections}"
                    )

            # Update actions with those that were not introduced because
            # a `before` action they required was not part of the menu yet.
            for before, actions in self.unintroduced_actions.items():
                for section, action in actions:
                    self.add_action(action, section=section,
                                    before=before, check_before=False)

            actions = self.get_actions()
            add_actions(self, actions)
            self._dirty = False

    def _update_sections(self, section, before_section):
        """Update sections ordering."""
        new_sections = []
        for sec in self._sections:
            if sec == before_section:
                new_sections.append(section)
            if sec != section:
                new_sections.append(sec)
        self._sections = new_sections


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
            self._dirty = False
