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
from spyder.utils.icon_manager import ima
from spyder.api.preferences import PluginConfigPage


class CompletionConfigPage(PluginConfigPage):
    def __init__(self, plugin, parent, providers=[]):
        super().__init__(plugin, parent)
        self.providers = providers

    def setup_page(self):
        newcb = self.create_checkbox

        # -------------------- Plugin status group -----------------------------
        plugin_state_group = QGroupBox(_('Plugin status'))
        plugin_state_layout = QVBoxLayout()
        self.completion_box = newcb(
            _("Enable code completion and linting in the editor"),
            'enable'
        )
        plugin_state_layout.addWidget(self.completion_box)
        plugin_state_group.setLayout(plugin_state_layout)

        self.completion_box.toggled.connect(self.enable_disable_plugin)

        # ------------------- Providers status group ---------------------------
        self.provider_checkboxes = []
        providers_layout = QGridLayout()
        self.providers_group = QGroupBox(_("Providers"))
        for i, (provider_key, provider_name) in enumerate(self.providers):
            cb = newcb(_('Enable {0} provider').format(provider_name),
                       ('enabled_providers', provider_key), default=True)
            providers_layout.addWidget(cb, i, 0)
            self.provider_checkboxes.append(cb)

        self.providers_group.setLayout(providers_layout)

        completions_wait_for_ms = self.create_spinbox(
            _("Time to wait for all providers to return (ms):"), None,
            'completions_wait_for_ms', min_=0, max_=10000, step=10,
            tip=_("Beyond this timeout the first available provider "
                  "will be returned"))
        completion_hint_box = newcb(
            _("Show completion details"),
            'completions_hint',
            section='editor')
        automatic_completion_box = newcb(
            _("Show completions on the fly"),
            'automatic_completions',
            section='editor')
        completions_after_characters = self.create_spinbox(
            _("Show automatic completions after characters entered:"), None,
            'automatic_completions_after_chars', min_=1, step=1,
            tip=_("Default is 3"), section='editor')
        code_snippets_box = newcb(
            _("Enable code snippets"), 'enable_code_snippets')
        kite_cta_box = newcb(
            _("Notify me when Kite can provide missing completions "
              "(but is unavailable)"),
            'kite_call_to_action')

        # ------------------- Completions group ---------------------------
        self.completions_group = QGroupBox(_('Completions'))
        completions_layout = QGridLayout()
        completions_layout.addWidget(completion_hint_box, 0, 0)
        completions_layout.addWidget(code_snippets_box, 1, 0)
        completions_layout.addWidget(automatic_completion_box, 2, 0)
        completions_layout.addWidget(kite_cta_box, 3, 0)
        completions_layout.addWidget(completions_after_characters.plabel, 4, 0)
        completions_layout.addWidget(completions_after_characters.spinbox, 4, 1)
        completions_layout.addWidget(completions_wait_for_ms.plabel, 5, 0)
        completions_layout.addWidget(completions_wait_for_ms.spinbox, 5, 1)
        completions_layout.setColumnStretch(2, 6)
        self.completions_group.setLayout(completions_layout)

        def disable_completion_after_characters(state):
            completions_after_characters.plabel.setEnabled(state)
            completions_after_characters.spinbox.setEnabled(state)

        automatic_completion_box.toggled.connect(
            disable_completion_after_characters)

        layout = QVBoxLayout()
        layout.addWidget(plugin_state_group)
        layout.addWidget(self.completions_group)
        layout.addWidget(self.providers_group)
        layout.addStretch(1)
        self.setLayout(layout)

    def enable_disable_plugin(self, state):
        self.providers_group.setEnabled(state)
        self.completions_group.setEnabled(state)

        if self.tabs is not None:
            num_tabs = self.tabs.count()
            index = 1
            while index < num_tabs:
                tab_widget = self.tabs.widget(index)
                tab_widget.setEnabled(state)
                index += 1
