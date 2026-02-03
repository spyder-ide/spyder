# -----------------------------------------------------------------------------
# Copyright (c) 2020- Spyder Project Contributors
#
# Released under the terms of the MIT License
# (see LICENSE.txt in the project root directory for details)
# -----------------------------------------------------------------------------

"""
Spyder API toolbar widgets.
"""

from __future__ import annotations

# Standard library imports
import os
import sys
import uuid
from collections import OrderedDict
from typing import Literal, Union, TYPE_CHECKING

if sys.version_info < (3, 10):
    from typing_extensions import TypeAlias
else:
    from typing import TypeAlias  # noqa: ICN003

# Third part imports
from qtpy.QtCore import QEvent, QObject, QSize, Qt, Signal
from qtpy.QtWidgets import (
    QAction,
    QProxyStyle,
    QStyle,
    QToolBar,
    QToolButton,
    QWidget,
)

# Local imports
import spyder.utils.qthelpers  # For fully-qualified SpyderAction in type alias
from spyder.api.exceptions import SpyderAPIError
from spyder.api.translations import _
from spyder.api.widgets.menus import SpyderMenu, SpyderMenuProxyStyle
from spyder.utils.icon_manager import ima
from spyder.utils.qthelpers import SpyderAction
from spyder.utils.stylesheet import (
    APP_TOOLBAR_STYLESHEET,
    PANES_TOOLBAR_STYLESHEET,
)

if TYPE_CHECKING:
    from qtpy.QtWidgets import QMainWindow, QStyleOption


# Generic type aliases
ToolbarItem: TypeAlias = Union[spyder.utils.qthelpers.SpyderAction, QWidget]
"""Type alias for the set of supported objects that can be toolbar items."""

ToolbarItemEntry: TypeAlias = tuple[
    ToolbarItem, Union[str, None], Union[str, None], Union[str, None]
]
"""Type alias for the full tuple entry in the list of toolbar items."""


# ---- Constants
# ----------------------------------------------------------------------------
class ToolbarLocation:
    """Pseudo-enum listing possible locations for a toolbar."""

    Top: Qt.ToolBarArea = Qt.TopToolBarArea
    """Toolbar at the top of the layout."""

    Bottom: Qt.ToolBarArea = Qt.BottomToolBarArea
    """Toolbar at the bottom of the layout."""


# ---- Event filters
# ----------------------------------------------------------------------------
class _ToolTipFilter(QObject):
    """
    Filter tooltip events on toolbar buttons.
    """

    def eventFilter(self, obj: QObject, event: QEvent) -> bool:
        """
        Filter tooltip events on toolbar buttons.

        Parameters
        ----------
        obj : QObject
            The object receiving the event.
        event : QEvent
            The event object.

        Returns
        -------
        bool
            ``True`` the event should be filtered out, ``False`` otherwise.
        """
        event_type = event.type()
        action = obj.defaultAction() if isinstance(obj, QToolButton) else None
        if event_type == QEvent.ToolTip and action is not None:
            if action.tip is None:
                return action.text_beside_icon

        return QObject.eventFilter(self, obj, event)


# ---- Styles
# ----------------------------------------------------------------------------
class ToolbarStyle(QProxyStyle):
    """Proxy style class to control the style of Spyder toolbars.

    .. deprecated:: 6.2

        This class will be renamed to the private :class:`!_ToolbarStyle`
        in Spyder 6.2, while the current public name will become an alias
        raising a :exc:`DeprecationWarning` on use, and removed in 7.0.

        It was never intended to be used directly by plugins, and its
        functionality is automatically inherited by using the appropriate
        :class:`ApplicationToolbar` and :class:`MainWidgetToolbar` classes.
    """

    TYPE: Literal["Application"] | Literal["MainWidget"] | None = None
    """
    The toolbar type; must be either "Application" or "MainWidget".
    """

    def pixelMetric(
        self, pm: QStyle.PixelMetric, option: QStyleOption, widget: QWidget
    ) -> int:
        """
        Adjust size of toolbar extension button (in pixels).

        From `Stack Overflow <https://stackoverflow.com/a/27042352/438386>`__.

        This is a callback intended to be called internally by Qt.

        Parameters
        ----------
        pm : QStyle.PixelMetric
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

        Raises
        ------
        SpyderAPIError
            If :attr:`TYPE` is not ``"Application"`` or ``"MainWidget"``,
            as then this style would do nothing.
        """
        # Important: These values need to be updated in case we change the size
        # of our toolbar buttons in utils/stylesheet.py. That's because Qt only
        # allow to set them in pixels here, not em's.
        if pm == QStyle.PM_ToolBarExtensionExtent:
            if self.TYPE == "Application":
                if os.name == "nt":
                    return 40
                elif sys.platform == "darwin":
                    return 54
                else:
                    return 57
            elif self.TYPE == "MainWidget":
                if os.name == "nt":
                    return 36
                elif sys.platform == "darwin":
                    return 42
                else:
                    return 44
            else:
                raise SpyderAPIError(
                    "Toolbar style must be 'Application' or 'MainWidget', not"
                    f" {self.TYPE!r}"
                )
        return super().pixelMetric(pm, option, widget)


