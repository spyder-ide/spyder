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
import logging
import os

# Third party imports
from qtpy.QtCore import Qt, QByteArray, QSize, QPoint, Slot
from qtpy.QtWidgets import QApplication, QDesktopWidget

# Local imports
from spyder.api.exceptions import SpyderAPIError
from spyder.api.plugins import (
    Plugins, DockablePlugins, SpyderDockablePlugin, SpyderPluginV2)
from spyder.api.plugin_registration.decorators import (
    on_plugin_available, on_plugin_teardown)
from spyder.api.plugin_registration.registry import PLUGIN_REGISTRY
from spyder.api.translations import _
from spyder.api.utils import get_class_values
from spyder.plugins.mainmenu.api import ApplicationMenus, ViewMenuSections
from spyder.plugins.layout.container import (
    LayoutContainer, LayoutContainerActions, LayoutPluginMenus)
from spyder.plugins.layout.layouts import (DefaultLayouts,
                                           HorizontalSplitLayout,
                                           MatlabLayout, RLayout,
                                           SpyderLayout, VerticalSplitLayout)
from spyder.plugins.preferences.widgets.container import PreferencesActions
from spyder.plugins.toolbar.api import (
    ApplicationToolbars, MainToolbarSections)
from spyder.py3compat import qbytearray_to_str  # FIXME:


# For logging
logger = logging.getLogger(__name__)

# Number of default layouts available
DEFAULT_LAYOUTS = get_class_values(DefaultLayouts)

# ----------------------------------------------------------------------------
# ---- Window state version passed to saveState/restoreState.
# ----------------------------------------------------------------------------
# This defines the layout version used by different Spyder releases. In case
# there's a need to reset the layout when moving from one release to another,
# please increase the number below in integer steps, e.g. from 1 to 2, and
# leave a mention below explaining what prompted the change.
#
# The current versions are:
#
# * Spyder 4: Version 0 (it was the default).
# * Spyder 5.0.0 to 5.0.5: Version 1 (a bump was required due to the new API).
# * Spyder 5.1.0: Version 2 (a bump was required due to the migration of
#                            Projects to the new API).
# * Spyder 5.2.0: Version 3 (a bump was required due to the migration of
#                            IPython Console to the new API)
WINDOW_STATE_VERSION = 3


