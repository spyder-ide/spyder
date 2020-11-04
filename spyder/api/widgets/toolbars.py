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
from qtpy.QtWidgets import (QAction, QSizePolicy, QToolBar, QToolButton,
                            QWidget)

# Local imports
from spyder.config.gui import is_dark_interface


# --- Constants
# ----------------------------------------------------------------------------
class ApplicationToolBars:
    File = 'file_toolbar'
    Run = 'run_toolbar'
    Debug = 'defbug_toolbar'
    Main = 'main_toolbar'
    Search = 'search_toolbar'
    Edit = 'edit_toolbar'
    Source = 'source_toolbar'
    WorkingDirectory = 'working_directory_toolbar'


class ToolBarLocation:
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
            return action.text_beside_icon

        return QObject.eventFilter(self, obj, event)


# --- Widgets
# ----------------------------------------------------------------------------
class SpyderToolBar(QToolBar):
    """
    Spyder ToolBar.

    This class provides toolbars with some predefined functionality.
    """

    def __init__(self, parent, title):
        super().__init__(parent=parent)
        self._section_items = OrderedDict()
        self._title = title

        self.setWindowTitle(title)

    def add_item(self, action_or_widget, section=None, before=None):
        """
        Add action or widget item to given toolbar `section`. 
        """
        if section is not None:
            action_or_widget._section = section

        if section is None and before is not None:
            action_or_widget._section = before._section
            section = before._section

        if section is not None and section not in self._section_items:
            self._section_items[section] = [action_or_widget]
        else:
            self._section_items[section].append(action_or_widget)

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


class ApplicationToolBar(SpyderToolBar):
    """
    Spyder Main application ToolBar.
    """


class MainWidgetToolbar(SpyderToolBar):
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
        if is_dark_interface():
            stylesheet = r"""
                QToolBar QToolButton:!hover:!pressed {
                    border-color: transparent;
                }
                QToolBar {
                    border: 0px;
                    background: rgb(25, 35, 45);
                }
                QToolButton {
                    background-color: transparent;
                }
                QToolButton:checked {
                    background-color: rgb(49, 64, 75);
                }
            """
        else:
            stylesheet = r"QToolBar {border: 0px;}"

        self.setStyleSheet(textwrap.dedent(stylesheet))
