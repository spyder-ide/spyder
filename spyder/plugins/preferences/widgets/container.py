# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

# Third party imports
from qtpy.QtCore import Signal

# Local imports
from spyder.plugins.preferences.widgets.configdialog import ConfigDialog
from spyder.api.widgets import PluginMainContainer


class PreferencesContainer(PluginMainContainer):
    sig_reset_spyder = Signal()

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

    def reset_spyder(self):
        self.sig_reset_spyder.emit()

    def is_dialog_open(self):
        return self.dialog is not None and self.dialog.isVisible()

    # ---- PluginMainContainer API
    def setup(self, options=None):
        pass

    def update_actions(self):
        pass

    def on_option_update(self, _option, _value):
        pass
