# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""Shortcut configuration page."""

# Third party imports
from qtpy.QtWidgets import QHBoxLayout, QLabel, QMessageBox, QVBoxLayout

# Local imports
from spyder.api.preferences import PluginConfigPage
from spyder.api.translations import _
from spyder.plugins.shortcuts.widgets.table import (
    ShortcutFinder,
    ShortcutsTable,
)
from spyder.utils.icon_manager import ima
from spyder.utils.stylesheet import AppStyle


class ShortcutsConfigPage(PluginConfigPage):
    APPLY_CONF_PAGE_SETTINGS = True

    def setup_page(self):
        # Widgets
        self.table = ShortcutsTable(self)
        finder = ShortcutFinder(self.table, self.table.set_regex)
        reset_btn = self.create_button(
            icon=ima.icon("restart"),
            callback=self.reset_to_default,
            tooltip=_("Reset all shortcuts to default values"),
        )
        top_label = QLabel(
            _("Customize a shortcut by double-clicking on its entry below.")
        )

        # Widget setup
        self.table.finder = finder
        self.table.set_shortcut_data(self.plugin.get_shortcut_data())
        self.table.load_shortcuts()
        self.table.finder.setPlaceholderText(_("Type to search"))
        top_label.setWordWrap(True)

        # Layout
        hlayout = QHBoxLayout()
        hlayout.addWidget(finder)
        hlayout.addWidget(reset_btn)

        vlayout = QVBoxLayout()
        vlayout.addWidget(top_label)
        vlayout.addWidget(self.table)
        vlayout.addSpacing(AppStyle.MarginSize)
        vlayout.addLayout(hlayout)
        self.setLayout(vlayout)

        self.setTabOrder(self.table, finder)
        self.setTabOrder(finder, reset_btn)

        # Signals
        self.table.proxy_model.dataChanged.connect(
            lambda i1, i2, roles, opt='', sect='': self.has_been_modified(
                sect, opt))

    def check_settings(self):
        self.table.check_shortcuts()

    def reset_to_default(self, force=False):
        """Reset all shortcuts to default values after confirmation."""
        if not force:
            reset = QMessageBox.warning(
                self,
                _("Reset all shortcuts"),
                _(
                    "Do you want to reset all shortcuts to their default "
                    "values?"
                ),
                QMessageBox.Yes | QMessageBox.No,
            )

            if reset == QMessageBox.No:
                return

        self.plugin.reset_shortcuts()
        self.plugin.apply_shortcuts()
        self.table.load_shortcuts()
        self.load_from_conf()
        self.set_modified(False)

    def apply_settings(self, options):
        self.table.save_shortcuts()
        self.plugin.apply_shortcuts()
        self.plugin.apply_conf(options)
