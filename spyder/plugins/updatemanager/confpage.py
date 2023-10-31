# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""
General entry in Preferences.

For historical reasons (dating back to Spyder 2) the main class here is called
`MainConfigPage` and its associated entry in our config system is called
`main`.
"""

from qtpy.QtWidgets import QGroupBox, QVBoxLayout

from spyder.config.base import _
from spyder.api.preferences import PluginConfigPage


class UpdateManagerConfigPage(PluginConfigPage):
    def setup_page(self):
        """Setup config page widgets and options."""
        updates_group = QGroupBox(_("Updates"))
        check_updates = self.create_checkbox(
            _("Check for updates on startup"),
            'check_updates_on_startup'
        )
        stable_only = self.create_checkbox(
            _("Check for stable releases only"),
            'check_stable_only'
        )

        updates_layout = QVBoxLayout()
        updates_layout.addWidget(check_updates)
        updates_layout.addWidget(stable_only)
        updates_group.setLayout(updates_layout)

        vlayout = QVBoxLayout()
        vlayout.addWidget(updates_group)
        vlayout.addStretch(1)
        self.setLayout(vlayout)
