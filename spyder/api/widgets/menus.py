# -----------------------------------------------------------------------------
# Copyright (c) 2020- Spyder Project Contributors
#
# Released under the terms of the MIT License
# (see LICENSE.txt in the project root directory for details)
# -----------------------------------------------------------------------------

"""
Spyder API menu widgets.
"""

from __future__ import annotations

# Standard library imports
import sys
from typing import TypeVar, TYPE_CHECKING

# Third party imports
import qstylizer.style
from qtpy.QtCore import QTimer
from qtpy.QtGui import QCursor
from qtpy.QtWidgets import QAction, QMenu, QProxyStyle, QStyle

# Local imports
from spyder.api.fonts import SpyderFontType, SpyderFontsMixin
from spyder.utils.qthelpers import add_actions, set_menu_icons, SpyderAction
from spyder.utils.palette import SpyderPalette
from spyder.utils.stylesheet import AppStyle, MAC, WIN

if TYPE_CHECKING:
    from qtpy.QtGui import QShowEvent
    from qtpy.QtWidgets import QStyleOption, QWidget

    import spyder.utils.qthelpers  # For SpyderAction


# ---- Constants
# -----------------------------------------------------------------------------
MENU_SEPARATOR: None = None
"""Constant representing a separator line between groups in a menu."""


# Generic type annotations
T = TypeVar("T", bound="SpyderMenu")
"""Generic :class:`SpyderMenu` type variable (:class:`~typing.TypeVar`)."""


class OptionsMenuSections:
    """Pseudo-enum listing sections in the pane options (hamburger) menu."""

    Top: str = "top_section"
    """The top section of the options menu."""

    Bottom: str = "bottom_section"
    """The bottom section of the options menu."""


class PluginMainWidgetMenus:
    """Pseudo-enum listing the menu types dockable plugin main widgets have."""

    Context: str = "context_menu"
    """The widget context menu."""

    Options: str = "options_menu"
    """The widget options (hamburger) menu."""


# ---- Style
# -----------------------------------------------------------------------------
class SpyderMenuProxyStyle(QProxyStyle):
    """Menu style adjustments that can only be done with a proxy style.

    .. deprecated:: 6.2

        This class will be moved to the private :class:`!_SpyderMenuProxyStyle`
        in Spyder 6.2, while the current public name will become an alias
        raising a :exc:`DeprecationWarning` on use, and removed in 7.0.

        It was never intended to be used directly by plugins, and its
        functionality is automatically inherited by using :class:`SpyderMenu`.
    """

    def pixelMetric(
        self,
        metric: QStyle.PixelMetric,
        option: QStyleOption | None = None,
        widget: QWidget | None = None,
    ) -> int:
        """
        Calculate the value of the given pixel metric.

        This is a callback intended to be called internally by Qt.

        Parameters
        ----------
        metric : QStyle.PixelMetric
            The pixel metric to calculate.
        option : QStyleOption | None, optional
            The current style options, or ``None`` (default).
        widget : QWidget | None, optional
            The widget the pixel metric will be used for,
            or ``None`` (default).

        Returns
        -------
        int
            The resulting pixel metric value, used internally by Qt.
        """
        if metric == QStyle.PM_SmallIconSize:
            # Change icon size for menus.
            # Taken from https://stackoverflow.com/a/42145885/438386
            delta = -1 if MAC else (0 if WIN else 1)

            return (
                QProxyStyle.pixelMetric(self, metric, option, widget) + delta
            )

        return QProxyStyle.pixelMetric(self, metric, option, widget)


