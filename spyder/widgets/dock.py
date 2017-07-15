# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""
Dock widgets for plugins
"""

from qtpy.QtCore import QEvent, QObject, QPoint, Qt, Signal
from qtpy.QtGui import QCursor
from qtpy.QtWidgets import QApplication, QDockWidget, QTabBar


class TabFilter(QObject):
    """
    Filter event attached to each QTabBar that holds 2 or more dockwidgets in
    charge of handling tab rearangement.

    This filter also holds the methods needed for the detection of a drag and
    the movement of tabs.
    """
    def __init__(self, dock_tabbar, main):
        QObject.__init__(self)
        self.dock_tabbar = dock_tabbar
        self.main = main
        self.moving = False
        self.from_index = None
        self.to_index = None

    # Helper methods
    def _get_plugin(self, index):
        """Get plugin reference based on tab index."""
        for plugin in self.main.widgetlist:
            tab_text = self.dock_tabbar.tabText(index).replace('&', '')
            if plugin.get_plugin_title() == tab_text:
                return plugin

    def _get_plugins(self):
        """
        Get a list of all plugin references in the QTabBar to which this
        event filter is attached.
        """
        plugins = []
        for index in range(self.dock_tabbar.count()):
            plugin = self._get_plugin(index)
            plugins.append(plugin)
        return plugins

    def _fix_cursor(self, from_index, to_index):
        """Fix mouse cursor position to adjust for different tab sizes."""
        # The direction is +1 (moving to the right) or -1 (moving to the left)
        direction = abs(to_index - from_index)/(to_index - from_index)

        tab_width = self.dock_tabbar.tabRect(to_index).width()
        tab_x_min = self.dock_tabbar.tabRect(to_index).x()
        tab_x_max = tab_x_min + tab_width
        previous_width = self.dock_tabbar.tabRect(to_index - direction).width()

        delta = previous_width - tab_width
        if delta > 0:
            delta = delta * direction
        else:
            delta = 0
        cursor = QCursor()
        pos = self.dock_tabbar.mapFromGlobal(cursor.pos())
        x, y = pos.x(), pos.y()
        if x < tab_x_min or x > tab_x_max:
            new_pos = self.dock_tabbar.mapToGlobal(QPoint(x + delta, y))
            cursor.setPos(new_pos)

    def eventFilter(self,  obj,  event):
        """Filter mouse press events.

        Events that are captured and not propagated return True. Events that
        are not captured and are propagated return False.
        """
        event_type = event.type()
        if event_type == QEvent.MouseButtonPress:
            self.tab_pressed(event)
            return False
        if event_type == QEvent.MouseMove:
            self.tab_moved(event)
            return True
        if event_type == QEvent.MouseButtonRelease:
            self.tab_released(event)
            return True
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

    def tab_moved(self, event):
        """Method called when a tab from a QTabBar has been moved."""
        # If the left button isn't pressed anymore then return
        if not event.buttons() & Qt.LeftButton:
            self.to_index = None
            return

        self.to_index = self.dock_tabbar.tabAt(event.pos())

        if not self.moving and self.from_index != -1 and self.to_index != -1:
            QApplication.setOverrideCursor(Qt.ClosedHandCursor)
            self.moving = True

        if self.to_index == -1:
            self.to_index = self.from_index

        from_index, to_index = self.from_index, self.to_index
        if from_index != to_index and from_index != -1 and to_index != -1:
            self.move_tab(from_index, to_index)
            self._fix_cursor(from_index, to_index)
            self.from_index = to_index

    def tab_released(self, event):
        """Method called when a tab from a QTabBar has been released."""
        QApplication.restoreOverrideCursor()
        self.moving = False

    def move_tab(self, from_index, to_index):
        """Move a tab from a given index to a given index position."""
        plugins = self._get_plugins()
        from_plugin = self._get_plugin(from_index)
        to_plugin = self._get_plugin(to_index)

        from_idx = plugins.index(from_plugin)
        to_idx = plugins.index(to_plugin)

        plugins[from_idx], plugins[to_idx] = plugins[to_idx], plugins[from_idx]

        for i in range(len(plugins)-1):
            self.main.tabify_plugins(plugins[i], plugins[i+1])
        from_plugin.dockwidget.raise_()

    def show_tab_menu(self, event):
        """Show the context menu assigned to tabs."""
        self.show_nontab_menu(event)

    def show_nontab_menu(self, event):
        """Show the context menu assigned to nontabs section."""
        menu = self.main.createPopupMenu()
        menu.exec_(self.dock_tabbar.mapToGlobal(event.pos()))


class SpyderDockWidget(QDockWidget):
    """Subclass to override needed methods"""
    plugin_closed = Signal(object)

    def __init__(self, title, parent):
        super(SpyderDockWidget, self).__init__(title)

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
        self.plugin_closed.emit(event)

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
