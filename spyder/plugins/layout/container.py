# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""
Layout container.
"""

# Standard library imports
from collections import OrderedDict
import sys

# Third party imports
from qtpy.QtCore import Qt, Slot
from qtpy.QtWidgets import QMessageBox

# Local imports
from spyder.api.exceptions import SpyderAPIError
from spyder.api.translations import _
from spyder.api.widgets.main_container import PluginMainContainer
from spyder.plugins.layout.api import BaseGridLayoutType
from spyder.plugins.layout.layouts import DefaultLayouts
from spyder.plugins.layout.widgets.dialog import (
    LayoutSaveDialog, LayoutSettingsDialog)


class LayoutContainerActions:
    DefaultLayout = 'default_layout_action'
    MatlabLayout = 'matlab_layout_action'
    RStudio = 'rstudio_layout_action'
    HorizontalSplit = 'horizontal_split_layout_action'
    VerticalSplit = 'vertical_split_layout_action'
    SaveLayoutAction = 'save_layout_action'
    ShowLayoutPreferencesAction = 'show_layout_preferences_action'
    ResetLayout = 'reset_layout_action'
    # Needs to have 'Maximize pane' as name to properly register
    # the action shortcut
    MaximizeCurrentDockwidget = 'Maximize pane'
    # Needs to have 'Fullscreen mode' as name to properly register
    # the action shortcut
    Fullscreen = 'Fullscreen mode'
    # Needs to have 'Use next layout' as name to properly register
    # the action shortcut
    NextLayout = 'Use next layout'
    # Needs to have 'Use previous layout' as name to properly register
    # the action shortcut
    PreviousLayout = 'Use previous layout'
    # Needs to have 'Close pane' as name to properly register
    # the action shortcut
    CloseCurrentDockwidget = 'Close pane'
    # Needs to have 'Lock unlock panes' as name to properly register
    # the action shortcut
    LockDockwidgetsAndToolbars = 'Lock unlock panes'


class LayoutPluginMenus:
    PluginsMenu = "plugins_menu"
    LayoutsMenu = 'layouts_menu'


class LayoutContainer(PluginMainContainer):
    """
    Plugin container class that handles the Spyder quick layouts functionality.
    """

    def setup(self):
        # Basic attributes to handle layouts options and dialogs references
        self._spyder_layouts = OrderedDict()
        self._save_dialog = None
        self._settings_dialog = None
        self._layouts_menu = None
        self._current_quick_layout = None

        # Close current dockable plugin
        self._close_dockwidget_action = self.create_action(
            LayoutContainerActions.CloseCurrentDockwidget,
            text=_('Close current pane'),
            icon=self.create_icon('close_pane'),
            triggered=self._plugin.close_current_dockwidget,
            context=Qt.ApplicationShortcut,
            register_shortcut=True,
            shortcut_context='_'
        )

        # Maximize current dockable plugin
        self._maximize_dockwidget_action = self.create_action(
            LayoutContainerActions.MaximizeCurrentDockwidget,
            text=_('Maximize current pane'),
            icon=self.create_icon('maximize'),
            toggled=lambda state: self._plugin.maximize_dockwidget(),
            context=Qt.ApplicationShortcut,
            register_shortcut=True,
            shortcut_context='_')

        # Fullscreen mode
        self._fullscreen_action = self.create_action(
            LayoutContainerActions.Fullscreen,
            text=_('Fullscreen mode'),
            triggered=self._plugin.toggle_fullscreen,
            context=Qt.ApplicationShortcut,
            register_shortcut=True,
            shortcut_context='_')
        if sys.platform == 'darwin':
            self._fullscreen_action.setEnabled(False)
            self._fullscreen_action.setToolTip(_("For fullscreen mode use the "
                                                 "macOS built-in feature"))

        # Lock dockwidgets and toolbars
        self._lock_interface_action = self.create_action(
            LayoutContainerActions.LockDockwidgetsAndToolbars,
            text='',
            triggered=lambda checked:
                self._plugin.toggle_lock(),
            context=Qt.ApplicationShortcut,
            register_shortcut=True,
            shortcut_context='_'
        )

        self._save_layout_action = self.create_action(
            LayoutContainerActions.SaveLayoutAction,
            _("Save current layout"),
            triggered=self.show_save_layout,
            context=Qt.ApplicationShortcut,
            register_shortcut=False,
        )
        self._show_preferences_action = self.create_action(
            LayoutContainerActions.ShowLayoutPreferencesAction,
            text=_("Layout preferences"),
            triggered=self.show_layout_settings,
            context=Qt.ApplicationShortcut,
            register_shortcut=False,
        )
        self._reset_action = self.create_action(
            LayoutContainerActions.ResetLayout,
            text=_('Reset to Spyder default'),
            triggered=self.reset_window_layout,
            register_shortcut=False,
        )

        # Layouts shortcuts actions
        self._toggle_next_layout_action = self.create_action(
            LayoutContainerActions.NextLayout,
            _("Use next layout"),
            triggered=self.toggle_next_layout,
            context=Qt.ApplicationShortcut,
            register_shortcut=True,
            shortcut_context='_')
        self._toggle_previous_layout_action = self.create_action(
            LayoutContainerActions.PreviousLayout,
            _("Use previous layout"),
            triggered=self.toggle_previous_layout,
            context=Qt.ApplicationShortcut,
            register_shortcut=True,
            shortcut_context='_')

        # Layouts menu
        self._layouts_menu = self.create_menu(
            LayoutPluginMenus.LayoutsMenu, _("Window layouts"))

        self._plugins_menu = self.create_menu(
            LayoutPluginMenus.PluginsMenu, _("Panes"))
        self._plugins_menu.setObjectName('checkbox-padding')

    def update_actions(self):
        pass

    def update_layout_menu_actions(self):
        """
        Update layouts menu and layouts related actions.
        """
        menu = self._layouts_menu
        menu.clear_actions()
        names = self.get_conf('names')
        ui_names = self.get_conf('ui_names')
        order = self.get_conf('order')
        active = self.get_conf('active')

        actions = []
        for name in order:
            if name in active:
                if name in self._spyder_layouts:
                    index = name
                    name = self._spyder_layouts[index].get_name()
                else:
                    index = names.index(name)
                    name = ui_names[index]

                # closure required so lambda works with the default parameter
                def trigger(i=index, self=self):
                    return lambda: self.quick_layout_switch(i)

                layout_switch_action = self.create_action(
                    name,
                    text=name,
                    triggered=trigger(),
                    register_shortcut=False,
                    overwrite=True
                )

                actions.append(layout_switch_action)

        for item in actions:
            self.add_item_to_menu(item, menu, section="layouts_section")

        for item in [self._save_layout_action, self._show_preferences_action,
                     self._reset_action]:
            self.add_item_to_menu(item, menu, section="layouts_section_2")

        self._show_preferences_action.setEnabled(len(order) != 0)

    # --- Public API
    # ------------------------------------------------------------------------
    def critical_message(self, title, message):
        """Expose a QMessageBox.critical dialog to be used from the plugin."""
        QMessageBox.critical(self, title, message)

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
        if not issubclass(layout_type, BaseGridLayoutType):
            raise SpyderAPIError(
                "A layout must be a subclass is `BaseGridLayoutType`!")

        layout_id = layout_type.ID
        if layout_id in self._spyder_layouts:
            raise SpyderAPIError(
                "Layout with id `{}` already registered!".format(layout_id))

        layout = layout_type(parent_plugin)
        layout._check_layout_validity()
        self._spyder_layouts[layout_id] = layout
        names = self.get_conf('names')
        ui_names = self.get_conf('ui_names')
        order = self.get_conf('order')
        active = self.get_conf('active')

        if layout_id not in names:
            names.append(layout_id)
            ui_names.append(layout.get_name())
            order.append(layout_id)
            active.append(layout_id)
            self.set_conf('names', names)
            self.set_conf('ui_names', ui_names)
            self.set_conf('order', order)
            self.set_conf('active', active)

    def get_layout(self, layout_id):
        """
        Get a registered layout by its ID.

        Parameters
        ----------
        layout_id : string
            The ID of the layout.

        Raises
        ------
        SpyderAPIError
            If the given id is not found in the registered layouts.

        Returns
        -------
        Instance of a spyder.plugins.layout.api.BaseGridLayoutType subclass
            Layout.
        """
        if layout_id not in self._spyder_layouts:
            raise SpyderAPIError(
                "Layout with id `{}` is not registered!".format(layout_id))

        return self._spyder_layouts[layout_id]

    @Slot()
    def show_save_layout(self):
        """Show the save layout dialog."""
        names = self.get_conf('names')
        ui_names = self.get_conf('ui_names')
        order = self.get_conf('order')
        active = self.get_conf('active')
        dialog_names = [name for name in names
                        if name not in self._spyder_layouts.keys()]
        dlg = self._save_dialog = LayoutSaveDialog(self, dialog_names)

        if dlg.exec_():
            name = dlg.combo_box.currentText()
            if name in self._spyder_layouts:
                QMessageBox.critical(
                    self,
                    _("Error"),
                    _("Layout <b>{0}</b> was defined programatically. "
                      "It is not possible to overwrite programatically "
                      "registered layouts.").format(name)
                )
                return
            if name in names:
                answer = QMessageBox.warning(
                    self,
                    _("Warning"),
                    _("Layout <b>{0}</b> will be overwritten. "
                      "Do you want to continue?").format(name),
                    QMessageBox.Yes | QMessageBox.No,
                )
                index = order.index(name)
            else:
                answer = True
                if None in names:
                    index = names.index(None)
                    names[index] = name
                else:
                    index = len(names)
                    names.append(name)

                order.append(name)

            # Always make active a new layout even if it overwrites an
            # inactive layout
            if name not in active:
                active.append(name)

            if name not in ui_names:
                ui_names.append(name)

            if answer:
                self._plugin.save_current_window_settings(
                    'layout_{}/'.format(index), section='quick_layouts')
                self.set_conf('names', names)
                self.set_conf('ui_names', ui_names)
                self.set_conf('order', order)
                self.set_conf('active', active)

            self.update_layout_menu_actions()

    @Slot()
    def show_layout_settings(self):
        """Layout settings dialog."""
        names = self.get_conf('names')
        ui_names = self.get_conf('ui_names')
        order = self.get_conf('order')
        active = self.get_conf('active')
        read_only = list(self._spyder_layouts.keys())

        dlg = self._settings_dialog = LayoutSettingsDialog(
            self, names, ui_names, order, active, read_only)
        if dlg.exec_():
            self.set_conf('names', dlg.names)
            self.set_conf('ui_names', dlg.ui_names)
            self.set_conf('order', dlg.order)
            self.set_conf('active', dlg.active)

            self.update_layout_menu_actions()

    @Slot()
    def reset_window_layout(self):
        """Reset window layout to default."""
        answer = QMessageBox.warning(
            self,
            _("Warning"),
            _("Window layout will be reset to default settings: "
              "this affects window position, size and dockwidgets.\n"
              "Do you want to continue?"),
            QMessageBox.Yes | QMessageBox.No,
        )

        if answer == QMessageBox.Yes:
            self._plugin.setup_layout(default=True)

    @Slot()
    def toggle_previous_layout(self):
        """Use the previous layout from the layouts list (default + custom)."""
        self.toggle_layout('previous')

    @Slot()
    def toggle_next_layout(self):
        """Use the next layout from the layouts list (default + custom)."""
        self.toggle_layout('next')

    def toggle_layout(self, direction='next'):
        """Change current layout."""
        names = self.get_conf('names')
        order = self.get_conf('order')
        active = self.get_conf('active')

        if len(active) == 0:
            return

        layout_index = []
        for name in order:
            if name in active:
                layout_index.append(names.index(name))

        current_layout = self._current_quick_layout
        dic = {'next': 1, 'previous': -1}

        if current_layout is None:
            # Start from default
            current_layout = names.index(DefaultLayouts.SpyderLayout)

        if current_layout in layout_index:
            current_index = layout_index.index(current_layout)
        else:
            current_index = 0

        new_index = (current_index + dic[direction]) % len(layout_index)
        index_or_layout_id = layout_index[new_index]
        is_layout_id = (
            names[index_or_layout_id] in self._spyder_layouts)

        if is_layout_id:
            index_or_layout_id = names[layout_index[new_index]]

        self.quick_layout_switch(index_or_layout_id)

    def quick_layout_switch(self, index_or_layout_id):
        """
        Switch to quick layout number *index* or *layout id*.

        Parameters
        ----------
        index: int or str
        """
        possible_current_layout = self._plugin.quick_layout_switch(
            index_or_layout_id)

        if possible_current_layout is not None:
            if isinstance(possible_current_layout, int):
                self._current_quick_layout = possible_current_layout
            else:
                names = self.get_conf('names')
                self._current_quick_layout = names.index(
                    possible_current_layout)
