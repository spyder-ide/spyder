# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""
Dock widgets for plugins
"""

from qtpy.QtCore import QEvent, QObject, Qt, QSize, Signal
from qtpy.QtWidgets import (QApplication, QDockWidget, QHBoxLayout,
                            QSizePolicy, QStyle, QTabBar, QToolButton,
                            QWidget)

from spyder.config.gui import is_dark_interface
from spyder.utils import icon_manager as ima


# =============================================================================
# Tab filter
# =============================================================================
class TabFilter(QObject):
    """Filter event attached to each DockWidget QTabBar."""
    def __init__(self, dock_tabbar, main):
        QObject.__init__(self)
        self.dock_tabbar = dock_tabbar
        self.main = main
        self.from_index = None

        # Center dockwidget tabs to differentiate them from plugin tabs.
        # See spyder-ide/spyder#9763
        self.dock_tabbar.setStyleSheet("QTabBar {alignment: center;}")

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


# =============================================================================
# Title bar
# =============================================================================
class DragButton(QToolButton):
    """
    Drag button for the title bar.

    This button pass all its mouse events to its parent.
    """

    def __init__(self, parent, button_size):
        super(QToolButton, self).__init__(parent)
        self.parent = parent

        # Style
        self.setMaximumSize(button_size)
        self.setAutoRaise(True)
        self.setIcon(ima.icon('drag-horizontal'))
        if is_dark_interface():
            self.setStyleSheet(
                "QToolButton {"
                "border-radius: 0px;"
                "border: 0px;"
                "background-color: #32414B;}")
        else:
            self.setStyleSheet("QToolButton {border: 0px;}")

    def mouseReleaseEvent(self, event):
        self.parent.mouseReleaseEvent(event)

    def mousePressEvent(self, event):
        self.parent.mousePressEvent(event)

    def mouseMoveEvent(self, event):
        self.parent.mouseMoveEvent(event)


class CloseButton(QToolButton):
    """Close button for the title bar."""

    def __init__(self, parent, button_size):
        super(QToolButton, self).__init__(parent)

        # Style
        self.setMaximumSize(button_size)
        self.setAutoRaise(True)
        self.setCursor(Qt.ArrowCursor)
        if is_dark_interface():
            self.setStyleSheet(
                "QToolButton {"
                "border-radius: 0px;"
                "border: 0px;"
                "image: url(:/qss_icons/rc/close.png);"
                "background-color: #32414B;}"
                "QToolButton:hover {"
                "image: url(:/qss_icons/rc/close-hover.png);}")
        else:
            self.setIcon(QApplication.style().standardIcon(
                QStyle.SP_DockWidgetCloseButton))


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
        button_size = icon_size + QSize(8, 8)

        left_spacer = QWidget(self)
        left_spacer.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum)
        if is_dark_interface():
            left_spacer.setStyleSheet("background-color: #32414B")

        drag_button = DragButton(self, button_size)

        right_spacer = QWidget(self)
        right_spacer.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum)
        if is_dark_interface():
            right_spacer.setStyleSheet("background-color: #32414B")

        close_button = CloseButton(self, button_size)
        close_button.clicked.connect(parent.sig_plugin_closed.emit)

        hlayout = QHBoxLayout(self)
        hlayout.setSpacing(0)
        hlayout.setContentsMargins(0, 0, 0, 0)
        hlayout.addWidget(left_spacer)
        hlayout.addWidget(drag_button)
        hlayout.addWidget(right_spacer)
        hlayout.addWidget(close_button)

        # To signal that dock widgets can be dragged from here
        self.setCursor(Qt.SizeAllCursor)

    def mouseReleaseEvent(self, event):
        self.setCursor(Qt.SizeAllCursor)
        QWidget.mouseReleaseEvent(self, event)

    def mousePressEvent(self, event):
        self.setCursor(Qt.ClosedHandCursor)
        QWidget.mousePressEvent(self, event)

    def mouseMoveEvent(self, event):
        QWidget.mouseMoveEvent(self, event)
        self.setCursor(Qt.SizeAllCursor)


class SpyderDockWidget(QDockWidget):
    """Subclass to override needed methods"""
    sig_plugin_closed = Signal()

    def __init__(self, title, parent):
        super(SpyderDockWidget, self).__init__(title, parent)

        # Set our custom title bar
        self.titlebar = DockTitleBar(self)
        self.set_title_bar()

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
