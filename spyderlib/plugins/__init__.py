# -*- coding: utf-8 -*-
#
# Copyright © 2009-2010 Pierre Raybaut
# Licensed under the terms of the MIT License
# (see spyderlib/__init__.py for details)

"""
spyderlib.plugins
=================

Here, 'plugins' are widgets designed specifically for Spyder
These plugins inherit the following classes
(SpyderPluginMixin & SpyderPluginWidget)
"""

# pylint: disable=C0103
# pylint: disable=R0903
# pylint: disable=R0911
# pylint: disable=R0201

# Standard library imports
import inspect
import os

# Third party imports
from spyderlib.qt import PYQT5
from spyderlib.qt.QtCore import (Qt, Signal, QPoint, QSize, QObject, QEvent)
from spyderlib.qt.QtGui import (QDockWidget, QWidget, QShortcut, QCursor,
                                QKeySequence, QMainWindow, QApplication,
                                QLabel, QPainter, QToolButton, QFrame, QStyle,
                                QVBoxLayout, QHBoxLayout, QTabBar)

# Local imports
from spyderlib.utils import icon_manager as ima
from spyderlib.utils.qthelpers import toggle_actions, create_action
from spyderlib.config.base import _, debug_print
from spyderlib.config.gui import get_font, set_font
from spyderlib.config.main import CONF
from spyderlib.config.user import NoDefault
from spyderlib.plugins.configdialog import SpyderConfigPage
from spyderlib.py3compat import configparser, is_text_string, to_text_string


class PluginConfigPage(SpyderConfigPage):
    """Plugin configuration dialog box page widget"""
    def __init__(self, plugin, parent):
        self.plugin = plugin
        self.get_option = plugin.get_option
        self.set_option = plugin.set_option
        self.get_font = plugin.get_plugin_font
        self.set_font = plugin.set_plugin_font
        self.apply_settings = plugin.apply_plugin_settings
        SpyderConfigPage.__init__(self, parent)

    def get_name(self):
        return self.plugin.get_plugin_title()

    def get_icon(self):
        return self.plugin.get_plugin_icon()


class EmptyTitleBar(QWidget):
    """
    When docks are locked and title bar is set to be hidden.

    This provides a minimal vertical space for having a clean look.
    """
    def sizeHint(self):
        return QSize(2, 2)  # TODO: find adequate metrics here.


class DirectionLabel(QLabel):
    """A QLabel that can be set to horizontal or vertical."""
    def __init__(self, *args, **kwargs):
        super(DirectionLabel, self).__init__(*args, **kwargs)
        self._parent = kwargs.get('parent', 0)
        self._horizontal = True
        self._offset = TitleButton.HEIGHT*3 + TitleButton.SPACING*4 + 10

    def paintEvent(self, event):
        """Overloaded Qt method."""
        if self._horizontal:
            QLabel.paintEvent(self, event)
        else:
            painter = QPainter(self)

            text = to_text_string(self.text())
            fm = self.fontMetrics()
            font_height = fm.height()
            h = self._parent.height()

            # TODO: Check that this is acurate
            painter.translate(font_height, h - self._offset)
            painter.rotate(270)
            painter.drawText(QPoint(0, 0), text)

    def sizeHint(self):
        """Overloaded Qt method."""
        return QSize(24, 24)

    # Public api
    def set_horizontal(self, horizontal=True):
        """Set the direction to horizontal if True, or vertical if False."""
        self._horizontal = horizontal


class TitleButton(QToolButton):
    """A generic tool button for pane options."""
    WIDTH = 16
    HEIGHT = 18
    SPACING = 0

    def __init__(self, parent=0):
        super(TitleButton, self).__init__(parent=parent)
        self.setContentsMargins(0, 0, 0, 0)
        self.setIconSize(QSize(self.WIDTH, self.HEIGHT))

    def sizeHint(self):
        """Overloaded Qt method"""
        return QSize(self.WIDTH, self.HEIGHT)


