# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""
Dock widgets for plugins
"""

from qtpy.QtCore import QEvent, QObject, QPoint, Qt, QSize, Signal
from qtpy.QtGui import QCursor
from qtpy.QtWidgets import (QApplication, QDockWidget, QHBoxLayout, QStyle,
                            QTabBar, QToolButton, QWidget)

from spyder.utils import icon_manager as ima


class TabFilter(QObject):
    """Filter event attached to each DockWidget QTabBar."""
    def __init__(self, dock_tabbar, main):
        QObject.__init__(self)
        self.dock_tabbar = dock_tabbar
        self.main = main
        self.from_index = None

    def eventFilter(self, obj, event):
        """Filter mouse press events.

        Events that are captured and not propagated return True. Events that
        are not captured and are propagated return False.
        """
        event_type = event.type()
        if event_type == QEvent.MouseButtonPress:
            self.tab_pressed(event)
            return False
        return False

    def tab_pressed(self, event):
        """Method called when a tab from a QTabBar has been pressed."""
        self.from_index = self.dock_tabbar.tabAt(event.pos())
        self.dock_tabbar.setCurrentIndex(self.from_index)

        if event.button() == Qt.RightButton:
            if self.from_index == -1:
                self.show_nontab_menu(event)
            else:
                self.show_tab_menu(event)

    def show_tab_menu(self, event):
        """Show the context menu assigned to tabs."""
        self.show_nontab_menu(event)

    def show_nontab_menu(self, event):
        """Show the context menu assigned to nontabs section."""
        menu = self.main.createPopupMenu()
        menu.exec_(self.dock_tabbar.mapToGlobal(event.pos()))


class DockTitleBar(QWidget):
    """
    Custom title bar for our dock widgets.

    Inspired from
    https://stackoverflow.com/a/40894225/438386
    """

    def __init__(self, parent):
        super(DockTitleBar, self).__init__(parent)

        icon_size = QApplication.style().standardIcon(
            QStyle.SP_TitleBarNormalButton).actualSize(QSize(100, 100))
        button_size = icon_size + QSize(4, 4)

        self.drag_button = QToolButton(self)
        self.drag_button.setMaximumSize(button_size)
        self.drag_button.setAutoRaise(True)
        self.drag_button.setIcon(ima.icon('drag-horizontal'))

        self.close_button = QToolButton(self)
        self.close_button.setMaximumSize(button_size)
        self.close_button.setAutoRaise(True)
        self.close_button.setIcon(QApplication.style().standardIcon(
            QStyle.SP_DockWidgetCloseButton))
        self.close_button.setCursor(Qt.ArrowCursor)
        self.close_button.clicked.connect(self.close_parent)

        hlayout = QHBoxLayout(self)
        hlayout.setSpacing(1)
        hlayout.addStretch()
        hlayout.addWidget(self.drag_button)
        hlayout.addStretch()
        hlayout.addSpacing(5)
        hlayout.addWidget(self.close_button)

        # To signal that dock widgets can be dragged from here
        self.setCursor(Qt.OpenHandCursor)

    def close_parent(self):
        """Close dockwidget."""
        self.parent().toggleViewAction().setChecked(False)
        self.parent().hide()

    def mouseReleaseEvent(self, event):
        self.setCursor(Qt.OpenHandCursor)
        QWidget.mouseReleaseEvent(self, event)

    def mousePressEvent(self, event):
        self.setCursor(Qt.ClosedHandCursor)
        QWidget.mousePressEvent(self, event)

    def mouseMoveEvent(self, event):
        QWidget.mouseMoveEvent(self, event)
        self.setCursor(Qt.OpenHandCursor)


class SpyderDockWidget(QDockWidget):
    """Subclass to override needed methods"""
    sig_plugin_closed = Signal()

    def __init__(self, title, parent):
        super(SpyderDockWidget, self).__init__(title, parent)

        # Our custom title bar
        self.titlebar = DockTitleBar(self)

        # Needed for the installation of the event filter
        self.title = title
        self.main = parent
        self.dock_tabbar = None

        # To track dockwidget changes the filter is installed when dockwidget
        # visibility changes. This installs the filter on startup and also
        # on dockwidgets that are undocked and then docked to a new location.
        self.visibilityChanged.connect(self.install_tab_event_filter)

    def closeEvent(self, event):
        """
        Reimplement Qt method to send a signal on close so that "Panes" main
        window menu can be updated correctly
        """
        self.sig_plugin_closed.emit()

    def install_tab_event_filter(self, value):
        """
        Install an event filter to capture mouse events in the tabs of a
        QTabBar holding tabified dockwidgets.
        """
        dock_tabbar = None
        tabbars = self.main.findChildren(QTabBar)
        for tabbar in tabbars:
            for tab in range(tabbar.count()):
                title = tabbar.tabText(tab)
                if title == self.title:
                    dock_tabbar = tabbar
                    break
        if dock_tabbar is not None:
            self.dock_tabbar = dock_tabbar
            # Install filter only once per QTabBar
            if getattr(self.dock_tabbar, 'filter', None) is None:
                self.dock_tabbar.filter = TabFilter(self.dock_tabbar,
                                                    self.main)
                self.dock_tabbar.installEventFilter(self.dock_tabbar.filter)

    def set_title_bar(self):
        """Set custom title bar."""
        self.setTitleBarWidget(self.titlebar)
