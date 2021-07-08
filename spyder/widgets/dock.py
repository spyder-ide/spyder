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

from spyder.utils.icon_manager import ima
from spyder.utils.palette import QStylePalette


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
        self.dock_tabbar.setStyleSheet(self._tabbar_stylesheet)

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

        try:
            if event.button() == Qt.RightButton:
                if self.from_index == -1:
                    self.show_nontab_menu(event)
                else:
                    self.show_tab_menu(event)
        except AttributeError:
            # Needed to avoid an error when generating the
            # context menu on top of the tab.
            # See spyder-ide/spyder#11226
            pass

    def show_tab_menu(self, event):
        """Show the context menu assigned to tabs."""
        self.show_nontab_menu(event)

    def show_nontab_menu(self, event):
        """Show the context menu assigned to nontabs section."""
        menu = self.main.createPopupMenu()
        menu.exec_(self.dock_tabbar.mapToGlobal(event.pos()))

    @property
    def _tabbar_stylesheet(self):
        # - Center tabs to differentiate them from plugin ones.
        #   See spyder-ide/spyder#9763
        # - Also add a border below selected tabs so they don't touch
        #   either the window separator or the status bar.
        stylesheet = """
            QTabBar {
                alignment: center;
            }

            QTabBar::tab:bottom:selected {
                border-bottom: 2px solid %s;
            }
        """ % QStylePalette.COLOR_BACKGROUND_1

        return stylesheet


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
        self.setStyleSheet((
            "QToolButton {{"
            "border-radius: 0px;"
            "border: 0px;"
            "background-color: {color};}}").format(
                color=QStylePalette.COLOR_BACKGROUND_3))

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
        self.setStyleSheet((
            "QToolButton {{"
            "border-radius: 0px;"
            "border: 0px;"
            "image: url(:/qss_icons/rc/close.png);"
            "background-color: {color};}}"
            "QToolButton:hover {{"
            "image: url(:/qss_icons/rc/close-hover.png);}}").format(
                color=QStylePalette.COLOR_BACKGROUND_3))


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
        left_spacer.setStyleSheet(
            f"background-color: {QStylePalette.COLOR_BACKGROUND_3}")

        drag_button = DragButton(self, button_size)

        right_spacer = QWidget(self)
        right_spacer.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum)
        right_spacer.setStyleSheet(
            f"background-color: {QStylePalette.COLOR_BACKGROUND_3}")

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

    # Attributes
    ALLOWED_AREAS = Qt.AllDockWidgetAreas
    LOCATION = Qt.LeftDockWidgetArea
    FEATURES = QDockWidget.DockWidgetClosable | QDockWidget.DockWidgetMovable

    # Signals
    sig_plugin_closed = Signal()

    def __init__(self, title, parent):
        super(SpyderDockWidget, self).__init__(title, parent)

        self.title = title

        # Widgets
        self.main = parent
        self.empty_titlebar = QWidget(self)
        self.titlebar = DockTitleBar(self)
        self.dock_tabbar = None  # Needed for event filter

        # Layout
        # Prevent message on internal console
        # See: https://bugreports.qt.io/browse/QTBUG-42986
        layout = QHBoxLayout(self.empty_titlebar)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        self.empty_titlebar.setLayout(layout)
        self.empty_titlebar.setMinimumSize(0, 0)
        self.empty_titlebar.setMaximumSize(0, 0)

        # Setup
        self.set_title_bar()

        # Signals
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

    def remove_title_bar(self):
        """Set empty qwidget on title bar."""
        self.setTitleBarWidget(self.empty_titlebar)

    def set_title_bar(self):
        """Set custom title bar."""
        self.setTitleBarWidget(self.titlebar)