class SpyderTitleBarWidget(QFrame):
    """ """
    MIN_LENGTH = 24
    MAX_LENGTH = 16777215

    def __init__(self, title, parent=0):
        super(SpyderTitleBarWidget, self).__init__(parent=parent)
        self.dockwidget = parent
        self._content_margins = (1, 0, 1, 0)
        self._title = title

        self.setLayout(QHBoxLayout())
        self._set_layout()
        self.set_content_margins(self._content_margins)

    def _is_vertical(self):
        """
        Returns True if the current orientation of the title bar is verical.
        """
        features = self.dockwidget.features()
        return features & QDockWidget.DockWidgetVerticalTitleBar

    def _clear_layout(self, layout):
        """Remove the current layout of the title bar."""
        if layout is not None:
            while layout.count():
                item = layout.takeAt(0)
                widget = item.widget()
                if widget is not None:
                    widget.deleteLater()
                else:
                    self._clear_layout(item.layout())

    def _update(self):
        """Update the look and feel of pane buttons."""
        style = QApplication.style()
        icon_close = style.standardIcon(QStyle.SP_TitleBarCloseButton)
        icon_float = style.standardIcon(QStyle.SP_TitleBarNormalButton)
        icon_maximize = style.standardIcon(QStyle.SP_TitleBarMaxButton)

        # Widget setup
        self._button_close.setAutoRaise(True)
        self._button_float.setAutoRaise(True)
        self._button_maximize.setAutoRaise(True)

        self._button_close.setIcon(icon_close)
        self._button_float.setIcon(icon_float)
        self._button_maximize.setIcon(icon_maximize)

        self.set_content_margins(self._content_margins)

    def _set_layout(self):
        """Reset the layout of the title bar based on dock options."""
        if self.layout().count():
            layout = self.layout().takeAt(0)
            self._clear_layout(layout)
            layout.deleteLater()

        self._label_title = DirectionLabel(self._title, parent=self)
        self._button_close = TitleButton(parent=self)
        self._button_maximize = TitleButton(parent=self)
        self._button_float = TitleButton(parent=self)

        # Add tooltips
        self._button_close.setToolTip(_("Close pane"))
        self._button_float.setToolTip(_("Float pane"))
        self._button_maximize.setToolTip(_("Maximize pane"))

        if self.dockwidget.isFloating():
            self.setFrameStyle(QFrame.NoFrame)
            b = 2  # FIXME: find the adequate metrics here...
        elif not self.dockwidget.locked:
            self.setFrameStyle(QFrame.StyledPanel)
            b = 1
        else:
            self.setFrameStyle(QFrame.NoFrame)
            b = 2  # FIXME: find the adequate metrics here...

        if self._is_vertical():
            self._content_margins = (0+b, 1+b, 0+b, 1+b)
            layout = QVBoxLayout()

            widgets = [self._button_close, self._button_float,
                       self._button_maximize, self._label_title]

            self._label_title.set_horizontal(False)
            self._orientation = Qt.Vertical
            self.setMaximumHeight(self.MAX_LENGTH)
            self.setMaximumWidth(self.MIN_LENGTH)
        else:
            self._content_margins = (1+b, 0+b, 1+b, 0+b)
            layout = QHBoxLayout()

            widgets = [self._label_title, self._button_maximize,
                       self._button_float, self._button_close]

            self._label_title.set_horizontal(True)
            self._label_title.setAlignment(Qt.AlignCenter)
            self._orientation = Qt.Horizontal
            self.setMaximumHeight(self.MIN_LENGTH)
            self.setMaximumWidth(self.MAX_LENGTH)

        if self.dockwidget.isFloating():
            self._button_float.setToolTip(_("Restore pane"))
            widgets_enable = [self._label_title, self._button_float]
        elif self.dockwidget.maximized:
            self._button_maximize.setToolTip(_("Restore pane"))
            widgets_enable = [self._label_title, self._button_maximize]
        else:
            widgets_enable = widgets

        for w in widgets:
            if w:
                layout.addWidget(w, Qt.AlignCenter)
                w.setEnabled(False)
            else:
                layout.addStretch()

        for w in widgets_enable:
            if w:
                w.setEnabled(True)

        if self.layout() is None:
            self.setLayout(layout)
        else:
            self.layout().insertLayout(0, layout)

        # Signals and slots
        self._button_float.clicked.connect(self.dockwidget.float_window)
        self._button_close.clicked.connect(self.dockwidget.close)
        self._button_maximize.clicked.connect(self.dockwidget.maximize)

        self._update()

    # Qt overloads
    def sizeHint(self):
        """Overloaded Qt method"""
        if self._is_vertical():
            return QSize(self.MIN_LENGTH, self.MIN_LENGTH*3)
        else:
            return QSize(self.MIN_LENGTH, self.MIN_LENGTH)

    def minimumSizeHint(self):
        """Overloaded Qt method"""
        return self.sizeHint()

    def mouseDoubleClickEvent(self, event):
        """Overloaded Qt method"""
        if not self.dockwidget.locked:
            self.dockwidget.float_window()

    # Public api
    def update_features(self):
        """Reset layout when features change."""
        if not (self._is_vertical() and self._orientation == Qt.Vertical or
           not self._is_vertical() and self._orientation == Qt.Horizontal):
            self._set_layout()

    def set_title(self, value):
        """Set the title of the title bar."""
        self._title = value
        self._label_title.setText(self._title)

    def set_content_margins(self, margins=None):
        """Set the content margins of the title bar."""
        if margins is None:
            margins = self._content_margins
        self._content_margins = margins
        self.layout().setSpacing(TitleButton.SPACING)
        self.layout().setContentsMargins(*margins)


