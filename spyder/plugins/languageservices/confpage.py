# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""Preferences page of the language services plugin."""

from __future__ import annotations

# Standard library imports
import functools
import inspect

# Third party imports
from qtpy.QtWidgets import (
    QGridLayout,
    QGroupBox,
    QLabel,
    QVBoxLayout,
    QWidget,
)

# Local imports
from spyder.api.preferences import PluginConfigPage
from spyder.api.translations import _
from spyder.widgets.config import BaseConfigTab
from spyder.plugins.languageservices.api.provider import (
    ProviderConfigAccessor,
)
from spyder.plugins.languageservices.widgets.policies import (
    RequestPolicyTable,
)


class ProviderTabHost(QWidget):
    """Parent widget of a provider preference tab.

    :class:`~spyder.api.preferences.SpyderPreferencesTab` delegates every
    unknown attribute to its parent. This host forwards them to the plugin's
    config page while rewriting the ``option`` argument of ``create_*``
    calls and the ``get/set/remove_option`` accessors to the provider's
    configuration namespace, so provider tabs are written as if they had a
    section of their own.
    """

    def __init__(self, page: PluginConfigPage, config: ProviderConfigAccessor):
        super().__init__(page)
        self.page = page
        self.config = config

    # Attribute names used by tabs that must resolve to this object.
    get_option = property(lambda self: self.config.get_conf)
    set_option = property(lambda self: self.config.set_conf)
    remove_option = property(lambda self: self.config.remove_conf)

    def wrap_options(self, options):
        """Prefix a set of option keys with the provider namespace."""
        return {self.config.wrap_option(option) for option in options}

    def __getattr__(self, name):
        target = getattr(self.page, name)
        if not name.startswith("create_") or not callable(target):
            return target
        parameters = inspect.signature(target).parameters
        if "option" not in parameters:
            return target
        position = list(parameters).index("option")

        @functools.wraps(target)
        def wrapper(*args, **kwargs):
            if kwargs.get("section") is None:
                if "option" in kwargs:
                    kwargs["option"] = self.config.wrap_option(kwargs["option"])
                elif len(args) > position:
                    args = list(args)
                    args[position] = self.config.wrap_option(args[position])
            widget = target(*args, **kwargs)
            if isinstance(widget, QWidget):
                widget.setParent(self)
            return widget

        return wrapper


class LanguageServicesConfigPage(PluginConfigPage):
    """General options, provider switches, request policies and the
    preference tabs declared by providers."""

    def __init__(self, plugin, parent):
        self.provider_tabs = {}
        super().__init__(plugin, parent)

    def setup_page(self):
        newcb = self.create_checkbox
        plugin = self.plugin

        # ---- Completions
        completions_group = QGroupBox(_("Completions"))
        completions_layout = QGridLayout()
        completions_layout.addWidget(
            newcb(_("Show completion details"), "completions_hint",
                  section="editor"), 0, 0)
        completions_layout.addWidget(
            newcb(_("Enable code snippets"), "enable_code_snippets"), 1, 0)
        automatic = newcb(_("Show completions on the fly"),
                          "automatic_completions", section="editor")
        completions_layout.addWidget(automatic, 2, 0)
        completions_layout.addWidget(
            newcb(_("Use Enter to accept code completions"),
                  "use_enter_for_completions",
                  tip=_("If this option is disabled, completions will be "
                        "accepted with the Tab key only.")), 3, 0)
        after_chars = self.create_spinbox(
            _("Show automatic completions after characters entered:"), None,
            "automatic_completions_after_chars", min_=1, step=1,
            tip=_("Default is 1"), section="editor")
        completions_layout.addWidget(after_chars.plabel, 4, 0)
        completions_layout.addWidget(after_chars.spinbox, 4, 1)
        completions_layout.addWidget(after_chars.help_label, 4, 2)
        hint_idle = self.create_spinbox(
            _("Show completion details after keyboard idle (ms):"), None,
            "completions_hint_after_ms", min_=0, max_=10000, step=10,
            tip=_("Default is 500 milliseconds"), section="editor")
        completions_layout.addWidget(hint_idle.plabel, 5, 0)
        completions_layout.addWidget(hint_idle.spinbox, 5, 1)
        completions_layout.addWidget(hint_idle.help_label, 5, 2)
        timeout = self.create_spinbox(
            _("Time to wait for a provider to answer (ms):"), None,
            "request_timeout_ms", min_=100, max_=60000, step=100,
            tip=_("Answers arriving after this timeout are discarded"))
        completions_layout.addWidget(timeout.plabel, 6, 0)
        completions_layout.addWidget(timeout.spinbox, 6, 1)
        completions_layout.addWidget(timeout.help_label, 6, 2)
        completions_layout.setColumnStretch(3, 6)
        completions_group.setLayout(completions_layout)

        automatic.checkbox.toggled.connect(after_chars.plabel.setEnabled)
        automatic.checkbox.toggled.connect(after_chars.spinbox.setEnabled)

        # ---- Providers
        self.providers_group = QGroupBox(_("Providers"))
        providers_layout = QGridLayout()
        self.provider_names = plugin.provider_names()
        for row, name in enumerate(self.provider_names):
            providers_layout.addWidget(
                newcb(_("Enable {0} provider").format(name),
                      ("providers", name, "enable"), default=True),
                row, 0)
        self.providers_group.setLayout(providers_layout)

        # ---- Request policies
        policies_group = QGroupBox(_("Requests"))
        policies_layout = QVBoxLayout()
        label = QLabel(_(
            "Choose how the answers of several providers are combined for "
            "each feature, or which provider answers it alone."))
        label.setWordWrap(True)
        policies_layout.addWidget(label)
        self.policies_table = RequestPolicyTable(self, self.provider_names)
        self.policies_table.load(self.get_option("request_policies", {}))
        policies_layout.addWidget(self.policies_table)
        policies_group.setLayout(policies_layout)

        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(completions_group)
        layout.addWidget(self.providers_group)
        layout.addWidget(policies_group)
        layout.addStretch(1)
        self.setLayout(layout)

        for name in self.provider_names:
            provider = plugin.get_provider(name)
            for Tab in provider.CONF_TABS:
                self._add_provider_tab(Tab, provider.config)

    def _add_provider_tab(self, Tab, config):
        host = ProviderTabHost(self, config)
        tab = Tab(host)
        self.provider_tabs[tab] = host
        if self.tabs is None:
            main_widget = QWidget(self)
            main_widget.setLayout(self.layout())
            self.create_tab(_("General"), main_widget)
        self.create_tab(Tab.TITLE, tab)

    def apply_settings(self):
        options = super().apply_settings() or set()
        policies = self.policies_table.policies()
        if policies != self.get_option("request_policies", {}):
            self.set_option("request_policies", policies)
            options |= {"request_policies"}
        return options

    def _apply_settings_tabs(self, options):
        """Namespace the options that provider tabs apply by hand."""
        if self.tabs is not None:
            for i in range(self.tabs.count()):
                layout = self.tabs.widget(i).layout()
                for j in range(layout.count()):
                    widget = layout.itemAt(j).widget()
                    if not isinstance(widget, BaseConfigTab):
                        continue
                    applied = widget.apply_settings() or set()
                    host = self.provider_tabs.get(widget)
                    if host is not None:
                        applied = host.wrap_options(applied)
                    options |= applied
        self.apply_settings(options)

    def enable_disable_plugin(self, state):
        self.providers_group.setEnabled(state)
        if self.tabs is not None:
            for index in range(1, self.tabs.count()):
                self.tabs.widget(index).setEnabled(state)
