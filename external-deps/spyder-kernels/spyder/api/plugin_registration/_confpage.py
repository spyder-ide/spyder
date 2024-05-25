# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""Plugin registry configuration page."""

# Third party imports
from pyuca import Collator
from qtpy.QtWidgets import QVBoxLayout, QLabel

# Local imports
from spyder.api.preferences import PluginConfigPage
from spyder.config.base import _
from spyder.widgets.elementstable import ElementsTable


class PluginsConfigPage(PluginConfigPage):

    def setup_page(self):
        newcb = self.create_checkbox
        self.plugins_checkboxes = {}

        header_label = QLabel(
            _("Disable a Spyder plugin (external or built-in) to prevent it "
              "from loading until re-enabled here, to simplify the interface "
              "or in case it causes problems.")
        )
        header_label.setWordWrap(True)

        # To save the plugin elements
        internal_elements = []
        external_elements = []

        # ------------------ Internal plugins ---------------------------------
        for plugin_name in self.plugin.all_internal_plugins:
            (conf_section_name,
             PluginClass) = self.plugin.all_internal_plugins[plugin_name]

            if not getattr(PluginClass, 'CAN_BE_DISABLED', True):
                # Do not list core plugins that can not be disabled
                continue

            plugin_state = self.get_option(
                'enable', section=conf_section_name, default=True)
            cb = newcb('', 'enable', default=True, section=conf_section_name,
                       restart=True)

            internal_elements.append(
                dict(
                    title=PluginClass.get_name(),
                    description=PluginClass.get_description(),
                    icon=PluginClass.get_icon(),
                    widget=cb,
                    additional_info=_("Built-in")
                )
            )

            self.plugins_checkboxes[plugin_name] = (cb.checkbox, plugin_state)

        # ------------------ External plugins ---------------------------------
        for plugin_name in self.plugin.all_external_plugins:
            (conf_section_name,
             PluginClass) = self.plugin.all_external_plugins[plugin_name]

            if not getattr(PluginClass, 'CAN_BE_DISABLED', True):
                # Do not list external plugins that can not be disabled
                continue

            plugin_state = self.get_option(
                f'{conf_section_name}/enable',
                section=self.plugin._external_plugins_conf_section,
                default=True
            )
            cb = newcb('', f'{conf_section_name}/enable', default=True,
                       section=self.plugin._external_plugins_conf_section,
                       restart=True)

            external_elements.append(
                dict(
                    title=PluginClass.get_name(),
                    description=PluginClass.get_description(),
                    icon=PluginClass.get_icon(),
                    widget=cb
                )
            )

            self.plugins_checkboxes[plugin_name] = (cb.checkbox, plugin_state)

        # Sort elements by title for easy searching
        collator = Collator()
        internal_elements.sort(key=lambda e: collator.sort_key(e['title']))
        external_elements.sort(key=lambda e: collator.sort_key(e['title']))

        # Build plugins table, showing external plugins first.
        plugins_table = ElementsTable(
            self, external_elements + internal_elements
        )

        # Layout
        layout = QVBoxLayout()
        layout.addWidget(header_label)
        layout.addSpacing(15)
        layout.addWidget(plugins_table)
        layout.addSpacing(15)
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
                    external = True  # noqa

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
