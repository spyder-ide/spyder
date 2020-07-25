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

    def __init__(self, parent=None, title=None, location=ToolBarLocation.Top,
                 corner_widget=None):
        super().__init__(parent, title=title or '')
        self._set_corner_widget(corner_widget)
        self._icon_size = QSize(16, 16)

        # Setup
        self.setObjectName("main_widget_toolbar_{}".format(
            str(uuid.uuid4())[:8]))
        self.setFloatable(False)
        self.setMovable(False)
        self.setAllowedAreas(location)
        self.setContextMenuPolicy(Qt.PreventContextMenu)
        self.setIconSize(self._icon_size)
        self._setup_style()
        self._filter = ToolTipFilter()

    def set_icon_size(self, icon_size):
        self._icon_size = icon_size
        self.setIconSize(icon_size)

    def addWidget(self, widget):
        """
        Override Qt method.

        Take into account the existence of a corner widget when adding a new
        widget to this toolbar.
        """
        if self._corner_widget is not None:
            super().insertWidget(self._corner_separator_action, widget)
        else:
            super().addWidget(widget)

    def create_toolbar_stretcher(self):
        """
        Create a stretcher widget to be used in a Qt toolbar.
        """
        stretcher = QWidget()
        stretcher.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        return stretcher

    def _set_corner_widget(self, corner_widget):
        """
        Add the given corner widget to this toolbar.

        A stretcher widget is added before the corner widget so that
        its position is forced to the right side of the toolbar when the
        toolbar is resized.
        """
        self._corner_widget = corner_widget
        if corner_widget is not None:
            stretcher = self.create_toolbar_stretcher()
            self._corner_separator = super().addWidget(stretcher)
            super().addWidget(self._corner_widget)
        else:
            self._corner_separator = None

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
                insert_method = super().insertAction
            else:
                add_method = super().addWidget
                insert_method = super().insertWidget

            if self._corner_widget is not None:
                insert_method(self._corner_separator, item)
            else:
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
