# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""
Layout Plugin.
"""
# Standard library imports
import configparser as cp
import os

# Third party imports
from qtpy.QtCore import Qt, QByteArray, QSize, QPoint, Slot
from qtpy.QtWidgets import QApplication, QDesktopWidget, QDockWidget

# Local imports
from spyder.api.plugins import Plugins, SpyderPluginV2
from spyder.api.translations import get_translation
from spyder.plugins.mainmenu.api import ApplicationMenus, ViewMenuSections
from spyder.plugins.layout.container import LayoutContainer
from spyder.plugins.layout.layouts import (HorizontalSplitLayout,
                                           MatlabLayout, RLayout,
                                           SpyderLayout, VerticalSplitLayout,
                                           DefaultLayouts)
from spyder.plugins.preferences.widgets.container import PreferencesActions
from spyder.plugins.toolbar.api import (
    ApplicationToolbars, MainToolbarSections)
from spyder.py3compat import qbytearray_to_str  # FIXME:

# Localization
_ = get_translation("spyder")

# Constants
# Number of default layouts available
DEFAULT_LAYOUTS = 4
# Version passed to saveState/restoreState
WINDOW_STATE_VERSION = 1


class Layout(SpyderPluginV2):
    """
    Layout manager plugin.
    """
    NAME = "layout"
    CONF_SECTION = "quick_layouts"
    REQUIRES = [Plugins.All]  # Uses wildcard to require all the plugins
    CONF_FILE = False
    CONTAINER_CLASS = LayoutContainer

    # --- SpyderDockablePlugin API
    # ------------------------------------------------------------------------
    def get_name(self):
        return _("Layout")

    def get_description(self):
        return _("Layout manager")

    def get_icon(self):
        return self.create_icon("history")  # FIXME:

    def register(self):
        container = self.get_container()
        self._last_plugin = None
        self._first_spyder_run = False
        self._fullscreen_flag = None
        # The following flag remember the maximized state even when
        # the window is in fullscreen mode:
        self._maximized_flag = None
        # The following flag is used to restore window's geometry when
        # toggling out of fullscreen mode in Windows.
        self._saved_normal_geometry = None
        self._state_before_maximizing = None
        self._interface_locked = self.get_conf('main', 'panes_locked')

        # Register default layouts
        self.register_layout(self, SpyderLayout)
        self.register_layout(self, RLayout)
        self.register_layout(self, MatlabLayout)
        self.register_layout(self, HorizontalSplitLayout)
        self.register_layout(self, VerticalSplitLayout)

        mainmenu = self.get_plugin(Plugins.MainMenu)
        if mainmenu:
            # Add Panes related actions to View application menu
            panes_items = [
                container._plugins_menu,
                container._lock_interface_action,
                container._close_dockwidget_action,
                container._maximize_dockwidget_action]
            for panes_item in panes_items:
                mainmenu.add_item_to_application_menu(
                    panes_item,
                    menu_id=ApplicationMenus.View,
                    section=ViewMenuSections.Pane,
                    before_section=ViewMenuSections.Toolbar)
            # Add layouts menu to View application menu
            layout_items = [
                container._layouts_menu,
                container._toggle_next_layout_action,
                container._toggle_previous_layout_action]
            for layout_item in layout_items:
                mainmenu.add_item_to_application_menu(
                    layout_item,
                    menu_id=ApplicationMenus.View,
                    section=ViewMenuSections.Layout)
            # Add fullscreen action to View application menu
            mainmenu.add_item_to_application_menu(
                container._fullscreen_action,
                menu_id=ApplicationMenus.View,
                section=ViewMenuSections.Bottom)

        toolbars = self.get_plugin(Plugins.Toolbar)
        if toolbars:
            # Add actions to Main application toolbar
            before_action = self.get_action(
                PreferencesActions.Show,
                plugin=Plugins.Preferences
            )

            toolbars.add_item_to_application_toolbar(
                container._maximize_dockwidget_action,
                toolbar_id=ApplicationToolbars.Main,
                section=MainToolbarSections.ApplicationSection,
                before=before_action
            )

        # Update actions icons and text
        self._update_fullscreen_action()

    def before_mainwindow_visible(self):
        self.setup_layout(default=False)

    def on_mainwindow_visible(self):
        # Populate panes menu
        self.create_plugins_menu()
        # Update panes and toolbars lock status
        self.toggle_lock(self._interface_locked)

    # --- Plubic API
    # ------------------------------------------------------------------------
    def get_last_plugin(self):
        """
        Return the last focused dockable plugin.

        Returns
        -------
        SpyderDockablePlugin
            The last focused dockable plugin.

        """
        return self._last_plugin

    def get_fullscreen_flag(self):
        """
        Give access to the fullscreen flag.

        The flag shows if the mainwindow is in fullscreen mode or not.

        Returns
        -------
        bool
            True is the mainwindow is in fullscreen. False otherwise.

        """
        return self._fullscreen_flag

    def register_layout(self, parent_plugin, layout_type):
        """
        Register a new layout type.

        Parameters
        ----------
        parent_plugin: spyder.api.plugins.SpyderPluginV2
            Plugin registering the layout type.
        layout_type: spyder.plugins.layout.api.BaseGridLayoutType
            Layout to register.
        """
        self.get_container().register_layout(parent_plugin, layout_type)

    def get_layout(self, layout_id):
        """
        Get a registered layout by his ID.

        Parameters
        ----------
        layout_id : string
            The ID of the layout.

        Returns
        -------
        Instance of a spyder.plugins.layout.api.BaseGridLayoutType subclass
            Layout.

        """
        return self.get_container().get_layout(layout_id)

    def setup_layout(self, default=False):
        """Initialize mainwindow layout."""
        prefix = 'window' + '/'
        settings = self.load_window_settings(prefix, default)
        hexstate = settings[0]

        self._first_spyder_run = False
        if hexstate is None:
            # First Spyder execution:
            self.main.setWindowState(Qt.WindowMaximized)
            self._first_spyder_run = True
            self.setup_default_layouts('default', settings)

            # Now that the initial setup is done, copy the window settings,
            # except for the hexstate in the quick layouts sections for the
            # default layouts.
            # Order and name of the default layouts is found in config.py
            section = 'quick_layouts'
            get_func = self.get_conf
            order = get_func(section, 'order')

            # Restore the original defaults if reset layouts is called
            if default:
                self.set_conf(section, 'active', order)
                self.set_conf(section, 'order', order)
                self.set_conf(section, 'names', order)

            for index, _name, in enumerate(order):
                prefix = 'layout_{0}/'.format(index)
                self.save_current_window_settings(prefix, section,
                                                  none_state=True)

            # Store the initial layout as the default in spyder
            prefix = 'layout_default/'
            section = 'quick_layouts'
            self.save_current_window_settings(prefix, section, none_state=True)
            self._current_quick_layout = 'default'

        self.set_window_settings(*settings)

    def setup_default_layouts(self, index, settings):
        """Setup default layouts when run for the first time."""
        main = self.main
        main.setUpdatesEnabled(False)

        first_spyder_run = bool(self._first_spyder_run)  # Store copy

        if first_spyder_run:
            self.set_window_settings(*settings)
        else:
            if self._last_plugin:
                if self._last_plugin._ismaximized:
                    self.maximize_dockwidget(restore=True)

            if not (main.isMaximized() or self._maximized_flag):
                main.showMaximized()

            min_width = main.minimumWidth()
            max_width = main.maximumWidth()
            base_width = main.width()
            main.setFixedWidth(base_width)

        # IMPORTANT: order has to be the same as defined in the config file
        MATLAB, RSTUDIO, VERTICAL, HORIZONTAL = range(DEFAULT_LAYOUTS)

        # Layout selection
        layouts = {
            'default': self.get_layout(DefaultLayouts.SpyderLayout),
            RSTUDIO: self.get_layout(DefaultLayouts.RLayout),
            MATLAB: self.get_layout(DefaultLayouts.MatlabLayout),
            VERTICAL: self.get_layout(DefaultLayouts.VerticalSplitLayout),
            HORIZONTAL: self.get_layout(DefaultLayouts.HorizontalSplitLayout),
        }

        layout = layouts[index]

        # Apply selected layout
        layout.set_main_window_layout(self.main, self.get_dockable_plugins())

        if first_spyder_run:
            self._first_spyder_run = False
        else:
            self.main.setMinimumWidth(min_width)
            self.main.setMaximumWidth(max_width)

            if not (self.main.isMaximized() or self._maximized_flag):
                self.main.showMaximized()

        self.main.setUpdatesEnabled(True)
        self.main.sig_layout_setup_ready.emit(layout)

        return layout

    def quick_layout_switch(self, index):
        """
        Switch to quick layout number *index*.

        Parameters
        ----------
        index: int
        """
        section = 'quick_layouts'
        container = self.get_container()
        try:
            settings = self.load_window_settings(
                'layout_{}/'.format(index), section=section)
            (hexstate, window_size, prefs_dialog_size, pos, is_maximized,
             is_fullscreen) = settings

            # The defaults layouts will always be regenerated unless there was
            # an overwrite, either by rewriting with same name, or by deleting
            # and then creating a new one
            if hexstate is None:
                # The value for hexstate shouldn't be None for a custom saved
                # layout (ie, where the index is greater than the number of
                # defaults).  See spyder-ide/spyder#6202.
                if index != 'default' and index >= DEFAULT_LAYOUTS:
                    container.critical_message(
                        _("Warning"),
                        _("Error opening the custom layout.  Please close"
                          " Spyder and try again.  If the issue persists,"
                          " then you must use 'Reset to Spyder default' "
                          "from the layout menu."))
                    return
                self.setup_default_layouts(index, settings)
        except cp.NoOptionError:
            container.critical_message(
                _("Warning"),
                _("Quick switch layout #%s has not yet "
                  "been defined.") % str(index))
            return

        self.set_window_settings(*settings)

        # Make sure the flags are correctly set for visible panes
        for plugin in self.get_dockable_plugins():
            try:
                # New API
                action = plugin.toggle_view_action
            except AttributeError:
                # Old API
                action = plugin._toggle_view_action
            action.setChecked(plugin.dockwidget.isVisible())

        return index

    def load_window_settings(self, prefix, default=False, section='main'):
        """
        Load window layout settings from userconfig-based configuration with
        *prefix*, under *section* default: if True, do not restore inner
        layout.
        """
        get_func = self.get_conf
        window_size = get_func(prefix + 'size', section=section)
        prefs_dialog_size = get_func(
            prefix + 'prefs_dialog_size', section=section)

        if default:
            hexstate = None
        else:
            try:
                hexstate = get_func(prefix + 'state', section=section)
            except Exception:
                hexstate = None

        pos = get_func(prefix + 'position', section=section)

        # It's necessary to verify if the window/position value is valid
        # with the current screen. See spyder-ide/spyder#3748.
        width = pos[0]
        height = pos[1]
        screen_shape = QApplication.desktop().geometry()
        current_width = screen_shape.width()
        current_height = screen_shape.height()
        if current_width < width or current_height < height:
            pos = get_func(prefix + 'position', section)

        is_maximized = get_func(prefix + 'is_maximized', section=section)
        is_fullscreen = get_func(prefix + 'is_fullscreen', section=section)
        return (hexstate, window_size, prefs_dialog_size, pos, is_maximized,
                is_fullscreen)

    def get_window_settings(self):
        """
        Return current window settings.

        Symetric to the 'set_window_settings' setter.
        """
        # FIXME: Window size in main window is update on resize
        window_size = (self.window_size.width(), self.window_size.height())

        is_fullscreen = self.main.isFullScreen()
        if is_fullscreen:
            is_maximized = self._maximized_flag
        else:
            is_maximized = self.main.isMaximized()

        pos = (self.window_position.x(), self.window_position.y())
        prefs_dialog_size = (self.prefs_dialog_size.width(),
                             self.prefs_dialog_size.height())

        hexstate = qbytearray_to_str(
            self.main.saveState(version=WINDOW_STATE_VERSION))
        return (hexstate, window_size, prefs_dialog_size, pos, is_maximized,
                is_fullscreen)

    def set_window_settings(self, hexstate, window_size, prefs_dialog_size,
                            pos, is_maximized, is_fullscreen):
        """
        Set window settings Symetric to the 'get_window_settings' accessor.
        """
        main = self.main
        main.setUpdatesEnabled(False)
        self.prefs_dialog_size = QSize(prefs_dialog_size[0],
                                       prefs_dialog_size[1])  # width,height
        main.set_prefs_size(self.prefs_dialog_size)
        self.window_size = QSize(window_size[0],
                                 window_size[1])  # width, height
        self.window_position = QPoint(pos[0], pos[1])  # x,y
        main.setWindowState(Qt.WindowNoState)
        main.resize(self.window_size)
        main.move(self.window_position)

        # Window layout
        if hexstate:
            hexstate_valid = self.main.restoreState(
                QByteArray().fromHex(str(hexstate).encode('utf-8')),
                version=WINDOW_STATE_VERSION)

            # Check layout validity. Spyder 4 and below uses the version 0
            # state (default), whereas Spyder 5 will use version 1 state.
            # For more info see the version argument for
            # QMainWindow.restoreState:
            # https://doc.qt.io/qt-5/qmainwindow.html#restoreState
            if not hexstate_valid:
                self.main.setUpdatesEnabled(True)
                self.setup_layout(default=True)
                return

            # Workaround for spyder-ide/spyder#880.
            # QDockWidget objects are not painted if restored as floating
            # windows, so we must dock them before showing the mainwindow.
            for widget in self.children():
                if isinstance(widget, QDockWidget) and widget.isFloating():
                    self.floating_dockwidgets.append(widget)
                    widget.setFloating(False)

        # Is fullscreen?
        if is_fullscreen:
            self.main.setWindowState(Qt.WindowFullScreen)

        # Is maximized?
        if is_fullscreen:
            self._maximized_flag = is_maximized
        elif is_maximized:
            self.main.setWindowState(Qt.WindowMaximized)

        self.main.setUpdatesEnabled(True)

    def save_current_window_settings(self, prefix, section='main',
                                     none_state=False):
        """
        Save current window settings.

        Takes config form *prefix* in the userconfig-based configuration,
        under *section*.
        """
        win_size = self.window_size
        prefs_size = self.prefs_dialog_size

        self.set_conf(
            prefix + 'size',
            (win_size.width(), win_size.height()),
            section=section,
        )
        self.set_conf(
            prefix + 'prefs_dialog_size',
            (prefs_size.width(), prefs_size.height()),
            section=section,
        )
        self.set_conf(
            prefix + 'is_maximized',
            self.main.isMaximized(),
            section=section,
        )
        self.set_conf(
            prefix + 'is_fullscreen',
            self.main.isFullScreen(),
            section=section,
        )

        pos = self.window_position
        self.set_conf(
            prefix + 'position',
            (pos.x(), pos.y()),
            section=section,
        )

        self.maximize_dockwidget(restore=True)  # Restore non-maximized layout

        if none_state:
            self.set_conf(
                prefix + 'state',
                None,
                section=section,
            )
        else:
            qba = self.main.saveState(version=WINDOW_STATE_VERSION)
            self.set_conf(
                prefix + 'state',
                qbytearray_to_str(qba),
                section=section,
            )

        self.set_conf(
            prefix + 'statusbar',
            not self.main.statusBar().isHidden(),
            section=section,
        )

    @Slot()
    def close_current_dockwidget(self):
        """Search for the currently focused plugin and close it."""
        widget = QApplication.focusWidget()
        for plugin in self.get_dockable_plugins():
            # TODO: remove old API
            try:
                # New API
                if plugin.get_widget().isAncestorOf(widget):
                    plugin.toggle_view_action.setChecked(False)
                    break
            except AttributeError:
                # Old API
                if plugin.isAncestorOf(widget):
                    plugin._toggle_view_action.setChecked(False)
                    break

    @property
    def maximize_action(self):
        """Expose maximize current dockwidget action."""
        return self.get_container()._maximize_dockwidget_action

    def maximize_dockwidget(self, restore=False):
        """
        Maximize current dockwidget.

        Shortcut: Ctrl+Alt+Shift+M
        First call: maximize current dockwidget
        Second call (or restore=True): restore original window layout
        """
        if self._state_before_maximizing is None:
            if restore:
                return

            # Select plugin to maximize
            self._state_before_maximizing = self.main.saveState(
                version=WINDOW_STATE_VERSION)
            focus_widget = QApplication.focusWidget()

            for plugin in self.get_dockable_plugins():
                plugin.dockwidget.hide()

                try:
                    # New API
                    if plugin.get_widget().isAncestorOf(focus_widget):
                        self._last_plugin = plugin
                except Exception:
                    # Old API
                    if plugin.isAncestorOf(focus_widget):
                        self._last_plugin = plugin

            # Only plugins that have a dockwidget are part of widgetlist,
            # so last_plugin can be None after the above "for" cycle.
            # For example, this happens if, after Spyder has started, focus
            # is set to the Working directory toolbar (which doesn't have
            # a dockwidget) and then you press the Maximize button
            if self._last_plugin is None:
                # Using the Editor as default plugin to maximize
                self._last_plugin = self.get_plugin(Plugins.Editor)

            # Maximize last_plugin
            self._last_plugin.dockwidget.toggleViewAction().setDisabled(True)
            try:
                # New API
                self.main.setCentralWidget(self._last_plugin.get_widget())
            except AttributeError:
                # Old API
                self.main.setCentralWidget(self._last_plugin)

            self._last_plugin._ismaximized = True

            # Workaround to solve an issue with editor's outline explorer:
            # (otherwise the whole plugin is hidden and so is the outline
            # explorer and the latter won't be refreshed if not visible)
            try:
                # New API
                self._last_plugin.get_widget().show()
                self._last_plugin.change_visibility(True)
            except AttributeError:
                # Old API
                self._last_plugin.show()
                self._last_plugin._visibility_changed(True)

            if self._last_plugin is self.main.editor:
                # Automatically show the outline if the editor was maximized:
                outline_explorer = self.get_plugin(Plugins.OutlineExplorer)
                self.main.addDockWidget(
                    Qt.RightDockWidgetArea,
                    outline_explorer.dockwidget)
                outline_explorer.dockwidget.show()
        else:
            # Restore original layout (before maximizing current dockwidget)
            try:
                # New API
                self._last_plugin.dockwidget.setWidget(
                    self._last_plugin.get_widget())
            except AttributeError:
                # Old API
                self._last_plugin.dockwidget.setWidget(self._last_plugin)

            self._last_plugin.dockwidget.toggleViewAction().setEnabled(True)
            self.main.setCentralWidget(None)

            try:
                # New API
                self._last_plugin.get_widget().is_maximized = False
            except AttributeError:
                # Old API
                self._last_plugin._ismaximized = False

            self.main.restoreState(
                self._state_before_maximizing, version=WINDOW_STATE_VERSION)
            self._state_before_maximizing = None
            try:
                # New API
                self._last_plugin.get_widget().get_focus_widget().setFocus()
            except AttributeError:
                # Old API
                self._last_plugin.get_focus_widget().setFocus()

    def _update_fullscreen_action(self):
        if self._fullscreen_flag:
            icon = self.create_icon('window_nofullscreen')
        else:
            icon = self.create_icon('window_fullscreen')
        self.get_container()._fullscreen_action.setIcon(icon)

    @Slot()
    def toggle_fullscreen(self):
        """
        Toggle option to show the mainwindow in fullscreen or windowed.

        Returns
        -------
        None.

        """
        main = self.main
        if self._fullscreen_flag:
            self._fullscreen_flag = False
            if os.name == 'nt':
                main.setWindowFlags(
                    main.windowFlags()
                    ^ (Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint))
                main.setGeometry(self._saved_normal_geometry)
            main.showNormal()
            if self._maximized_flag:
                main.showMaximized()
        else:
            self._maximized_flag = main.isMaximized()
            self._fullscreen_flag = True
            self._saved_normal_geometry = main.normalGeometry()
            if os.name == 'nt':
                # Due to limitations of the Windows DWM, compositing is not
                # handled correctly for OpenGL based windows when going into
                # full screen mode, so we need to use this workaround.
                # See spyder-ide/spyder#4291.
                main.setWindowFlags(main.windowFlags()
                                    | Qt.FramelessWindowHint
                                    | Qt.WindowStaysOnTopHint)

                screen_number = QDesktopWidget().screenNumber(main)
                if screen_number < 0:
                    screen_number = 0

                r = QApplication.desktop().screenGeometry(screen_number)
                main.setGeometry(
                    r.left() - 1, r.top() - 1, r.width() + 2, r.height() + 2)
                main.showNormal()
            else:
                main.showFullScreen()
        self._update_fullscreen_action()

    @property
    def plugins_menu(self):
        """Expose plugins toggle actions menu."""
        return self.get_container()._plugins_menu

    def create_plugins_menu(self):
        """
        Populate panes menu with the toggle view action of each base plugin.
        """
        order = ['editor', 'ipython_console', 'variable_explorer',
                 'help', 'plots', None, 'explorer', 'outline_explorer',
                 'project_explorer', 'find_in_files', None, 'historylog',
                 'profiler', 'breakpoints', 'pylint', None,
                 'onlinehelp', 'internal_console', None]

        for plugin in self.get_dockable_plugins():
            try:
                # New API
                action = plugin.toggle_view_action
            except AttributeError:
                # Old API
                action = plugin._toggle_view_action

            if action:
                action.setChecked(plugin.dockwidget.isVisible())

            try:
                name = plugin.CONF_SECTION
                pos = order.index(name)
            except ValueError:
                pos = None

            if pos is not None:
                order[pos] = action
            else:
                order.append(action)

        actions = order[:]
        for action in actions:
            if type(action) is not str:
                self.get_container()._plugins_menu.add_action(action)

    @property
    def lock_interface_action(self):
        return self.get_container()._lock_interface_action

    def _update_lock_interface_action(self):
        """
        Helper method to update the locking of panes/dockwidgets and toolbars.

        Returns
        -------
        None.

        """
        container = self.get_container()
        if self._interface_locked:
            icon = self.create_icon('lock')
            text = _('Unlock panes and toolbars')
        else:
            icon = self.create_icon('lock_open')
            text = _('Lock panes and toolbars')
        self.lock_interface_action.setIcon(icon)
        self.lock_interface_action.setText(text)

    def toggle_lock(self, value=None):
        """Lock/Unlock dockwidgets and toolbars."""
        self._interface_locked = (
            not self._interface_locked if value is None else value)
        self.set_conf('panes_locked', self._interface_locked, 'main')
        self._update_lock_interface_action()
        # Apply lock to panes
        for plugin in self.get_dockable_plugins():
            if self._interface_locked:
                if plugin.dockwidget.isFloating():
                    plugin.dockwidget.setFloating(False)

                plugin.dockwidget.remove_title_bar()
            else:
                plugin.dockwidget.set_title_bar()

        # Apply lock to toolbars
        toolbar = self.get_plugin(Plugins.Toolbar)
        if toolbar:
            toolbar.toggle_lock(value=self._interface_locked)