# ---- Toolbars
# ----------------------------------------------------------------------------
class SpyderToolbar(QToolBar):
    """
    This class provides toolbars with some predefined functionality.

    .. caution::

        This class isn't intended to be used directly; use its subclasses
        :class:`ApplicationToolbar` and :class:`MainWidgetToolbar` instead.
    """

    sig_is_rendered: Signal = Signal()
    """
    Signal to let other objects know that the toolbar is now rendered.
    """

    def __init__(self, parent: QWidget | None, title: str) -> None:
        """
        Create a new toolbar object.

        Parameters
        ----------
        parent : QWidget | None
            The parent widget of this one, or ``None``.
        title : str
            The localized title of this toolbar, to display in the UI.

        Returns
        -------
        None
        """
        super().__init__(parent=parent)

        # Attributes
        self._title = title
        self._section_items = OrderedDict()
        self._item_map: dict[str, ToolbarItem] = {}
        self._pending_items: dict[str, list[ToolbarItemEntry]] = {}
        self._default_section = "default_section"
        self._filter = None

        self.setWindowTitle(title)

        # Set attributes for extension button.
        # From https://stackoverflow.com/a/55412455/438386
        ext_button = self.findChild(QToolButton, "qt_toolbar_ext_button")
        ext_button.setIcon(ima.icon("toolbar_ext_button"))
        ext_button.setToolTip(_("More"))

        # Set style for extension button menu (not all extension buttons have
        # it).
        if ext_button.menu():
            ext_button.menu().setStyleSheet(
                SpyderMenu._generate_stylesheet().toString()
            )

            ext_button_menu_style = SpyderMenuProxyStyle(None)
            ext_button_menu_style.setParent(self)
            ext_button.menu().setStyle(ext_button_menu_style)

    def add_item(
        self,
        action_or_widget: ToolbarItem,
        section: str | None = None,
        before: str | None = None,
        before_section: str | None = None,
        omit_id: bool = False,
    ) -> None:
        """
        Add action or widget item to the given toolbar ``section``.

        Parameters
        ----------
        action_or_widget: ToolbarItem
            The item to add to the toolbar.
        section: str | None, optional
            The section id in which to insert the ``action_or_widget``,
            or ``None`` (default) for no section.
        before: str | None, optional
            Make the ``action_or_widget`` appear before the action with the
            identifier ``before``. If ``None`` (default), add it to the end.
            If ``before`` is not ``None``, ``before_section`` will be ignored.
        before_section : str | None, optional
            Make the ``section`` appear prior to ``before_section``.
            If ``None`` (the default), add the section to the end.
            If you provide a ``before`` action, the new action will be placed
            before this one, so the section option will be ignored, since the
            action will now be placed in the same section as the ``before``
            action.
        omit_id: bool, optional
            If ``False``, the default, then the toolbar will check if
            ``action.action_id`` exists and is set to a string, and raise
            an :exc:`~spyder.api.exceptions.SpyderAPIError` if either is not
            the case. If ``True``, it will add the ``action_or_widget`` anyway.

        Returns
        -------
        None

        Raises
        ------
        SpyderAPIError
            If ``omit_id`` is ``False`` (the default) and
            ``action_or_widget.action_id`` does not exist or is not set to
            a string.
        """
        item_id = None
        if isinstance(action_or_widget, SpyderAction) or hasattr(
            action_or_widget, "action_id"
        ):
            item_id = action_or_widget.action_id
        elif hasattr(action_or_widget, "ID"):
            item_id = action_or_widget.ID
        if not omit_id and item_id is None and action_or_widget is not None:
            raise SpyderAPIError(
                f"Item {action_or_widget} must declare an ID attribute."
            )

        if before is not None:
            if before not in self._item_map:
                before_pending_items = self._pending_items.get(before, [])
                before_pending_items.append(
                    (action_or_widget, section, before, before_section)
                )
                self._pending_items[before] = before_pending_items
                return
            else:
                before = self._item_map[before]

        if section is None:
            section = self._default_section

        action_or_widget._section = section

        if before is not None:
            if section == self._default_section:
                action_or_widget._section = before._section
                section = before._section

        if section not in self._section_items:
            self._section_items[section] = [action_or_widget]
        else:
            if before is not None:
                new_actions_or_widgets = []
                for act_or_wid in self._section_items[section]:
                    if act_or_wid == before:
                        new_actions_or_widgets.append(action_or_widget)
                    new_actions_or_widgets.append(act_or_wid)

                self._section_items[section] = new_actions_or_widgets
            else:
                self._section_items[section].append(action_or_widget)
        if (
            before_section is not None
            and before_section in self._section_items
        ):
            new_sections_keys = []
            for sec in self._section_items.keys():
                if sec == before_section:
                    new_sections_keys.append(section)
                if sec != section:
                    new_sections_keys.append(sec)
            self._section_items = OrderedDict(
                (section_key, self._section_items[section_key])
                for section_key in new_sections_keys
            )

        if item_id is not None:
            self._item_map[item_id] = action_or_widget
            if item_id in self._pending_items:
                item_pending = self._pending_items.pop(item_id)
                for item, section, before, before_section in item_pending:
                    self.add_item(
                        item,
                        section=section,
                        before=before,
                        before_section=before_section,
                    )

    def remove_item(self, item_id: str) -> None:
        """
        Remove the toolbar item with the given string identifier.

        Parameters
        ----------
        item_id : str
            The string identifier of the toolbar item to remove.

        Returns
        -------
        None
        """
        try:
            item = self._item_map.pop(item_id)
            for section in list(self._section_items.keys()):
                section_items = self._section_items[section]
                if item in section_items:
                    section_items.remove(item)
                if len(section_items) == 0:
                    self._section_items.pop(section)
            self.clear()
            self.render()
        except KeyError:
            pass

    def render(self) -> None:
        """
        Render the toolbar taking into account sections and locations.

        Returns
        -------
        None
        """
        sec_items = []
        for sec, items in self._section_items.items():
            for item in items:
                sec_items.append([sec, item])

            sep = QAction(self)
            sep.setSeparator(True)
            sec_items.append((None, sep))

        if sec_items:
            sec_items.pop()

        for sec, item in sec_items:
            if isinstance(item, QAction):
                add_method = super().addAction
            else:
                add_method = super().addWidget

            add_method(item)

            if isinstance(item, QAction):
                widget = self.widgetForAction(item)

                if self._filter is not None:
                    widget.installEventFilter(self._filter)

                text_beside_icon = getattr(item, "text_beside_icon", False)
                if text_beside_icon:
                    widget.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)

                if item.isCheckable():
                    widget.setCheckable(True)

        self.sig_is_rendered.emit()


