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
import qstylizer.style
from qtpy.QtCore import Qt
from qtpy.QtWidgets import QAction, QMenu

# Local imports
from spyder.api.config.fonts import SpyderFontType, SpyderFontsMixin
from spyder.utils.qthelpers import add_actions, set_menu_icons, SpyderAction
from spyder.utils.palette import QStylePalette
from spyder.utils.stylesheet import AppStyle, MAC, WIN


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
class SpyderMenu(QMenu, SpyderFontsMixin):
    """
    A QMenu subclass to implement additional functionality for Spyder.
    """
    MENUS = []
    APP_MENU = False

    def __init__(self, parent=None, title=None, menu_id=None, min_width=None):
        self._parent = parent
        self._title = title
        self.menu_id = menu_id

        self._sections = []
        self._actions = []
        self._actions_map = {}
        self._unintroduced_actions = {}
        self._after_sections = {}
        self._dirty = False
        self._is_shown = False
        self._is_submenu = False
        self._reposition = True
        self._in_app_menu = False

        if title is None:
            super().__init__(parent)
        else:
            super().__init__(title, parent)

        self.MENUS.append((parent, title, self))

        # Set min width
        if min_width is not None:
            self.setMinimumWidth(min_width)

        # Signals
        self.aboutToShow.connect(self._render)

        # Adjustmens for Mac
        if sys.platform == 'darwin':
            # Needed to enable the dynamic population of actions in app menus
            # in the aboutToShow signal.
            # See spyder-ide/spyder#14612
            if self.APP_MENU:
                self.addAction(QAction(self))

            # Necessary to follow Mac's HIG for app menus.
            self.aboutToShow.connect(self._set_icons)

        # This line is necessary to have rounded borders in menu corners.
        # Solution taken from https://stackoverflow.com/a/65576117/438386
        #
        # Notes
        # -----
        # * This requires composition on Linux, but it's not possible to detect
        #   if that's available in Qt 6 and requires extra libraries in Qt 5.
        #   Hopefully it's a minor inconvenience to users without it.
        self.setAttribute(Qt.WA_TranslucentBackground)

        # Style
        self.css = self._generate_stylesheet()
        self.setStyleSheet(self.css.toString())

    # ---- Public API
    # -------------------------------------------------------------------------
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
        self._unintroduced_actions = {}
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
            action._is_submenu = True

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
            # `_unintroduced_actions` dict, so we can add them again when
            # the menu is rendered.
            if not added and check_before:
                before_actions = self._unintroduced_actions.get(before, [])
                before_actions.append((section, action))
                self._unintroduced_actions[before] = before_actions

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

    # ---- Private API
    # -------------------------------------------------------------------------
    def _render(self):
        """
        Create the menu prior to showing it. This takes into account sections
        and location of menus.
        """
        if self._dirty:
            self.clear()

            # Update actions with those that were not introduced because
            # a `before` action they required was not part of the menu yet.
            for before, actions in self._unintroduced_actions.items():
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

    def _set_icons(self):
        """
        Unset menu icons for app menus and set them for regular menus.

        This is necessary only for Mac to follow its Human Interface
        Guidelines (HIG), which don't recommend icons in app menus.
        """
        if sys.platform == "darwin":
            if self.APP_MENU or self._in_app_menu:
                set_menu_icons(self, False, in_app_menu=True)
            else:
                set_menu_icons(self, True)

    def _generate_stylesheet(self):
        """Generate base stylesheet for menus."""
        css = qstylizer.style.StyleSheet()
        font = self.get_font(SpyderFontType.Interface)

        # Add padding and border radius to follow modern standards
        css.QMenu.setValues(
            padding=f'{2 * AppStyle.MarginSize}px',
            # Add more radius than normal to make it more visible.
            borderRadius=(
                f'{2 * int(QStylePalette.SIZE_BORDER_RADIUS.split("px")[0])}px'
            )
        )

        # Set the right background color This is the only way to do it!
        css['QWidget:disabled QMenu'].setValues(
            backgroundColor=QStylePalette.COLOR_BACKGROUND_3,
        )

        # Add padding around separators to prevent that hovering on items hides
        # them.
        css["QMenu::separator"].setValues(
            margin=f'{2 * AppStyle.MarginSize}px 0px',
        )

        # Set menu item properties
        delta_top = 0 if (MAC or WIN) else 1
        delta_bottom = 0 if MAC else (2 if WIN else 1)
        css["QMenu::item"].setValues(
            height='1.1em' if MAC else ('1.35em' if WIN else '1.25em'),
            paddingTop=f'{AppStyle.MarginSize + delta_top}px',
            paddingBottom=f'{AppStyle.MarginSize + delta_bottom}px',
            paddingLeft=f'{3 * AppStyle.MarginSize}px',
            paddingRight=f'{3 * AppStyle.MarginSize}px',
            fontFamily=font.family(),
            fontSize=f'{font.pointSize()}pt',
            backgroundColor='transparent'
        )

        # Set hover and pressed state of items
        for state in ['selected', 'pressed']:
            if state == 'selected':
                bg_color = QStylePalette.COLOR_BACKGROUND_4
            else:
                bg_color = QStylePalette.COLOR_BACKGROUND_5

            css[f"QMenu::item:{state}"].setValues(
                backgroundColor=bg_color,
                borderRadius=QStylePalette.SIZE_BORDER_RADIUS
            )

        # Set state of disabled items
        css["QMenu::item:selected:disabled"].setValues(
            color=QStylePalette.COLOR_DISABLED,
            backgroundColor="transparent"
        )

        return css

    def __str__(self):
        return f"SpyderMenu('{self.menu_id}')"

    def __repr__(self):
        return f"SpyderMenu('{self.menu_id}')"

    # ---- Qt methods
    # -------------------------------------------------------------------------
    def showEvent(self, event):
        """Adjustments when the menu is shown."""
        # Reposition menu vertically due to padding
        if (
            not sys.platform == "darwin"
            and self._reposition
            and self._is_submenu
            and not self._is_shown
        ):
            self.move(self.pos().x(), self.pos().y() - 2 * AppStyle.MarginSize)
            self._is_shown = True

        super().showEvent(event)


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
