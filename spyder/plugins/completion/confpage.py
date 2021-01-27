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

        providers_layout = QGridLayout()
        providers_group = QGroupBox(_("Completion providers"))
        for i, (provider_key, provider_name) in enumerate(self.providers):
            cb = newcb(_('Enable {0} provider').format(provider_name),
                       ('enabled_providers', provider_key), default=True)
            providers_layout.addWidget(cb, i, 0)
            self.provider_checkboxes.append(cb)

        providers_group.setLayout(providers_layout)

        completions_wait_for_ms = self.create_spinbox(
            _("Time to wait for all providers to return (ms):"), None,
            'completions_wait_for_ms', min_=0, max_=5000, step=10,
            tip=_("Beyond this timeout, "
                "the first available provider will be returned"))

        advanced_layout = QVBoxLayout()
        advanced_group = QGroupBox(_('Advanced settings'))
        advanced_layout.addWidget(completions_wait_for_ms)
        advanced_group.setLayout(advanced_layout)

        layout = QVBoxLayout()
        layout.addWidget(providers_group)
        layout.addWidget(advanced_group)
        layout.addStretch(1)
        self.setLayout(layout)