class ApplicationToolbar(SpyderToolbar):
    """
    A Spyder main application toolbar.

    These toolbars are placed above all Spyder dockable plugins in the
    interface.
    """

    ID: str | None = None
    """
    Unique string toolbar identifier.

    This is used by Qt to be able to save and restore the state of widgets.
    """

    def __init__(
        self, parent: QMainWindow, toolbar_id: str, title: str
    ) -> None:
        """
        Create a main Spyder application toolbar.

        Parameters
        ----------
        parent : QMainWindow
            The parent main window of this toolbar.
        toolbar_id : str
            The unique string identifier of this toolbar.
        title : str
            The localized name of this toolbar, displayed in the interface.

        Returns
        -------
        None
        """
        super().__init__(parent=parent, title=title)
        self.ID = toolbar_id

        self._style = ToolbarStyle(None)
        self._style.TYPE = "Application"
        self._style.setParent(self)
        self.setStyle(self._style)

        self.setStyleSheet(str(APP_TOOLBAR_STYLESHEET))

    def __str__(self) -> str:
        """
        Output this toolbar's class name and identifier as a string.

        Returns
        -------
        str
            The toolbar's class name and string identifier, in the format
            :file:``ApplicationToolbar({TOOLBAR_ID})``.
        """
        return f"ApplicationToolbar('{self.ID}')"

    def __repr__(self) -> str:
        """
        Output this toolbar's class name and identifier as a string.

        Returns
        -------
        str
            The menu's class name and string identifier, in the format
            :file:``ApplicationToolbar({TOOLBAR_ID})``.
        """
        return f"ApplicationToolbar('{self.ID}')"


class MainWidgetToolbar(SpyderToolbar):
    """
    A Spyder dockable plugin toolbar.

   This is used by dockable plugins to have their own toolbars.
    """

    ID: str | None = None
    """
    Unique string toolbar identifier.
    """

    def __init__(
        self, parent: QWidget | None = None, title: str | None = None
    ) -> None:
        """
        Create a new toolbar.

        Parameters
        ----------
        parent : QWidget | None, optional
            The parent widget of this one, or ``None`` (default).
        title : str | None, optional
            The localized title of this toolbar, or ``None`` (default) for
            no title.

        Returns
        -------
        None
        """
        super().__init__(parent, title=title or "")
        self._icon_size = QSize(16, 16)

        # Setup
        self.setObjectName(
            "main_widget_toolbar_{}".format(str(uuid.uuid4())[:8])
        )
        self.setFloatable(False)
        self.setMovable(False)
        self.setContextMenuPolicy(Qt.PreventContextMenu)
        self.setIconSize(self._icon_size)

        self._style = ToolbarStyle(None)
        self._style.TYPE = "MainWidget"
        self._style.setParent(self)
        self.setStyle(self._style)

        self.setStyleSheet(str(PANES_TOOLBAR_STYLESHEET))

        self._filter = _ToolTipFilter()

    def set_icon_size(self, icon_size: QSize) -> None:
        """
        Set the icon size for this toolbar.

        Parameters
        ----------
        icon_size : QSize
            The icon size to set.

        Returns
        -------
        None
        """
        self._icon_size = icon_size
        self.setIconSize(icon_size)
