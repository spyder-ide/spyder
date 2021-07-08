# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

# Standard library imports
import sys

# Third party imports
from qtpy.QtCore import Signal
from qtpy.QtWidgets import QAction

# Local imports
from spyder.api.translations import get_translation
from spyder.api.widgets.main_container import PluginMainContainer
from spyder.plugins.preferences.widgets.configdialog import ConfigDialog


# Localization
_ = get_translation('spyder')


class PreferencesActions:
    Show = 'show_action'
    Reset = 'reset_action'


class PreferencesContainer(PluginMainContainer):
    sig_reset_preferences_requested = Signal()
    """Request a reset of preferences."""

    sig_show_preferences_requested = Signal()
    """Request showing preferences."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.dialog = None
        self.dialog_index = None

    def create_dialog(self, config_pages, config_tabs, prefs_dialog_size,
                      main_window):

        def _dialog_finished(result_code):
            """Restore preferences dialog instance variable."""
            self.dialog = None

        if self.dialog is None:
            # TODO: Remove all references to main window
            dlg = ConfigDialog(main_window)
            dlg.setStyleSheet("QTabWidget::tab-bar {"
                                "alignment: left;}")
            self.dialog = dlg

            if prefs_dialog_size is not None:
                dlg.resize(prefs_dialog_size)

            for page_name in config_pages:
                (api, ConfigPage, plugin) = config_pages[page_name]
                if api == 'new':
                    page = ConfigPage(plugin, dlg)
                    page.initialize()
                    for Tab in config_tabs.get(page_name, []):
                        page.add_tab(Tab)
                    dlg.add_page(page)
                else:
                    page = plugin._create_configwidget(dlg, main_window)
                    for Tab in config_tabs.get(page_name, []):
                        page.add_tab(Tab)
                    dlg.add_page(page)

            if self.dialog_index is not None:
                dlg.set_current_index(self.dialog_index)

            dlg.show()
            dlg.check_all_settings()

            dlg.finished.connect(_dialog_finished)
            dlg.pages_widget.currentChanged.connect(
                self.__preference_page_changed)
            dlg.size_change.connect(main_window.set_prefs_size)
        else:
            self.dialog.show()
            self.dialog.activateWindow()
            self.dialog.raise_()
            self.dialog.setFocus()

    def __preference_page_changed(self, index):
        """Preference page index has changed."""
        self.dialog_index = index

    def reset(self):
        self.sig_reset_preferences_requested.emit()

    def is_dialog_open(self):
        return self.dialog is not None and self.dialog.isVisible()

    def show_preferences(self):
        """Show preferences."""
        self.sig_show_preferences_requested.emit()

    # ---- PluginMainContainer API
    def setup(self):
        self.show_action = self.create_action(
            PreferencesActions.Show,
            _("Preferences"),
            icon=self.create_icon('configure'),
            triggered=self.show_preferences
        )

        if sys.platform == 'darwin':
            self.show_action.setMenuRole(QAction.PreferencesRole)

        self.reset_action = self.create_action(
            PreferencesActions.Reset,
            _("Reset Spyder to factory defaults"),
            triggered=self.reset,
            icon=self.create_icon('reset_factory_defaults'),
        )

    def update_actions(self):
        pass
