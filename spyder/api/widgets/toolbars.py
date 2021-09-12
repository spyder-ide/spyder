# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""
Spyder API toolbar widgets.
"""

# Standard library imports
import uuid
from collections import OrderedDict
from typing import Union, Optional, Tuple, List, Dict

# Third part imports
from qtpy.QtCore import QEvent, QObject, QSize, Qt
from qtpy.QtWidgets import QAction, QToolBar, QToolButton, QWidget

# Local imports
from spyder.api.exceptions import SpyderAPIError
from spyder.utils.qthelpers import SpyderAction
from spyder.utils.stylesheet import (
    APP_TOOLBAR_STYLESHEET, PANES_TOOLBAR_STYLESHEET)


# Generic type annotations
ToolbarItem = Union[SpyderAction, QWidget]
ToolbarItemEntry = Tuple[ToolbarItem, Optional[str], Optional[str],
                         Optional[str]]

# --- Constants
# ----------------------------------------------------------------------------
class ToolbarLocation:
    Top = Qt.TopToolBarArea
    Bottom = Qt.BottomToolBarArea


# --- Event filters
# ----------------------------------------------------------------------------
class ToolTipFilter(QObject):
    """
    Filter tool tip events on toolbuttons.
    """

    def eventFilter(self, obj, event):
        event_type = event.type()
        action = obj.defaultAction() if isinstance(obj, QToolButton) else None
        if event_type == QEvent.ToolTip and action is not None:
            if action.tip is None:
                return action.text_beside_icon

        return QObject.eventFilter(self, obj, event)


# --- Widgets
# ----------------------------------------------------------------------------
class SpyderToolbar(QToolBar):
    """
    Spyder Toolbar.

    This class provides toolbars with some predefined functionality.
    """

    def __init__(self, parent, title):
        super().__init__(parent=parent)
        self._section_items = OrderedDict()
        self._item_map = {}  # type: Dict[str, ToolbarItem]
        self._pending_items = {}  # type: Dict[str, List[ToolbarItemEntry]]
        self._title = title
        self._default_section = "default_section"

        self.setWindowTitle(title)

    def add_item(self, action_or_widget: ToolbarItem,
                 section: Optional[str] = None, before: Optional[str] = None,
                 before_section: Optional[str] = None, omit_id: bool = False):
        """
        Add action or widget item to given toolbar `section`.

        Parameters
        ----------
        item: SpyderAction or QWidget
            The item to add to the `toolbar`.
        toolbar_id: str or None
            The application toolbar unique string identifier.
        section: str or None
            The section id in which to insert the `item` on the `toolbar`.
        before: str or None
            Make the item appear before another given item.
        before_section: str or None
            Make the item defined section appear before another given section
            (must be already defined).
        omit_id: bool
            If True, then the toolbar will check if the item to add declares an
            id, False otherwise. This flag exists only for items added on
            Spyder 4 plugins. Default: False
        """
        item_id = None
        if (isinstance(action_or_widget, SpyderAction) or
                hasattr(action_or_widget, 'action_id')):
            item_id = action_or_widget.action_id
        elif hasattr(action_or_widget, 'ID'):
            item_id = action_or_widget.ID

        if not omit_id and item_id is None and action_or_widget is not None:
            raise SpyderAPIError(
                f'Item {action_or_widget} must declare an ID attribute.')

        if before is not None:
            if before not in self._item_map:
                before_pending_items = self._pending_items.get(before, [])
                before_pending_items.append(
                    (action_or_widget, section, before, before_section))
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
        if (before_section is not None and
                before_section in self._section_items):
            new_sections_keys = []
            for sec in self._section_items.keys():
                if sec == before_section:
                    new_sections_keys.append(section)
                if sec != section:
                    new_sections_keys.append(sec)
            self._section_items = OrderedDict(
                (section_key, self._section_items[section_key])
                for section_key in new_sections_keys)

        if item_id is not None:
            self._item_map[item_id] = action_or_widget
            if item_id in self._pending_items:
                item_pending = self._pending_items.pop(item_id)
                for item, section, before, before_section in item_pending:
                    self.add_item(item, section=section, before=before,
                                  before_section=before_section)

    def _render(self):
        """
        Create the toolbar taking into account sections and locations.

        This method is called once on widget setup.
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

        for (sec, item) in sec_items:
            if isinstance(item, QAction):
                add_method = super().addAction
            else:
                add_method = super().addWidget

            add_method(item)

            if isinstance(item, QAction):
                text_beside_icon = getattr(item, 'text_beside_icon', False)
                widget = self.widgetForAction(item)

                if text_beside_icon:
                    widget.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)

                if item.isCheckable():
                    widget.setCheckable(True)


class ApplicationToolbar(SpyderToolbar):
    """
    Spyder Main application Toolbar.
    """

    ID = None
    """
    Unique string toolbar identifier.

    This is used by Qt to be able to save and restore the state of widgets.
    """

    def __init__(self, parent, title):
        super().__init__(parent=parent, title=title)
        self.setStyleSheet(str(APP_TOOLBAR_STYLESHEET))


class MainWidgetToolbar(SpyderToolbar):
    """
    Spyder Widget toolbar class.

    A toolbar used in Spyder dockable plugins to add internal toolbars
    to their interface.
    """

    ID = None
    """
    Unique string toolbar identifier.
    """

    def __init__(self, parent=None, title=None):
        super().__init__(parent, title=title or '')
        self._icon_size = QSize(16, 16)

        # Setup
        self.setObjectName("main_widget_toolbar_{}".format(
            str(uuid.uuid4())[:8]))
        self.setFloatable(False)
        self.setMovable(False)
        self.setContextMenuPolicy(Qt.PreventContextMenu)
        self.setIconSize(self._icon_size)

        self._setup_style()
        self._filter = ToolTipFilter()

    def set_icon_size(self, icon_size):
        self._icon_size = icon_size
        self.setIconSize(icon_size)

    def _render(self):
        """
        Create the toolbar taking into account the sections and locations.

        This method is called once on widget setup.
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

        for (sec, item) in sec_items:
            if isinstance(item, QAction):
                add_method = super().addAction
            else:
                add_method = super().addWidget

            add_method(item)

            if isinstance(item, QAction):
                widget = self.widgetForAction(item)
                widget.installEventFilter(self._filter)

                text_beside_icon = getattr(item, 'text_beside_icon', False)
                if text_beside_icon:
                    widget.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)

                if item.isCheckable():
                    widget.setCheckable(True)

    def _setup_style(self):
        """
        Set the style of this toolbar with a stylesheet.
        """
        self.setStyleSheet(str(PANES_TOOLBAR_STYLESHEET))
