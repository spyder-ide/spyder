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
from spyder.utils.qthelpers import add_actions, SpyderAction


# ---- Constants
# -----------------------------------------------------------------------------
MENU_SEPARATOR = None


# Generic type annotations
T = TypeVar('T', bound='SpyderMenu')


class OptionsMenuSections:
    Top = 'top_section'
    Bottom = 'bottom_section'


class PluginMainWidgetMenus:
    Context = 'context_menu'
    Options = 'options_menu'


# ---- Widgets
# -----------------------------------------------------------------------------
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
        self._after_sections = {}
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
        self._after_sections = {}

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

        if section not in self._sections:
            self._add_section(section, before_section)

        # Track state of menu to avoid re-rendering if menu has not changed
        self._dirty = True
        self._actions_map[item_id] = action

    def remove_action(self, item_id: str):
        if item_id in self._actions_map:
            action = self._actions_map.pop(item_id)
            position = None

            for i, (_, act) in enumerate(self._actions):
                if act == action:
                    position = i
                    break

            if position is not None:
                self._actions.pop(position)
                self._dirty = True

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

            # Update actions with those that were not introduced because
            # a `before` action they required was not part of the menu yet.
            for before, actions in self.unintroduced_actions.items():
                for section, action in actions:
                    self.add_action(action, section=section,
                                    before=before, check_before=False)

            actions = self.get_actions()
            add_actions(self, actions)
            self._dirty = False

    def _add_section(self, section, before_section=None):
        """
        Add a new section to the list of sections in this menu.

        Parameters
        ----------
        before_section: str or None
            Make `section` appear before another one.
        """
        inserted_before_other = False

        if before_section is not None:
            if before_section in self._sections:
                # If before_section was already introduced, we simply need to
                # insert the new section on its position, which will put it
                # exactly behind before_section.
                idx = self._sections.index(before_section)
                self._sections.insert(idx, section)
                inserted_before_other = True
            else:
                # If before_section hasn't been introduced yet, we know we need
                # to insert it after section when it's finally added to the
                # menu. So, we preserve that info in the _after_sections dict.
                self._after_sections[before_section] = section

                # Append section to the list of sections because we assume
                # people build menus from top to bottom, i.e. they add its
                # upper sections first.
                self._sections.append(section)
        else:
            self._sections.append(section)

        # Check if section should be inserted after another one, according to
        # what we have in _after_sections.
        after_section = self._after_sections.pop(section, None)

        if after_section is not None:
            if not inserted_before_other:
                # Insert section to the right of after_section, if it was not
                # inserted before another one.
                if section in self._sections:
                    self._sections.remove(section)

                index = self._sections.index(after_section)
                self._sections.insert(index + 1, section)
            else:
                # If section was already inserted before another one, then we
                # need to move after_section to its left instead.
                if after_section in self._sections:
                    self._sections.remove(after_section)

                idx = self._sections.index(section)
                idx = idx if (idx == 0) else (idx - 1)
                self._sections.insert(idx, after_section)


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
