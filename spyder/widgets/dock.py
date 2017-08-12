# -*- coding: utf-8 -*-
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""Dock widgets for plugins."""

# Standard library imports
import sys

# Third party imports
from qtpy.QtCore import QSize, Qt, Signal
from qtpy.QtWidgets import (QDockWidget, QFrame, QTabBar, QHBoxLayout,
                            QToolButton, QVBoxLayout, QMenu)

# Local imports
from spyder.utils.qthelpers import add_actions, create_action
import spyder.utils.icon_manager as ima


class SpyderDockWidget(QDockWidget):
    """
    Dockwidget that overrides methods and creates curstom title bar.

    When dockwidgets are docked together Qt provides a QTabBar that is
    created on the fly and is not accessible globally. Additional to the tabbar
    docked widgets have a title bar that offer float and close buttons.

    This dockwidget includes a custom title bar that acts as both the tab bar
    (if needed) and hides the original QTabBar that gets created on the fly.
    """
    ALLOWED_AREAS = Qt.AllDockWidgetAreas
    LOCATION = Qt.LeftDockWidgetArea
    FEATURES = QDockWidget.DockWidgetClosable | QDockWidget.DockWidgetFloatable

    # Signals
    plugin_closed = Signal()
    sig_selected = Signal()

    def __init__(self, title, parent=None, plugin=None):
        """Dockwidget that overrides methods and creates curstom title bar."""

        super(SpyderDockWidget, self).__init__(title, parent)

        # Needed for the installation of the event filter
        self.title = title
        self.main = parent
        self.plugin = plugin

        # Widgets
        self.dock_tabbar = None
        self.title_bar = TitleBarWidget(parent=self, title=title)

        # Widget setup
        if self.plugin:
            self.setWidget(plugin)
            self.setObjectName(self.plugin.__class__.__name__+"_dw")

        self.setTitleBarWidget(self.title_bar)
        self.setAttribute(Qt.WA_LayoutUsesWidgetRect, True)
        self.setAllowedAreas(self.ALLOWED_AREAS)
        self.setFeatures(self.FEATURES)

        # Signals
        self.visibilityChanged.connect(self.setup)
        self.topLevelChanged.connect(self.setup)
        self.featuresChanged.connect(self.setup)
        self.dockLocationChanged.connect(self.setup)
        self.allowedAreasChanged.connect(self.setup)

        # Setup
        self.setup()

    # --- Qt Overrrides
    # -------------------------------------------------------------------------
    def closeEvent(self, event):
        """
        Override Qt method.

        Send a signal on close so that "Panes" main window menu can be updated
        correctly.
        """
        self.plugin_closed.emit()

    # --- Helpers
    # -------------------------------------------------------------------------
    def _tab_closed(self, text=None):
        """Close the selected tab on the custom title bar."""
        for plugin in self.main.widgetlist:
            if text == plugin.get_plugin_title():
                plugin.dockwidget.closeEvent(None)
            if plugin.dockwidget.dock_tabbar is self.dock_tabbar:
                plugin.dockwidget.setup()
            
    def _tab_moved(self, from_index, to_index):
        """Move the tabs on the custom title bar."""
        if self.dock_tabbar:
            self.dock_tabbar.moveTab(from_index, to_index)

    def _tab_selected(self, index):
        """Select tab on mouse click on the custom title bar."""
        self.blockSignals(True)
        self.setUpdatesEnabled(False)
        if self.dock_tabbar:
            self.dock_tabbar.setCurrentIndex(index)
        self.setUpdatesEnabled(True)
        self.blockSignals(False)

    # --- API
    # -------------------------------------------------------------------------
    def set_locked(self, value):
        """Set the locked status of the dokwidget."""

    def plugin_titles(self):
        """Get all names of plugins."""
        plugin_titles = []
        for plugin in self.main.widgetlist:
            plugin_titles.append(plugin.get_plugin_title())
        return plugin_titles

    def dock_tabbars(self):
        """"Find all dock widget tabbars."""
        dock_tabbars = []
        tabbars = self.main.findChildren(QTabBar)
        for tabbar in tabbars:
            if not isinstance(tabbar, DockTabBar):
                for tab in range(tabbar.count()):
                    title = tabbar.tabText(tab)
                    if title in self.plugin_titles():
                        dock_tabbars.append(tabbar)
        return list(set(dock_tabbars))

    def dock_tabbar_titles(self):
        """"""
        titles = []
        if self.dock_tabbar:
            for i in range(self.dock_tabbar.count()):
                title = self.dock_tabbar.tabText(i)
                titles.append(title)
        return titles

    def titlebar_titles(self):
        """"""
        titles = []
        for i in range(self.title_bar.count()):
            title = self.dock_tabbar.tabText(i)
            titles.append(title)
        return titles

    def hide_dock_tabbar(self):
        """Hide original dockwidget tabbar."""
        self.dock_tabbar.setStyleSheet('''
            QTabBar:tab {
                border: 0px solid black;
                background: none;
                padding: 0px;
                margin: 0px;
                outline: none;
                min-height: 0px;
                max-height: 0px;
            }
        ''')

    def setup(self, value=None):
        """"""
        #self.title_bar.setVisible(not self.isFloating())
        dock_tabbar = None
        for tabbar in self.dock_tabbars():
            for tab in range(tabbar.count()):
                title = tabbar.tabText(tab)
                if title == self.title:
                    dock_tabbar = tabbar
                    break

        # Disconnect signals to avoid duplication of actions
        for signal in (self.title_bar.sig_tab_closed,
                       self.title_bar.sig_tab_moved,
                       self.title_bar.sig_tab_selected):
            try:
                signal.disconnect()
            except Exception:
                pass

