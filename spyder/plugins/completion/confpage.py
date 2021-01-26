# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""Spyder completion plugin configuration page."""

# Third party imports
from qtpy.QtWidgets import QGroupBox, QVBoxLayout, QCheckBox, QGridLayout

# Local imports
from spyder.config.base import _
from spyder.utils import icon_manager as ima
from spyder.api.preferences import PluginConfigPage


class CompletionConfigPage(PluginConfigPage):
    def __init__(self, plugin, parent, providers=[]):
        super().__init__(plugin, parent)
        self.providers = providers

    def setup_page(self):
        newcb = self.create_checkbox
        self.provider_checkboxes = []
        # enabled_providers = self.get_option('enabled_providers')

        providers_layout = QGridLayout()
        providers_group = QGroupBox(_("Completion providers"))
        for i, (provider_key, provider_name) in enumerate(self.providers):
            # provider_status = enabled_providers.get(provider_key, True)
            cb = newcb(_('Enable {0} provider').format(provider_name),
                       ('enabled_providers', provider_key), default=True)
            # cb = QCheckBox(_('Enable {0} provider').format(provider_name))
            # cb.setChecked(provider_status)
            # cb.clicked.connect(
            #     lambda _: self.has_been_modified('enabled_providers'))
            providers_layout.addWidget(cb, i, 0)
            self.provider_checkboxes.append(cb)

        providers_group.setLayout(providers_layout)
        layout = QVBoxLayout()
        layout.addWidget(providers_group)
        layout.addStretch(1)
        self.setLayout(layout)

    def apply_settings(self, options):
        enabled_providers = self.get_option('enabled_providers')
        print(options)
        print(enabled_providers)
