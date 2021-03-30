# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""
Spyder API toolbar widgets.
"""

# Standard library imports
import textwrap
import uuid
from collections import OrderedDict

# Third part imports
from qtpy.QtCore import QEvent, QObject, QSize, Qt
from qtpy.QtWidgets import QAction, QToolBar, QToolButton

# Local imports
from spyder.utils.stylesheet import (
    APP_TOOLBAR_STYLESHEET, PANES_TOOLBAR_STYLESHEET)


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
        self._title = title
        self._default_section = "default_section"

        self.setWindowTitle(title)

    def add_item(self, action_or_widget, section=None, before=None,
                 before_section=None):
        """
        Add action or widget item to given toolbar `section`.
        """
        if section is None:
            section = self._default_section

        action_or_widget._section = section
        if section is None and before is not None:
            action_or_widget._section = before._section
            section = before._section

        if section is not None and section not in self._section_items:
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