class TabFilter(QObject):
    """
    Filter event attached to each QTabBar that holds 2 or more dockwidgets in
    charge of handling tab rearangement.

    This filter also holds the methods needed for the detection of a drag and
    the movement of tabs.
    """
    def __init__(self, dock_tabbar, dockwidget, main):
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
            if plugin.get_plugin_title() == self.dock_tabbar.tabText(index):
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
    # Custom signals
    plugin_closed = Signal()

    # Class variables
    FEATURES = QDockWidget.DockWidgetClosable
    ALLOWED_AREAS = Qt.AllDockWidgetAreas
    LOCATION = Qt.LeftDockWidgetArea

    def __init__(self, title, parent, get_focus_func):
        super(SpyderDockWidget, self).__init__(title, parent)

        # Needed for the installation of the event filter
        self.title = title
        self.main = parent
        self.dock_tabbar = None
        self.maximized = False
        self.locked = None

        # This is needed for the new maximize button in the custom title bar
        self._flags = self.windowFlags()
        self.custom_titlebar = SpyderTitleBarWidget(title, self)
        self.get_focus_widget = get_focus_func

        # Widget setup
        self.setTitleBarWidget(self.custom_titlebar)

        # Signals and slots
        self.featuresChanged.connect(self.custom_titlebar.update_features)
        self.dockLocationChanged.connect(self.fix_tab_name)
        # To track dockwidget changes the filter is installed when dockwidget
        # visibility changes. This installs the filter on startup and also
        # on dockwidgets that are undocked and then docked to a new location.
        self.visibilityChanged.connect(self.install_tab_event_filter)

    def closeEvent(self, event):
        """
        Reimplement Qt method to send a signal on close so that "Panes" main
        window menu can be updated correctly
        """
        self.plugin_closed.emit()

    def setWindowTitle(self, title):
        """Override Qt method"""
        # This is needed due to the custom title bar
        if self.isFloating():
            super(SpyderDockWidget, self).setWindowTitle(self.main.windowTitle())
        else:
            super(SpyderDockWidget, self).setWindowTitle(self.title)
        self.custom_titlebar.set_title(title)

    def fix_tab_name(self):
        """
        This method is needed for windows user double clicking on the titlebar
        of a floating dockwidget.
        """
        if self.dock_tabbar is not None:
            for index in range(self.dock_tabbar.count()):
                if self.main.windowTitle() == self.dock_tabbar.tabText(index):
                    self.update_dockwidget()
                    break

    def update_dockwidget(self, show=True, maximized=False):
        """Update dockwidget (pane) titlebar and enabled buttons."""
        debug_print('updating', self.title, self.isFloating())
        features = self.FEATURES
        vertical_title = CONF.get('main', 'vertical_dockwidget_titlebars')
        hide_dock_titlebar = CONF.get('main', 'hide_dock_titlebar')
        locked = self.main.dockwidgets_locked

        if vertical_title:
            features = features | QDockWidget.DockWidgetVerticalTitleBar
        if not locked:
            features = features | QDockWidget.DockWidgetMovable

        self.maximized = maximized
        self.locked = locked
        self.custom_titlebar._set_layout()
        if not maximized:
            self.setTitleBarWidget(self.custom_titlebar)

        if self.isFloating():
            show = True
            # When a dockwidget is set to float, this prevents the dockwidget
            # from redocking if the window is moved on top of any part of the
            # spyder application.
            self.setAllowedAreas(Qt.BottomDockWidgetArea)
            self.setWindowFlags(Qt.Window)
            self.setFeatures(features | QDockWidget.DockWidgetFloatable)
        else:
            self.setAllowedAreas(self.ALLOWED_AREAS)
            self.setFeatures(features)
            self.setWindowFlags(self._flags)

        self.setWindowTitle(self.title)

        if locked and hide_dock_titlebar and not self.isFloating():
            self.setTitleBarWidget(EmptyTitleBar())

        if show:
            self.show()
            self.raise_()

    def float_window(self):
        """Float dockwidget (pane) as an independent window."""
        self.setFloating(not self.isFloating())
        self.update_dockwidget()

    def maximize(self):
        """Maximize dockwidget (pane)."""
        self.get_focus_widget().setFocus()
        self.main.maximize_dockwidget()
        self.maximized = not self.maximized

    def get_dock_tabbars(self):
        """Returns a list of QTabBars in the main window."""
        tabbars = self.main.findChildren(QTabBar)
        dock_tabbars = []
        for tabbar in tabbars:
            if '.QTabBar' in str(tabbar):
                dock_tabbars.append(tabbar)
        return dock_tabbars

    # This method is needed to allow tab reordering
    def install_tab_event_filter(self, value):
        """
        Install an event filter to capture mouse events in the tabs of a
        QTabBar holding tabified dockwidgets.
        """
        dock_tabbar = None
        tabbars = self.get_dock_tabbars()
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
                                                    self, self.main)
                self.dock_tabbar.installEventFilter(self.dock_tabbar.filter)
            self.fix_tab_name()


