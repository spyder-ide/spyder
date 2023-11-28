# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""
Update manager Preferences configuration page.
"""

from qtpy.QtWidgets import QGroupBox, QVBoxLayout

from spyder.config.base import _
from spyder.api.preferences import PluginConfigPage


class UpdateManagerConfigPage(PluginConfigPage):
    def setup_page(self):
        """Setup config page widgets and options."""
        updates_group = QGroupBox(_("Updates"))
        check_update_cb = self.create_checkbox(
            _("Check for updates on startup"),
            'check_updates_on_startup'
        )
        stable_only_cb = self.create_checkbox(
            _("Check for stable releases only"),
            'check_stable_only'
        )

        updates_layout = QVBoxLayout()
        updates_layout.addWidget(check_update_cb)
        updates_layout.addWidget(stable_only_cb)
        updates_group.setLayout(updates_layout)

        vlayout = QVBoxLayout()
        vlayout.addWidget(updates_group)
        vlayout.addStretch(1)
        self.setLayout(vlayout)