#        print(self.title, self.dock_tabbar)
        if dock_tabbar is not None:
            self.dock_tabbar = dock_tabbar

            self.title_bar.sig_tab_closed.connect(self._tab_closed)
            self.title_bar.sig_tab_moved.connect(self._tab_moved)
            self.title_bar.sig_tab_selected.connect(self._tab_selected)
            self.title_bar.add_tabs(self.dock_tabbar_titles())
            self.hide_dock_tabbar()
        else:
            self.dock_tabbar = None
            self.title_bar.sig_tab_closed.connect(self._tab_closed)
            self.title_bar.add_tabs([self.title])


class FocusIndicatorFrame(QFrame):
    """
    Frame located on the bottom of the custom title bar widget.

    This class is used for CSS styling.
    """


class TitleBarWidget(QFrame):
    """Custom Dockwidget title bar."""
    sig_tab_closed = Signal(str)
    sig_tab_moved = Signal(int, int)
    sig_tab_selected = Signal(int)

    def __init__(self, parent=None, title=None):
        """Custom Dockwidget title bar."""
        super(TitleBarWidget, self).__init__(parent)
        self._title = title

        # Widgets
        self._tabbar = DockTabBar(self)
        self._focus_indicator = FocusIndicatorFrame(self)

        # Widget setup
        self.setStyleSheet("""
        TitleBarWidget {
          background: transparent;
          margin: 12px;
        }

        FocusIndicatorFrame {
          background: #2fa4e7;
          background: transparent;
          min-height: 12px;
        }""")


        if sys.platform == 'darwin':
            self.align = Qt.AlignCenter
        else:
            self.align = Qt.AlignLeft

        # Layouts
        horizontal_layout = QHBoxLayout()
        horizontal_layout.addWidget(self._tabbar, self.align)
        horizontal_layout.addStretch()
        horizontal_layout.addSpacing(20)

        layout = QVBoxLayout()
        layout.addLayout(horizontal_layout)
        layout.addWidget(self._focus_indicator)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        self.setLayout(layout)

        # Signals
        self._tabbar.tabMoved.connect(self.sig_tab_moved)
        self._tabbar.sig_tab_closed.connect(self.sig_tab_closed)
        self._tabbar.currentChanged.connect(self.sig_tab_selected)

    def set_current_index(self, index):
        """"""
        self._tabbar.setCurrentIndex(index)

    def tabs_titles(self):
        """TODO:"""
        titles = []
        for i in range(self._tabbar.count()):
            titles.append(self._tabbar.tabText(i))
        return titles

    def add_tabs(self, tabs):
        """TODO:"""
        self.setUpdatesEnabled(False)
        self._tabbar.add_tabs(tabs)
        for i in range(self._tabbar.count()):
            if self._tabbar.tabText(i) == self._title:
                self._tabbar.setCurrentIndex(i)
                break
        self.setUpdatesEnabled(True)



class TabButton(QToolButton):
    """Tab custom close button."""
    TAB_BUTTON_SIZE = 14

    def __init__(self, *args, **kwargs):
        """Tab custom close button."""
        super(TabButton, self).__init__(*args, **kwargs)

        # Widget setup
        # TODO: centralize on QSS, how to handle OS differences?
        self.setAttribute(Qt.WA_LayoutUsesWidgetRect, True)
        self.setStyleSheet(
        '''
        TabButton {
          margin: 1px;
          padding: 1px;
          background: #999;
          border: 0px solid black;
          border-radius:6px;
        }
        TabButton:hover{
          background: #aaa;
        }
        TabButton:pressed {
          background: #777;
        }
        '''
        )
        self.setContentsMargins(0, 0, 0, 0)
        self.setIcon(ima.icon('close_panel', options={'color': 'white'}))

    def sizeHint(self):
        """Override Qt method."""
        return QSize(self.TAB_BUTTON_SIZE, self.TAB_BUTTON_SIZE)