class SpyderPluginMixin(object):
    """
    Useful methods to bind widgets to the main window
    See SpyderPluginWidget class for required widget interface
    
    Signals:
        * sig_option_changed
             Example:
             plugin.sig_option_changed.emit('show_all', checked)
        * show_message
        * update_plugin_title
    """
    CONF_SECTION = None
    CONFIGWIDGET_CLASS = None
    IMG_PATH = 'images'
    DISABLE_ACTIONS_WHEN_HIDDEN = True

    # Signals
    sig_option_changed = None
    show_message = None
    update_plugin_title = None

    def __init__(self, main=None, **kwds):
        """Bind widget to a QMainWindow instance"""
        super(SpyderPluginMixin, self).__init__(**kwds)
        assert self.CONF_SECTION is not None
        self.PLUGIN_PATH = os.path.dirname(inspect.getfile(self.__class__))
        self.main = main
        self.default_margins = None
        self.plugin_actions = None
        self.dockwidget = None
        self.mainwindow = None
        self.ismaximized = False
        self.isvisible = False

        # NOTE: Don't use the default option of CONF.get to assign a
        # None shortcut to plugins that don't have one. That will mess
        # the creation of our Keyboard Shortcuts prefs page
        try:
            self.shortcut = CONF.get('shortcuts', '_/switch to %s' % \
                                     self.CONF_SECTION)
        except configparser.NoOptionError:
            self.shortcut = None

        # We decided to create our own toggle action instead of using
        # the one that comes with dockwidget because it's not possible
        # to raise and focus the plugin with it.
        self.toggle_view_action = None 
        
    def initialize_plugin(self):
        """Initialize plugin: connect signals, setup actions, ..."""
        self.plugin_actions = self.get_plugin_actions()
        if self.show_message is not None:
            self.show_message.connect(self.__show_message)
        if self.update_plugin_title is not None:
            self.update_plugin_title.connect(self.__update_plugin_title)
        if self.sig_option_changed is not None:
            self.sig_option_changed.connect(self.set_option)
        self.setWindowTitle(self.get_plugin_title())
        self.create_toggle_view_action()

    def on_first_registration(self):
        """Action to be performed on first plugin registration"""
        # Was written to handle the very first plugin position in Spyder's
        # main window layout, but this could also be used for other things
        # (see for example the IPython console plugin for which this method 
        #  had to be written to handle the fact that this plugin was 
        #  introduced between v2.1 and v2.2)
        raise NotImplementedError

    def initialize_plugin_in_mainwindow_layout(self):
        """If this is the first time the plugin is shown, perform actions to
        initialize plugin position in Spyder's window layout"""
        if self.get_option('first_time', True):
            try:
                self.on_first_registration()
            except NotImplementedError:
                return
            self.set_option('first_time', False)
        
    def update_margins(self):
        layout = self.layout()
        if self.default_margins is None:
            self.default_margins = layout.getContentsMargins()
        if CONF.get('main', 'use_custom_margin'):
            margin = CONF.get('main', 'custom_margin')
            layout.setContentsMargins(*[margin]*4)
        else:
            layout.setContentsMargins(*self.default_margins)
            
    def __update_plugin_title(self):
        """Update plugin title, i.e. dockwidget or mainwindow title"""
        if self.dockwidget is not None:
            win = self.dockwidget
        elif self.mainwindow is not None:
            win = self.mainwindow
        else:
            return
        win.setWindowTitle(self.get_plugin_title())
        
    def create_dockwidget(self):
        """Add to parent QMainWindow as a dock widget"""

        # This is not clear yet why the following do not work...
        # (see Issue #880)
