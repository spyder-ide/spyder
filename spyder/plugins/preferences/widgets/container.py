# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

# Third party imports
from qtpy.QtCore import Signal
from qtpy.QtWidgets import QAction
from qtpy import PYSIDE2, PYSIDE6

# Local imports
from spyder.api.plugin_registration.registry import PreferencesAdapter
from spyder.api.translations import _
from spyder.api.widgets.main_container import PluginMainContainer
from spyder.plugins.preferences import MOST_IMPORTANT_PAGES
from spyder.plugins.preferences.api import PreferencesActions
from spyder.plugins.preferences.widgets.configdialog import ConfigDialog


class PreferencesContainer(PluginMainContainer):
    sig_reset_preferences_requested = Signal()
    """Request a reset of preferences."""

    sig_show_preferences_requested = Signal()
    """Request showing preferences."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.dialog = None
        self.dialog_index = 0
        self._dialog_size = None

    def create_dialog(self, config_pages, config_tabs, main_window):

        def _dialog_finished(result_code):
            """Restore preferences dialog instance variable."""
            if PYSIDE2 or PYSIDE6:
                self.dialog.disconnect(None, None, None)
            else:
                self.dialog.disconnect()

            self.dialog = None

        if self.dialog is None:
            # TODO: Remove all references to main window
            dlg = ConfigDialog(main_window)
            self.dialog = dlg

            if self._dialog_size is None:
                self._dialog_size = self.get_conf('dialog_size')
            dlg.resize(*self._dialog_size)

            for page_name in config_pages:
                # Add separator before the Plugins page
                if page_name == PreferencesAdapter.NAME:
                    dlg.add_separator()

                (api, ConfigPage, plugin) = config_pages[page_name]
                if api == 'new':
                    page = ConfigPage(plugin, dlg)
                    page.initialize()
                    for Tab in config_tabs.get(page_name, []):
                        page._add_tab(Tab)
                    dlg.add_page(page)
                else:
                    page = plugin._create_configwidget(dlg, main_window)
                    for Tab in config_tabs.get(page_name, []):
                        page._add_tab(Tab)
                    dlg.add_page(page)

                # Add separator after the last element of the most important
                # pages
                if page_name == MOST_IMPORTANT_PAGES[-1]:
                    dlg.add_separator()

            dlg.set_current_index(self.dialog_index)
            dlg.show()
            dlg.check_all_settings()

            dlg.finished.connect(_dialog_finished)
            dlg.pages_widget.currentChanged.connect(
                self.__preference_page_changed)
            dlg.sig_size_changed.connect(self._set_dialog_size)
            dlg.sig_reset_preferences_requested.connect(
                self.sig_reset_preferences_requested)
        else:
            self.dialog.resize(*self._dialog_size)
            self.dialog.show()
            self.dialog.activateWindow()
            self.dialog.raise_()
            self.dialog.setFocus()

    # ---- Private API
    def __preference_page_changed(self, index):
        """Preference page index has changed."""
        self.dialog_index = index

    def _set_dialog_size(self, size):
        self._dialog_size = (size.width(), size.height())

    # ---- Public API
    def is_preferences_open(self):
        """Check if preferences is open."""
        return self.dialog is not None and self.dialog.isVisible()

    def close_preferences(self):
        """Close preferences"""
        if self.dialog is not None:
            self.dialog.close()

    def show_preferences(self):
        """Show preferences."""
        self.sig_show_preferences_requested.emit()

    # ---- PluginMainContainer API
    def setup(self):
        self.show_action = self.create_action(
            PreferencesActions.Show,
            _("Preferences"),
            icon=self.create_icon('configure'),
            triggered=self.show_preferences,
            menurole=QAction.PreferencesRole
        )

        self.reset_action = self.create_action(
            PreferencesActions.Reset,
            _("Reset Spyder to factory defaults"),
            triggered=self.sig_reset_preferences_requested,
            icon=self.create_icon('reset_factory_defaults'),
        )

    def update_actions(self):
        pass

    def on_close(self):
        # Save dialog size to use it in the next Spyder session
        if isinstance(self._dialog_size, tuple):
            self.set_conf('dialog_size', self._dialog_size)