class DockTabBar(QTabBar):
    """Custom tabbar to use in place of the normal docked panes tab bar."""
    
    sig_tab_closed = Signal(str)

    def __init__(self, *args, **kwargs):
        """Custom tabbar to use in place of the normal docked panes tab bar."""
        super(DockTabBar, self).__init__(*args, **kwargs)

        # Widgets
        self._tab_buttons = {}
        self._menu_actions = [
            create_action(self, '&Float panel'),
            create_action(self, '&Close panel'), ]

        # Widget setup
        self.setDrawBase(False)
        self.setMovable(True)
        self.setMouseTracking(True)

        # Signals
        self.currentChanged.connect(self._refresh_buttons)
        self.tabMoved.connect(self._reconnect_buttons)

        if sys.platform == 'darwin':
            self.side = QTabBar.LeftSide
        else:
            self.side = QTabBar.RightSide

    # --- Qt Overrides
    # -------------------------------------------------------------------------
    def leaveEvent(self, event):
        """Override Qt Method."""
        self._refresh_buttons()
        super(DockTabBar, self).leaveEvent(event)

    def mouseMoveEvent(self, event):
        """Override Qt Method."""
        index = self.tabAt(event.pos())
        self._refresh_buttons(hover_index=index)
        super(DockTabBar, self).mouseMoveEvent(event)

    def mousePressEvent(self, event):
        """Override Qt Method."""
        super(DockTabBar, self).mousePressEvent(event)
        if event.button() == Qt.RightButton:
            if self._menu_actions:
                menu = QMenu()
                add_actions(menu, self._menu_actions)
                menu.exec_(self.mapToGlobal(event.pos()))
                event.accept()

    # --- Helpers
    # -------------------------------------------------------------------------
    def _handle_close(self, index=None):
        """# TODO:"""
        if index is not None:
            self.tabCloseRequested.emit(index)
            self.sig_tab_closed.emit(self.tabText(index))

    def _reconnect_buttons(self, index_from=None, index_to=None):
        """# TODO:"""
        for i in range(self.count()):
            button = self.tabButton(i, self.side)
            try:
                button.clicked.disconnect()
            except Exception:
                pass
            button.clicked.connect(lambda a=None, i=i: self._handle_close(i))
            self._tab_buttons[self.tabText(i)] = button

    def _refresh_buttons(self, a=None, hover_index=None):
        """# TODO:"""
        # Make all buttons invisibe
        for i in range(self.count()):
            button = self.tabButton(i, self.side)
            if button:
                button.setVisible(False)

        # Make button visible on current index
        current_index = self.currentIndex()
        button = self.tabButton(current_index, self.side)
        if button:
            button.setVisible(True)

        # Make button visible on hover
        if hover_index is not None:
            button = self.tabButton(hover_index, self.side)
            if button:
                button.setVisible(True)

    # --- API
    # -------------------------------------------------------------------------
    def add_tabs(self, tabs):
        """Add tabs by name."""
        current_tab_names = []
        for i in range(self.count()):
            current_tab_names.append(self.tabText(i))

        # First delete all tabs and associated buttons
        self.blockSignals(True)
        self.setUpdatesEnabled(False)
#        if current_tab_names != tabs:
        self._tab_buttons = {}
        for i in range(self.count(), -1, -1):
            self.removeTab(i)

        # Add tabs
        for tab in tabs:
            self.addTab(tab)

        # Add the close buttons
        for i in range(self.count()):
            button = TabButton(self)
            self.setTabButton(i, self.side, button)
            self._tab_buttons[self.tabText(i)] = button
        self._reconnect_buttons()
        self._refresh_buttons()
        self.setUpdatesEnabled(True)
        self.blockSignals(False)

    def set_menu_actions(self, actions):
        """Set the actions for the context menu."""
        pass


if __name__ == '__main__':
    from qtpy.QtCore import QCoreApplication
    from spyder.utils.qthelpers import qapplication

    if hasattr(Qt, 'AA_UseHighDpiPixmaps'):
        QCoreApplication.setAttribute(Qt.AA_UseHighDpiPixmaps)

    if hasattr(Qt, 'AA_EnableHighDpiScaling'):
        QCoreApplication.setAttribute(Qt.AA_EnableHighDpiScaling)
    app = qapplication()
    w = DockTabBar()
    w.add_tabs(['hello 1', 'hello 2', 'hello 3', 'hello 4'])
    w.add_tabs(['hello 1', 'hello 2', 'hello 3', 'hello 4'])
    w.add_tabs(['hello 1', 'hello 2', 'hello 3', 'hello 5'])
    w.show()
    app.exec_()