##         # Using Qt.Window window flags solves Issue #880 (detached dockwidgets
##         # are not painted after restarting Spyder and restoring their hexstate)
##         # but it does not work with PyQt <=v4.7 (dockwidgets can't be docked)
##         # or non-Windows platforms (lot of warnings are printed out)
##         # (so in those cases, we use the default window flags: Qt.Widget):
##         flags = Qt.Widget if is_old_pyqt or os.name != 'nt' else Qt.Window
        dock = SpyderDockWidget(self.get_plugin_title(), parent=self.main,
                                get_focus_func=self.get_focus_widget)#, flags)

        dock.setObjectName(self.__class__.__name__+"_dw")
        dock.setAllowedAreas(dock.ALLOWED_AREAS)
        dock.setFeatures(dock.FEATURES)
        dock.setWidget(self)
        self.update_margins()
        dock.visibilityChanged.connect(self.visibility_changed)
        dock.plugin_closed.connect(self.plugin_closed)
        self.dockwidget = dock
        self.update_margins()
        if self.shortcut is not None:
            sc = QShortcut(QKeySequence(self.shortcut), self.main,
                            self.switch_to_plugin)
            self.register_shortcut(sc, "_", "Switch to %s" % self.CONF_SECTION)
        return (dock, dock.LOCATION)
    
    def create_mainwindow(self):
        """
        Create a QMainWindow instance containing this plugin
        Note: this method is currently not used
        """
        self.mainwindow = mainwindow = QMainWindow()
        mainwindow.setAttribute(Qt.WA_DeleteOnClose)
        icon = self.get_plugin_icon()
        if is_text_string(icon):
            icon = self.get_icon(icon)
        mainwindow.setWindowIcon(icon)
        mainwindow.setWindowTitle(self.get_plugin_title())
        mainwindow.setCentralWidget(self)
        self.refresh_plugin()
        return mainwindow
    
    def create_configwidget(self, parent):
        """Create configuration dialog box page widget"""
        if self.CONFIGWIDGET_CLASS is not None:
            configwidget = self.CONFIGWIDGET_CLASS(self, parent)
            configwidget.initialize()
            return configwidget

    def apply_plugin_settings(self, options):
        """Apply configuration file's plugin settings"""
        raise NotImplementedError
    
    def register_shortcut(self, qaction_or_qshortcut, context, name,
                          default=NoDefault):
        """
        Register QAction or QShortcut to Spyder main application,
        with shortcut (context, name, default)
        """
        self.main.register_shortcut(qaction_or_qshortcut,
                                    context, name, default)
        
    def register_widget_shortcuts(self, context, widget):
        """
        Register widget shortcuts
        widget interface must have a method called 'get_shortcut_data'
        """
        for qshortcut, name, default in widget.get_shortcut_data():
            self.register_shortcut(qshortcut, context, name, default)
    
    def switch_to_plugin(self):
        """Switch to plugin
        This method is called when pressing plugin's shortcut key"""
        if not self.ismaximized:
            self.dockwidget.show()
        if not self.toggle_view_action.isChecked():
            self.toggle_view_action.setChecked(True)
        self.visibility_changed(True)

    def visibility_changed(self, enable):
        """DockWidget visibility has changed"""
        if enable:
            self.dockwidget.raise_()
            widget = self.get_focus_widget()
            if widget is not None:
                widget.setFocus()
        visible = self.dockwidget.isVisible() or self.ismaximized
        if self.DISABLE_ACTIONS_WHEN_HIDDEN:
            toggle_actions(self.plugin_actions, visible)
        self.isvisible = enable and visible
        if self.isvisible:
            self.refresh_plugin()   # To give focus to the plugin's widget
    
    def plugin_closed(self):
        """DockWidget was closed"""
        self.toggle_view_action.setChecked(False)

    def set_option(self, option, value):
        """
        Set a plugin option in configuration file
        Use a SIGNAL to call it, e.g.:
        plugin.sig_option_changed.emit('show_all', checked)
        """
        CONF.set(self.CONF_SECTION, str(option), value)

    def get_option(self, option, default=NoDefault):
        """Get a plugin option from configuration file"""
        return CONF.get(self.CONF_SECTION, option, default)
    
    def get_plugin_font(self, option=None):
        """Return plugin font option"""
        return get_font(self.CONF_SECTION, option)
    
    def set_plugin_font(self, font, option=None):
        """Set plugin font option"""
        set_font(font, self.CONF_SECTION, option)

    def __show_message(self, message, timeout=0):
        """Show message in main window's status bar"""
        self.main.statusBar().showMessage(message, timeout)

    def starting_long_process(self, message):
        """
        Showing message in main window's status bar
        and changing mouse cursor to Qt.WaitCursor
        """
        self.__show_message(message)
        QApplication.setOverrideCursor(QCursor(Qt.WaitCursor))
        QApplication.processEvents()
        
    def ending_long_process(self, message=""):
        """
        Clearing main window's status bar
        and restoring mouse cursor
        """
        QApplication.restoreOverrideCursor()
        self.__show_message(message, timeout=2000)
        QApplication.processEvents()
        
    def set_default_color_scheme(self, name='Spyder'):
        """Set default color scheme (only once)"""
        color_scheme_name = self.get_option('color_scheme_name', None)
        if color_scheme_name is None:
            names = CONF.get("color_schemes", "names")
            if name not in names:
                name = names[0]
            self.set_option('color_scheme_name', name)
    
    def create_toggle_view_action(self):
        """Associate a toggle view action with each plugin"""
        title = self.get_plugin_title()
        if self.CONF_SECTION == 'editor':
            title = _('Editor')
        if self.shortcut is not None:
            action = create_action(self, title,
                             toggled=lambda checked: self.toggle_view(checked),
                             shortcut=QKeySequence(self.shortcut))
            action.setShortcutContext(Qt.WidgetWithChildrenShortcut)
        else:
            action = create_action(self, title, toggled=lambda checked:
                                                self.toggle_view(checked))
        self.toggle_view_action = action
    
    def toggle_view(self, checked):
        """Toggle view"""
        if checked:
            self.dockwidget.show()
            self.dockwidget.raise_()
        else:
            self.dockwidget.hide()


