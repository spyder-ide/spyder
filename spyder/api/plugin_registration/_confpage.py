# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""Plugin registry configuration page."""

# Third party imports
from qtpy.QtWidgets import (QGroupBox, QVBoxLayout, QCheckBox,
                            QGridLayout, QLabel)

# Local imports
from spyder.api.plugins import SpyderPlugin
from spyder.api.preferences import PluginConfigPage
from spyder.config.base import _
from spyder.config.manager import CONF


class PluginsConfigPage(PluginConfigPage):
    def setup_page(self):
        newcb = self.create_checkbox
        self.plugins_checkboxes = {}

        header_label = QLabel(
            _("Here you can turn on/off any internal or external Spyder plugin "
              "to disable functionality that is not desired or to have a lighter "
              "experience. Unchecked plugins in this page will be unloaded "
              "immediately and will not be loaded the next time Spyder starts."))
        header_label.setWordWrap(True)

        # ------------------ Internal plugin status group ---------------------
        internal_layout = QGridLayout()
        self.internal_plugins_group = QGroupBox(_("Internal plugins"))

        i = 0
        for plugin_name in self.plugin.all_internal_plugins:
            (conf_section_name,
             PluginClass) = self.plugin.all_internal_plugins[plugin_name]

            if not getattr(PluginClass, 'CAN_BE_DISABLED', True):
                # Do not list core plugins that can not be disabled
                continue

            plugin_loc_name = None
            if hasattr(PluginClass, 'get_name'):
                plugin_loc_name = PluginClass.get_name()
            elif hasattr(PluginClass, 'get_plugin_title'):
                plugin_loc_name = PluginClass.get_plugin_title()

            plugin_state = CONF.get(conf_section_name, 'enable', True)
            cb = newcb(plugin_loc_name, 'enable', default=True,
                       section=conf_section_name, restart=True)
            internal_layout.addWidget(cb, i // 2, i % 2)
            self.plugins_checkboxes[plugin_name] = (cb, plugin_state)
            i += 1

        self.internal_plugins_group.setLayout(internal_layout)

        # ------------------ External plugin status group ---------------------
        external_layout = QGridLayout()
        self.external_plugins_group = QGroupBox(_("External plugins"))

        i = 0
        # Temporal fix to avoid disabling external plugins.
        # for more info see spyder#17464
        show_external_plugins_group = False
        for i, plugin_name in enumerate(self.plugin.all_external_plugins):
            (conf_section_name,
             PluginClass) = self.plugin.all_external_plugins[plugin_name]

            if not getattr(PluginClass, 'CAN_BE_DISABLED', True):
                # Do not list external plugins that can not be disabled
                continue

            plugin_loc_name = None
            if hasattr(PluginClass, 'get_name'):
                plugin_loc_name = PluginClass.get_name()
            elif hasattr(PluginClass, 'get_plugin_title'):
                plugin_loc_name = PluginClass.get_plugin_title()

            cb = newcb(plugin_loc_name, 'enable', default=True,
                       section=conf_section_name, restart=True)
            external_layout.addWidget(cb, i // 2, i % 2)
            plugin_state = CONF.get(conf_section_name, 'enable', True)
            self.plugins_checkboxes[plugin_name] = (cb, plugin_state)
            i += 1

        self.external_plugins_group.setLayout(external_layout)

        layout = QVBoxLayout()
        layout.addWidget(header_label)
        layout.addWidget(self.internal_plugins_group)
        if show_external_plugins_group:
            layout.addWidget(self.external_plugins_group)
        layout.addStretch(1)
        self.setLayout(layout)

    def apply_settings(self):
        for plugin_name in self.plugins_checkboxes:
            cb, previous_state = self.plugins_checkboxes[plugin_name]
            if cb.isChecked() and not previous_state:
                self.plugin.set_plugin_enabled(plugin_name)
                PluginClass = None
                external = False
                if plugin_name in self.plugin.all_internal_plugins:
                    (__,
                     PluginClass) = self.plugin.all_internal_plugins[plugin_name]
                elif plugin_name in self.plugin.all_external_plugins:
                    (__,
                     PluginClass) = self.plugin.all_external_plugins[plugin_name]
                    external = True

                # TODO: Once we can test that all plugins can be restarted
                # without problems during runtime, we can enable the
                # autorestart feature provided by the plugin registry:
                # self.plugin.register_plugin(self.main, PluginClass,
                #                             external=external)
            elif not cb.isChecked() and previous_state:
                # TODO: Once we can test that all plugins can be restarted
                # without problems during runtime, we can enable the
                # autorestart feature provided by the plugin registry:
                # self.plugin.delete_plugin(plugin_name)
                pass
        return set({})