class Layout(SpyderPluginV2):
    """
    Layout manager plugin.
    """
    NAME = "layout"
    CONF_SECTION = "quick_layouts"
    REQUIRES = [Plugins.All]  # Uses wildcard to require all plugins
    CONF_FILE = False
    CONTAINER_CLASS = LayoutContainer
    CAN_BE_DISABLED = False

    # ---- SpyderDockablePlugin API
    # -------------------------------------------------------------------------
    @staticmethod
    def get_name():
        return _("Layout")

    def get_description(self):
        return _("Layout manager")

    def get_icon(self):
        return self.create_icon("history")  # FIXME:

    def on_initialize(self):
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
        self._interface_locked = self.get_conf('panes_locked', section='main')

        # Register default layouts
        self.register_layout(self, SpyderLayout)
        self.register_layout(self, RLayout)
        self.register_layout(self, MatlabLayout)
        self.register_layout(self, HorizontalSplitLayout)
        self.register_layout(self, VerticalSplitLayout)

        self._update_fullscreen_action()

    @on_plugin_available(plugin=Plugins.MainMenu)
    def on_main_menu_available(self):
        mainmenu = self.get_plugin(Plugins.MainMenu)
        container = self.get_container()
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
                section=ViewMenuSections.Layout,
                before_section=ViewMenuSections.Bottom)
        # Add fullscreen action to View application menu
        mainmenu.add_item_to_application_menu(
            container._fullscreen_action,
            menu_id=ApplicationMenus.View,
            section=ViewMenuSections.Bottom)

    @on_plugin_available(plugin=Plugins.Toolbar)
    def on_toolbar_available(self):
        container = self.get_container()
        toolbars = self.get_plugin(Plugins.Toolbar)
        # Add actions to Main application toolbar
        toolbars.add_item_to_application_toolbar(
            container._maximize_dockwidget_action,
            toolbar_id=ApplicationToolbars.Main,
            section=MainToolbarSections.ApplicationSection,
            before=PreferencesActions.Show
        )

    @on_plugin_teardown(plugin=Plugins.MainMenu)
    def on_main_menu_teardown(self):
        mainmenu = self.get_plugin(Plugins.MainMenu)
        # Remove Panes related actions from the View application menu
        panes_items = [
            LayoutPluginMenus.PluginsMenu,
            LayoutContainerActions.LockDockwidgetsAndToolbars,
            LayoutContainerActions.CloseCurrentDockwidget,
            LayoutContainerActions.MaximizeCurrentDockwidget]
        for panes_item in panes_items:
            mainmenu.remove_item_from_application_menu(
                panes_item,
                menu_id=ApplicationMenus.View)
        # Remove layouts menu from the View application menu
        layout_items = [
            LayoutPluginMenus.LayoutsMenu,
            LayoutContainerActions.NextLayout,
            LayoutContainerActions.PreviousLayout]
        for layout_item in layout_items:
            mainmenu.remove_item_from_application_menu(
                layout_item,
                menu_id=ApplicationMenus.View)
        # Remove fullscreen action from the View application menu
        mainmenu.remove_item_from_application_menu(
            LayoutContainerActions.Fullscreen,
            menu_id=ApplicationMenus.View)

    @on_plugin_teardown(plugin=Plugins.Toolbar)
    def on_toolbar_teardown(self):
        toolbars = self.get_plugin(Plugins.Toolbar)

        # Remove actions from the Main application toolbar
        toolbars.remove_item_from_application_toolbar(
            LayoutContainerActions.MaximizeCurrentDockwidget,
            toolbar_id=ApplicationToolbars.Main
        )

    def before_mainwindow_visible(self):
        # Update layout menu
        self.update_layout_menu_actions()
        # Setup layout
        self.setup_layout(default=False)

    def on_mainwindow_visible(self):
        # Populate `Panes > View` menu.
        # This **MUST** be done before restoring the last visible plugins, so
        # that works as expected.
        self.create_plugins_menu()

        # Restore last visible plugins.
        # This **MUST** be done before running on_mainwindow_visible for the
        # other plugins so that the user doesn't experience sudden jumps in the
        # interface.
        self.restore_visible_plugins()

        # Update panes and toolbars lock status
        self.toggle_lock(self._interface_locked)

    # ---- Private API
    # -------------------------------------------------------------------------
    def _get_internal_dockable_plugins(self):
        """Get the list of internal dockable plugins"""
        return get_class_values(DockablePlugins)

    def _update_fullscreen_action(self):
        if self._fullscreen_flag:
            icon = self.create_icon('window_nofullscreen')
        else:
            icon = self.create_icon('window_fullscreen')
        self.get_container()._fullscreen_action.setIcon(icon)

    def _update_lock_interface_action(self):
        """
        Helper method to update the locking of panes/dockwidgets and toolbars.

        Returns
        -------
        None.
        """
        if self._interface_locked:
            icon = self.create_icon('drag_dock_widget')
            text = _('Unlock panes and toolbars')
        else:
            icon = self.create_icon('lock')
            text = _('Lock panes and toolbars')
        self.lock_interface_action.setIcon(icon)
        self.lock_interface_action.setText(text)

    # ---- Helper methods
    # -------------------------------------------------------------------------
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

    # ---- Layout handling
    # -------------------------------------------------------------------------
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

    def register_custom_layouts(self):
        """Register custom layouts provided by external plugins."""
        for plugin_name in PLUGIN_REGISTRY.external_plugins:
            plugin_instance = self.get_plugin(plugin_name)
            if hasattr(plugin_instance, 'CUSTOM_LAYOUTS'):
                if isinstance(plugin_instance.CUSTOM_LAYOUTS, list):
                    for custom_layout in plugin_instance.CUSTOM_LAYOUTS:
                        self.register_layout(self, custom_layout)
                else:
                    logger.info(
                        f'Unable to load custom layouts for plugin '
                        f'{plugin_name}. Expecting a list of layout classes '
                        f'but got {plugin_instance.CUSTOM_LAYOUTS}.'
                    )

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

    def update_layout_menu_actions(self):
        self.get_container().update_layout_menu_actions()

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
            self.setup_default_layouts(DefaultLayouts.SpyderLayout, settings)

            # Now that the initial setup is done, copy the window settings,
            # except for the hexstate in the quick layouts sections for the
            # default layouts.
            # Order and name of the default layouts is found in config.py
            section = 'quick_layouts'
            get_func = self.get_conf_default if default else self.get_conf
            order = get_func('order', section=section)

            # Restore the original defaults if reset layouts is called
            if default:
                self.set_conf('active', order, section)
                self.set_conf('order', order, section)
                self.set_conf('names', order, section)
                self.set_conf('ui_names', order, section)

            for index, _name, in enumerate(order):
                prefix = 'layout_{0}/'.format(index)
                self.save_current_window_settings(prefix, section,
                                                  none_state=True)

            # Store the initial layout as the default in spyder
            prefix = 'layout_default/'
            section = 'quick_layouts'
            self.save_current_window_settings(prefix, section, none_state=True)
            self._current_quick_layout = DefaultLayouts.SpyderLayout

        self.set_window_settings(*settings)

    def setup_default_layouts(self, layout_id, settings):
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

        # Layout selection
        layout = self.get_layout(layout_id)

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

    def quick_layout_switch(self, index_or_layout_id):
        """
        Switch to quick layout.

        Using a number *index* or a registered layout id *layout_id*.

        Parameters
        ----------
        index_or_layout_id: int or str
        """
        section = 'quick_layouts'
        container = self.get_container()
        try:
            settings = self.load_window_settings(
                'layout_{}/'.format(index_or_layout_id), section=section)
            (hexstate, window_size, prefs_dialog_size, pos, is_maximized,
             is_fullscreen) = settings

            # The defaults layouts will always be regenerated unless there was
            # an overwrite, either by rewriting with same name, or by deleting
            # and then creating a new one
            if hexstate is None:
                # The value for hexstate shouldn't be None for a custom saved
                # layout (ie, where the index is greater than the number of
                # defaults).  See spyder-ide/spyder#6202.
                if index_or_layout_id not in DEFAULT_LAYOUTS:
                    container.critical_message(
                        _("Warning"),
                        _("Error opening the custom layout.  Please close"
                          " Spyder and try again.  If the issue persists,"
                          " then you must use 'Reset to Spyder default' "
                          "from the layout menu."))
                    return
                self.setup_default_layouts(index_or_layout_id, settings)
            else:
                self.set_window_settings(*settings)
        except cp.NoOptionError:
            try:
                layout = self.get_layout(index_or_layout_id)
                layout.set_main_window_layout(
                    self.main, self.get_dockable_plugins())
                self.main.sig_layout_setup_ready.emit(layout)
            except SpyderAPIError:
                container.critical_message(
                    _("Warning"),
                    _("Quick switch layout #%s has not yet "
                      "been defined.") % str(index_or_layout_id))

        # Make sure the flags are correctly set for visible panes
        for plugin in self.get_dockable_plugins():
            try:
                # New API
                action = plugin.toggle_view_action
            except AttributeError:
                # Old API
                action = plugin._toggle_view_action
            action.setChecked(plugin.dockwidget.isVisible())

        return index_or_layout_id

    def load_window_settings(self, prefix, default=False, section='main'):
        """
        Load window layout settings from userconfig-based configuration with
        *prefix*, under *section*.

        Parameters
        ----------
        default: bool
            if True, do not restore inner layout.
        """
        get_func = self.get_conf_default if default else self.get_conf
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
            pos = self.get_conf_default(prefix + 'position', section)

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
            self.main.saveState(version=WINDOW_STATE_VERSION)
        )
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
                version=WINDOW_STATE_VERSION
            )

            # Check layout validity. Spyder 4 and below use the version 0
            # state (default), whereas Spyder 5 will use version 1 state.
            # For more info see the version argument for
            # QMainWindow.restoreState:
            # https://doc.qt.io/qt-5/qmainwindow.html#restoreState
            if not hexstate_valid:
                self.main.setUpdatesEnabled(True)
                self.setup_layout(default=True)
                return

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

        It saves config with *prefix* in the userconfig-based,
        configuration under *section*.
        """
        # Use current size and position when saving window settings.
        # Fixes spyder-ide/spyder#13882
        win_size = self.main.size()
        pos = self.main.pos()
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

    # ---- Maximize, close, switch to dockwidgets/plugins
    # -------------------------------------------------------------------------
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
                version=WINDOW_STATE_VERSION
            )
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
                self._last_plugin.get_widget().set_maximized_state(True)
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
                self._last_plugin.get_widget().set_maximized_state(False)
            except AttributeError:
                # Old API
                self._last_plugin._ismaximized = False

            self.main.restoreState(
                self._state_before_maximizing, version=WINDOW_STATE_VERSION
            )
            self._state_before_maximizing = None
            try:
                # New API
                self._last_plugin.get_widget().get_focus_widget().setFocus()
            except AttributeError:
                # Old API
                self._last_plugin.get_focus_widget().setFocus()

    def unmaximize_dockwidget(self):
        """Unmaximize any dockable plugin."""
        if self.maximize_action.isChecked():
            self.maximize_action.setChecked(False)

    def unmaximize_other_dockwidget(self, plugin_instance):
        """
        Unmaximize the currently maximized plugin, if not `plugin_instance`.
        """
        last_plugin = self.get_last_plugin()
        is_maximized = False

        if last_plugin is not None:
            try:
                # New API
                is_maximized = (
                    last_plugin.get_widget().get_maximized_state()
                )
            except AttributeError:
                # Old API
                is_maximized = last_plugin._ismaximized

        if (
            last_plugin is not None
            and is_maximized
            and last_plugin is not plugin_instance
        ):
            self.unmaximize_dockwidget()

    def switch_to_plugin(self, plugin, force_focus=None):
        """
        Switch to `plugin`.

        Notes
        -----
        This operation unmaximizes the current plugin (if any), raises
        this plugin to view (if it's hidden) and gives it focus (if
        possible).
        """
        last_plugin = self.get_last_plugin()

        try:
            # New API
            if (
                last_plugin is not None
                and last_plugin.get_widget().get_maximized_state()
                and last_plugin is not plugin
            ):
                if self.maximize_action.isChecked():
                    self.maximize_action.setChecked(False)
                else:
                    self.maximize_action.setChecked(True)
        except AttributeError:
            # Old API
            if (
                last_plugin is not None
                and last_plugin._ismaximized
                and last_plugin is not plugin
            ):
                if self.maximize_action.isChecked():
                    self.maximize_action.setChecked(False)
                else:
                    self.maximize_action.setChecked(True)

        try:
            # New API
            if not plugin.toggle_view_action.isChecked():
                plugin.toggle_view_action.setChecked(True)
                plugin.get_widget().is_visible = False
        except AttributeError:
            # Old API
            if not plugin._toggle_view_action.isChecked():
                plugin._toggle_view_action.setChecked(True)
                plugin._widget._is_visible = False

        try:
            # New API
            plugin.change_visibility(True, force_focus=force_focus)
        except AttributeError:
            # Old API
            plugin._visibility_changed(True)

    # ---- Menus and actions
    # -------------------------------------------------------------------------
    @Slot()
    def toggle_fullscreen(self):
        """
        Toggle option to show the mainwindow in fullscreen or windowed.
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
                action.action_id = f'switch to {plugin.CONF_SECTION}'

            if action:
                # Plugins that fail their compatibility checks don't have a
                # dockwidget. So, we need to skip them from the plugins menu.
                # Fixes spyder-ide/spyder#21074
                if plugin.dockwidget is None:
                    continue
                else:
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

    def toggle_lock(self, value=None):
        """Lock/Unlock dockwidgets and toolbars."""
        self._interface_locked = (
            not self._interface_locked if value is None else value)
        self.set_conf('panes_locked', self._interface_locked, 'main')
        self._update_lock_interface_action()
        # Apply lock to panes
        for plugin in self.get_dockable_plugins():
            # Plugins that fail their compatibility checks don't have a
            # dockwidget. So, we need to skip them from the code below.
            # Fixes spyder-ide/spyder#21074
            if plugin.dockwidget is None:
                continue

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

    # ---- Visible dockable plugins
    # -------------------------------------------------------------------------
    def restore_visible_plugins(self):
        """
        Restore dockable plugins that were visible during the previous session.
        """
        logger.info("Restoring visible plugins from the previous session")
        visible_plugins = self.get_conf('last_visible_plugins', default=[])

        # This should only be necessary the first time this method is run
        if not visible_plugins:
            visible_plugins = [Plugins.IPythonConsole, Plugins.Help,
                               Plugins.Editor]

        # Restore visible plugins
        for plugin in visible_plugins:
            plugin_class = self.get_plugin(plugin, error=False)
            if (
                plugin_class
                # This check is necessary for spyder-ide/spyder#21074
                and plugin_class.dockwidget is not None
                and plugin_class.dockwidget.isVisible()
            ):
                plugin_class.dockwidget.raise_()

    def save_visible_plugins(self):
        """Save visible plugins."""
        logger.debug("Saving visible plugins to config system")

        visible_plugins = []
        for plugin in self.get_dockable_plugins():
            try:
                # New API
                if plugin.get_widget().is_visible:
                    visible_plugins.append(plugin.NAME)
            except AttributeError:
                # Old API
                if plugin._isvisible:
                    visible_plugins.append(plugin.NAME)

        self.set_conf('last_visible_plugins', visible_plugins)

    # ---- Tabify plugins
    # -------------------------------------------------------------------------
    def tabify_plugins(self, first, second):
        """Tabify plugin dockwigdets."""
        self.main.tabifyDockWidget(first.dockwidget, second.dockwidget)

    def tabify_plugin(self, plugin, default=None):
        """
        Tabify `plugin` using the list of possible TABIFY options.

        Only do this if the dockwidget does not have more dockwidgets
        in the same position and if the plugin is using the New API.
        """
        def tabify_helper(plugin, next_to_plugins):
            for next_to_plugin in next_to_plugins:
                try:
                    self.tabify_plugins(next_to_plugin, plugin)
                    break
                except SpyderAPIError as err:
                    logger.error(err)

        # If TABIFY not defined use the [default]
        tabify = getattr(plugin, 'TABIFY', [default])
        if not isinstance(tabify, list):
            next_to_plugins = [tabify]
        else:
            next_to_plugins = tabify

        # Check if TABIFY is not a list with None as unique value or a default
        # list
        if tabify in [[None], []]:
            return False

        # Get the actual plugins from their names
        next_to_plugins = [self.get_plugin(p) for p in next_to_plugins]

        if plugin.get_conf('first_time', True):
            # This tabifies external and internal plugins that are loaded for
            # the first time, and internal ones that are not part of the
            # default layout.
            if (
                isinstance(plugin, SpyderDockablePlugin)
                and plugin.NAME != Plugins.Console
            ):
                logger.info(
                    f"Tabifying {plugin.NAME} plugin for the first time next "
                    f"to {next_to_plugins}"
                )
                tabify_helper(plugin, next_to_plugins)

                # Show external plugins
                if plugin.NAME in PLUGIN_REGISTRY.external_plugins:
                    plugin.get_widget().toggle_view(True)

            plugin.set_conf('enable', True)
            plugin.set_conf('first_time', False)
        else:
            # This is needed to ensure that, when switching to a different
            # layout, any plugin (external or internal) not part of its
            # declared areas is tabified as expected.
            # Note: Check if `plugin` has no other dockwidgets in the same
            # position before proceeding.
            if not bool(self.main.tabifiedDockWidgets(plugin.dockwidget)):
                logger.info(f"Tabifying {plugin.NAME} plugin")
                tabify_helper(plugin, next_to_plugins)

        return True

    def tabify_new_plugins(self):
        """
        Tabify new dockable plugins, i.e. plugins that were not part of the
        interface in the last session.

        Notes
        -----
        This is only necessary the first time a plugin is loaded. Afterwards,
        the plugin's placement is recorded in the window hexstate, which is
        loaded in the next session.
        """
        # Detect if a new dockable internal plugin hasn't been added to the
        # DockablePlugins enum and raise an error if that's the case.
        for plugin in self.get_dockable_plugins():
            if (
                plugin.NAME in PLUGIN_REGISTRY.internal_plugins
                and plugin.NAME not in self._get_internal_dockable_plugins()
            ):
                raise SpyderAPIError(
                    f"Plugin {plugin.NAME} is a new dockable plugin but it "
                    f"hasn't been added to the DockablePlugins enum. Please "
                    f"do that to avoid this error."
                )

        # If this is the first time Spyder runs, then we don't need to go
        # beyond this point because all plugins are tabified in the
        # set_main_window_layout method of any layout.
        if self._first_spyder_run:
            # Save the list of internal dockable plugins to compare it with
            # the current ones during the next session.
            self.set_conf(
                'internal_dockable_plugins',
                self._get_internal_dockable_plugins()
            )
            return

        logger.debug("Tabifying new plugins")

        # Get the list of internal dockable plugins that were present in the
        # last session to decide which ones need to be tabified.
        last_internal_dockable_plugins = self.get_conf(
            'internal_dockable_plugins',
            default=self._get_internal_dockable_plugins()
        )

        # Tabify new internal plugins
        for plugin_name in self._get_internal_dockable_plugins():
            if plugin_name not in last_internal_dockable_plugins:
                plugin = self.get_plugin(plugin_name, error=False)
                if plugin:
                    self.tabify_plugin(plugin, Plugins.Console)

        # Tabify new external plugins
        for plugin in self.get_dockable_plugins():
            if (
                plugin.NAME in PLUGIN_REGISTRY.external_plugins
                and plugin.get_conf('first_time', True)
            ):
                self.tabify_plugin(plugin, Plugins.Console)