class SpyderPluginWidget(QWidget, SpyderPluginMixin):
    """
    Spyder base widget class
    Spyder's widgets either inherit this class or reimplement its interface
    """
    sig_option_changed = Signal(str, object)
    show_message = Signal(str, int)
    update_plugin_title = Signal()

    if PYQT5:
        def __init__(self, parent, **kwds):
            super(SpyderPluginWidget, self).__init__(parent, **kwds)
    else:
        def __init__(self, parent):
            QWidget.__init__(self, parent)
            SpyderPluginMixin.__init__(self, parent)
        
    def get_plugin_title(self):
        """
        Return plugin title
        Note: after some thinking, it appears that using a method
        is more flexible here than using a class attribute
        """
        raise NotImplementedError
    
    def get_plugin_icon(self):
        """
        Return plugin icon (QIcon instance)
        Note: this is required for plugins creating a main window
              (see SpyderPluginMixin.create_mainwindow)
              and for configuration dialog widgets creation
        """
        return ima.icon('outline_explorer')
    
    def get_focus_widget(self):
        """
        Return the widget to give focus to when
        this plugin's dockwidget is raised on top-level
        """
        pass
        
    def closing_plugin(self, cancelable=False):
        """
        Perform actions before parent main window is closed
        Return True or False whether the plugin may be closed immediately or not
        Note: returned value is ignored if *cancelable* is False
        """
        return True
        
    def refresh_plugin(self):
        """Refresh widget"""
        raise NotImplementedError
    
    def get_plugin_actions(self):
        """
        Return a list of actions related to plugin
        Note: these actions will be enabled when plugin's dockwidget is visible
              and they will be disabled when it's hidden
        """
        raise NotImplementedError
    
    def register_plugin(self):
        """Register plugin in Spyder's main window"""
        raise NotImplementedError