# ---- Widgets
# -----------------------------------------------------------------------------
class SpyderMenu(QMenu, SpyderFontsMixin):
    """
    A QMenu subclass implementing additional functionality for Spyder.

    All menus in Spyder must inherit from this class.
    """

    MENUS: list[tuple[QWidget | None, str | None, SpyderMenu]] = []
    """
    List of 3-tuples, one per menu, describing each menu.

    Contains the menu's parent widget object, its name as a string,
    and the :class:`SpyderMenu` object itself, in that order.
    """

    APP_MENU: bool = False
    """
    Whether this is a main application menu or a plugin menu.

    Set this to ``True`` if this is an application menu; ``False`` otherwise.
    """

    HORIZONTAL_MARGIN_FOR_ITEMS: int = 2 * AppStyle.MarginSize
    """The QSS horizontal (left/right) margin for menu items, in pixels."""

    HORIZONTAL_PADDING_FOR_ITEMS: int = 3 * AppStyle.MarginSize
    """The QSS horizontal (left/right) padding for menu items, in pixels."""

    def __init__(
        self,
        parent: QWidget | None = None,
        menu_id: str | None = None,
        title: str | None = None,
        min_width: int | None = None,
        reposition: bool = True,
    ):
        """
        Create a menu for Spyder.

        Parameters
        ----------
        parent: QWidget | None, optional
            The menu's parent widget, or ``None`` if no parent.
        menu_id: str | None, optional
            Unique string identifier for the menu, or ``None`` if no ID.
        title: str | None, optional
            Localized title for the menu, or ``None`` (default) if no title.
        min_width: int or None, optional
            Minimum width for the menu, or ``None`` (default) for no min width.
        reposition: bool, optional
            Whether to vertically reposition the menu due to its padding.
            ``True`` by default.

        Returns
        -------
        None
        """
        self.menu_id: str | None = menu_id
        """The unique string identifier for the menu (or ``None`` if unset)."""

        self._parent = parent
        self._title = title
        self._reposition = reposition

        self._sections = []
        self._actions = []
        self._actions_map = {}
        self._unintroduced_actions = {}
        self._after_sections = {}
        self._dirty = False
        self._is_shown = False
        self._is_submenu = False
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
        self.aboutToShow.connect(self.render)

        # Adjustments for Mac
        if sys.platform == "darwin":
            # Needed to enable the dynamic population of actions in app menus
            # in the aboutToShow signal.
            # See spyder-ide/spyder#14612
            if self.APP_MENU:
                self.addAction(QAction(self))

            # Necessary to follow Mac's HIG for app menus.
            self.aboutToShow.connect(self._set_icons)

        # Style
        self.css = self._generate_stylesheet()
        self.setStyleSheet(self.css.toString())

        style = SpyderMenuProxyStyle(None)
        style.setParent(self)
        self.setStyle(style)

    # ---- Public API
    # -------------------------------------------------------------------------
    def clear_actions(self) -> None:
        """
        Remove actions from the menu (including custom references).

        Returns
        -------
        None
        """
        self.clear()
        self._sections = []
        self._actions = []
        self._actions_map = {}
        self._unintroduced_actions = {}
        self._after_sections = {}

    def add_action(
        self,
        action: spyder.utils.qthelpers.SpyderAction | SpyderMenu,
        section: str | None = None,
        before: str | None = None,
        before_section: str | None = None,
        check_before: bool = True,
        omit_id: bool = False,
    ) -> None:
        """
        Add action to a given menu section.

        Parameters
        ----------
        action: spyder.utils.qthelpers.SpyderAction | SpyderMenu
            The action or menu object to add to the menu.
        section: str | None, optional
            The section id in which to insert the ``action``, or ``None``
            (default) for no section.
        before: str | None, optional
            Make the ``action`` appear before the action with the identifier
            ``before``. If ``None`` (default), add it to the end.
        before_section: str | None, optional
            Make the item section appear prior to ``before_section``.
            If ``None`` (the default), add the section to the end.
        check_before: bool, optional
            Check if the ``before`` action is already part of the menu
            before adding this one, and if so save it to be added later.
            This is necessary to avoid an infinite recursion when adding
            unintroduced actions with this method again. ``True`` by default.
        omit_id: bool, optional
            If ``False``, the default, then the menu will check if
            ``action.action_id`` exists and is set to a string, and raise
            an :exc:`AttributeError` if either is not the case.
            If ``True``, it will add the ``action`` anyway.

        Returns
        -------
        None

        Raises
        ------
        AttributeError
            If ``omit_id`` is ``False`` (the default) and ``action.action_id``
            does not exist or is not set to a string.
        """
        item_id = None
        if isinstance(action, SpyderAction) or hasattr(action, "action_id"):
            item_id = action.action_id

            # This is necessary when we set a menu for `action`, e.g. for
            # todo_list_action in EditorMainWidget.
            if action.menu() and isinstance(action.menu(), SpyderMenu):
                action.menu()._is_submenu = True
        elif isinstance(action, SpyderMenu) or hasattr(action, "menu_id"):
            item_id = action.menu_id
            action._is_submenu = True

        if not omit_id and item_id is None and action is not None:
            raise AttributeError(f"Item {action} must declare an id.")

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

    def remove_action(self, item_id: str) -> None:
        """
        Remove the action with the given string identifier.

        Parameters
        ----------
        item_id : str
            The string identifier of the action to remove.

        Returns
        -------
        None
        """
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

    def get_title(self) -> str | None:
        """
        Return the title for the menu.

        Returns
        -------
        str | None
            The menu's title, or ``None`` if it doesn't have one set.
        """
        return self._title

    def get_actions(
        self,
    ) -> list[SpyderMenu | spyder.utils.qthelpers.SpyderAction]:
        """
        Return a parsed list of menu items/actions.

        Includes a :const:`MENU_SEPARATOR` between each defined menu section.

        Returns
        -------
        list[SpyderMenu | spyder.utils.qthelpers.SpyderAction]
            The list of menu items/actions for this menu.
        """
        actions = []
        for section in self._sections:
            for sec, action in self._actions:
                if sec == section:
                    actions.append(action)

            actions.append(MENU_SEPARATOR)
        return actions

    def get_sections(self) -> tuple[str, ...]:
        """
        Return a tuple of menu section names.

        Returns
        -------
        tuple[str, ...]
            An arbitrary-length tuple of menu section names.
        """
        return tuple(self._sections)

    # ---- Private API
    # -------------------------------------------------------------------------
    def _add_missing_actions(self) -> None:
        """
        Add actions that were not introduced to the menu because a `before`
        action they require is not part of it.
        """
        for before, actions in self._unintroduced_actions.items():
            for section, action in actions:
                self.add_action(
                    action, section=section, before=before, check_before=False
                )

        self._unintroduced_actions = {}

    def render(self, force: bool = False) -> None:
        """
        Create the menu prior to showing it. This takes into account sections
        and location of menus.

        Parameters
        ----------
        force: bool, optional
            Whether to force rendering the menu.
        """
        if self._dirty or force:
            self.clear()
            self._add_missing_actions()

            actions = self.get_actions()
            add_actions(self, actions)
            self._set_icons()

            self._dirty = False

    def _add_section(
        self, section: str, before_section: str | None = None
    ) -> None:
        """
        Add a new section to the list of sections in this menu.

        Parameters
        ----------
        section: str
            The name of the section to add.
        before_section: str | None, optional
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
                self._sections.insert(idx, after_section)

    def _set_icons(self) -> None:
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

    @classmethod
    def _generate_stylesheet(cls) -> qstylizer.style.StyleSheet:
        """Generate base stylesheet for menus."""
        css = qstylizer.style.StyleSheet()
        font = cls.get_font(SpyderFontType.Interface)

        # Add padding and border to follow modern standards
        css.QMenu.setValues(
            # Only add top and bottom padding so that menu separators can go
            # completely from the left to right border.
            paddingTop=f"{2 * AppStyle.MarginSize}px",
            paddingBottom=f"{2 * AppStyle.MarginSize}px",
            # This uses the same color as the separator
            border=f"1px solid {SpyderPalette.COLOR_BACKGROUND_6}",
        )

        # Set the right background color. This is the only way to do it!
        css["QWidget:disabled QMenu"].setValues(
            backgroundColor=SpyderPalette.COLOR_BACKGROUND_3,
        )

        # Add padding around separators to prevent that hovering on items hides
        # them.
        css["QMenu::separator"].setValues(
            # Only add top and bottom margins so that the separators can go
            # completely from the left to right border.
            margin=f"{2 * AppStyle.MarginSize}px 0px",
        )

        # Set menu item properties
        delta_top = 0 if (MAC or WIN) else 1
        delta_bottom = 0 if MAC else (2 if WIN else 1)
        css["QMenu::item"].setValues(
            height="1.1em" if MAC else ("1.35em" if WIN else "1.25em"),
            marginLeft=f"{cls.HORIZONTAL_MARGIN_FOR_ITEMS}px",
            marginRight=f"{cls.HORIZONTAL_MARGIN_FOR_ITEMS}px",
            paddingTop=f"{AppStyle.MarginSize + delta_top}px",
            paddingBottom=f"{AppStyle.MarginSize + delta_bottom}px",
            paddingLeft=f"{cls.HORIZONTAL_PADDING_FOR_ITEMS}px",
            paddingRight=f"{cls.HORIZONTAL_PADDING_FOR_ITEMS}px",
            fontFamily=font.family(),
            fontSize=f"{font.pointSize()}pt",
            backgroundColor="transparent",
        )

        # Set hover and pressed state of items
        for state in ["selected", "pressed"]:
            if state == "selected":
                bg_color = SpyderPalette.COLOR_BACKGROUND_4
            else:
                bg_color = SpyderPalette.COLOR_BACKGROUND_5

            css[f"QMenu::item:{state}"].setValues(
                backgroundColor=bg_color,
                borderRadius=SpyderPalette.SIZE_BORDER_RADIUS,
            )

        # Set disabled state of items
        for state in ["disabled", "selected:disabled"]:
            css[f"QMenu::item:{state}"].setValues(
                color=SpyderPalette.COLOR_DISABLED,
                backgroundColor="transparent",
            )

        return css

    def __str__(self) -> str:
        """
        Output this menu's class name and identifier as a string.

        Returns
        -------
        str
            The menu's class name and string identifier, in the format
            :file:``SpyderMenu({MENU_ID})``.
        """
        return f"SpyderMenu('{self.menu_id}')"

    def __repr__(self) -> str:
        """
        Output this menu's class name and identifier as a string.

        Returns
        -------
        str
            The menu's class name and string identifier, in the format
            :file:``SpyderMenu({MENU_ID})``.
        """
        return f"SpyderMenu('{self.menu_id}')"

    def _adjust_menu_position(self) -> None:
        """Menu position adjustment logic to follow custom style."""
        if not self._is_shown:
            # Reposition submenus vertically due to padding and border
            if self._reposition and self._is_submenu:
                self.move(
                    self.pos().x(),
                    # Current vertical pos - padding - border
                    self.pos().y() - 2 * AppStyle.MarginSize - 1,
                )

            self._is_shown = True

        # Reposition menus horizontally due to border
        if self.APP_MENU:
            delta_x = 0 if MAC else 3
        else:
            if QCursor().pos().x() - self.pos().x() < 40:
                # If the difference between the current cursor x position and
                # the menu one is small, it means the menu will be shown to the
                # right, so we need to move it in that direction.
                delta_x = 1
            else:
                # This happens when the menu is shown to the left.
                delta_x = -1

        self.move(self.pos().x() + delta_x, self.pos().y())

    # ---- Qt methods
    # -------------------------------------------------------------------------
    def showEvent(self, event: QShowEvent) -> None:
        """
        Perform adjustments when the menu is going to be shown.

        Parameters
        ----------
        event : QShowEvent
            The event object showing the menu.

        Returns
        -------
        None
        """
        # To prevent race conditions which can cause partially showing a menu
        # (as in spyder-ide/spyder#22266), we use a timer to queue the move
        # related events after the menu is shown.
        # For more info you can check:
        #  * https://forum.qt.io/topic/23381/showevent-not-working/3
        #  * https://stackoverflow.com/a/49351518
        QTimer.singleShot(0, self._adjust_menu_position)


class PluginMainWidgetOptionsMenu(SpyderMenu):
    """
    Options menu for :class:`~spyder.api.widgets.main_widget.PluginMainWidget`.
    """

    def render(self) -> None:
        """
        Render the menu's bottom section as expected.

        Returns
        -------
        None
        """
        if self._dirty:
            self.clear()
            self._add_missing_actions()

            bottom = OptionsMenuSections.Bottom
            actions = []
            for section in self._sections:
                for sec, action in self._actions:
                    if sec == section and sec != bottom:
                        actions.append(action)

                actions.append(MENU_SEPARATOR)

            # Add bottom actions
            for sec, action in self._actions:
                if sec == bottom:
                    actions.append(action)

            add_actions(self, actions)
            self._set_icons()

            self._dirty = False
