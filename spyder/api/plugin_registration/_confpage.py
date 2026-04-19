# -----------------------------------------------------------------------------
# Copyright (c) 2021- Spyder Project Contributors
#
# Released under the terms of the MIT License
# (see LICENSE.txt in the project root directory for details)
# -----------------------------------------------------------------------------

"""Plugin registry configuration page."""

# Standard library imports
from __future__ import annotations
from contextlib import contextmanager
import functools
import os

# Third party imports
from pyuca import Collator
from qtpy.QtCore import Qt
from qtpy.QtWidgets import QCheckBox, QLabel, QMessageBox, QVBoxLayout

# Local imports
from spyder.api.preferences import PluginConfigPage
from spyder.api.translations import _
from spyder.utils.palette import SpyderPalette
from spyder.widgets.elementstable import ElementsTable
from spyder.widgets.helperwidgets import FinderWidget


class PluginsConfigPage(PluginConfigPage):

    def setup_page(self):
        self.plugin_ui_names: dict[str, str] = {}
        self.plugins_checkboxes: dict[str, tuple[QCheckBox, bool]] = {}

        header_label = QLabel(
            _(
                "Disable a Spyder plugin (external or built-in) to prevent it "
                "from loading until re-enabled here, to simplify the interface "
                "or in case it causes problems."
            )
        )
        header_label.setWordWrap(True)

        # To save the plugin elements
        internal_elements = []
        external_elements = []

        # ------------------ Internal plugins ---------------------------------
        for plugin_name in self.plugin.all_internal_plugins:
            (conf_section_name, PluginClass) = (
                self.plugin.all_internal_plugins[plugin_name]
            )

            if not getattr(PluginClass, "CAN_BE_DISABLED", True):
                # Do not list core plugins that can not be disabled
                continue

            plugin_state = self.get_option(
                "enable", section=conf_section_name, default=True
            )
            cb = self.create_checkbox(
                "",
                "enable",
                default=True,
                section=conf_section_name,
                restart=True,
            )
            cb.checkbox.stateChanged.connect(
                functools.partial(
                    self._on_plugin_state_changed, plugin_name=plugin_name
                )
            )

            internal_elements.append(
                dict(
                    title=PluginClass.get_name(),
                    description=PluginClass.get_description(),
                    icon=PluginClass.get_icon(),
                    widget=cb,
                    additional_info=_("Built-in"),
                    additional_info_color=SpyderPalette.COLOR_TEXT_4,
                )
            )

            self.plugin_ui_names[plugin_name] = PluginClass.get_name()
            self.plugins_checkboxes[plugin_name] = (cb.checkbox, plugin_state)

        # ------------------ External plugins ---------------------------------
        for plugin_name in self.plugin.all_external_plugins:
            (conf_section_name, PluginClass) = (
                self.plugin.all_external_plugins[plugin_name]
            )

            if not getattr(PluginClass, "CAN_BE_DISABLED", True):
                # Do not list external plugins that can not be disabled
                continue

            plugin_state = self.get_option(
                f"{conf_section_name}/enable",
                section=self.plugin._external_plugins_conf_section,
                default=True,
            )
            cb = self.create_checkbox(
                "",
                f"{conf_section_name}/enable",
                default=True,
                section=self.plugin._external_plugins_conf_section,
                restart=True,
            )
            cb.checkbox.stateChanged.connect(
                functools.partial(
                    self._on_plugin_state_changed, plugin_name=plugin_name
                )
            )

            external_elements.append(
                dict(
                    title=PluginClass.get_name(),
                    description=PluginClass.get_description(),
                    icon=PluginClass.get_icon(),
                    widget=cb,
                )
            )

            self.plugin_ui_names[plugin_name] = PluginClass.get_name()
            self.plugins_checkboxes[plugin_name] = (cb.checkbox, plugin_state)

        # Sort elements by title for easy searching
        collator = Collator()
        internal_elements.sort(key=lambda e: collator.sort_key(e["title"]))
        external_elements.sort(key=lambda e: collator.sort_key(e["title"]))

        # Build plugins table, showing external plugins first.
        self._plugins_table = ElementsTable(
            self, add_padding_around_widgets=True
        )
        self._plugins_table.setup_elements(
            external_elements + internal_elements
        )

        # Finder to filter plugins
        finder = FinderWidget(
            self,
            find_on_change=True,
            show_close_button=False,
            set_min_width=False,
        )
        finder.sig_find_text.connect(self._do_find)

        # Layout
        layout = QVBoxLayout()
        layout.addWidget(header_label)
        layout.addSpacing(15)
        layout.addWidget(self._plugins_table)
        layout.addWidget(finder)
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
                    (__, PluginClass) = self.plugin.all_internal_plugins[
                        plugin_name
                    ]
                elif plugin_name in self.plugin.all_external_plugins:
                    (__, PluginClass) = self.plugin.all_external_plugins[
                        plugin_name
                    ]
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

    def _do_find(self, text):
        self._plugins_table.do_find(text)

    def _on_plugin_state_changed(self, state: Qt.CheckState, plugin_name: str):
        # Prevent to call this before options are loaded into the page
        if not self.is_loaded:
            return

        # Use a bool for the checked state because it's simpler
        checked = True if state == Qt.Checked else False

        # When a plugin is going to be enabled, we check if we also need to
        # enable some of its dependencies. But if it's disabled, we check if
        # it's necessary to disable its dependents.
        if checked:
            plugins = self.plugin.get_plugin_required_dependencies(plugin_name)
        else:
            plugins = self.plugin.get_plugin_required_dependents(plugin_name)

        if not plugins:
            return

        # Filter those plugins whose current state we also needs to change
        plugins = {
            plugin
            for plugin in plugins
            if self.plugins_checkboxes[plugin][0].isChecked() != checked
        }

        if not plugins:
            return

        # Build list of plugins to show
        plugins_list = ""
        for plugin in plugins:
            plugins_list += f"<li>{self.plugin_ui_names[plugin]}</li>"

        plugins_list = f"<ul>{plugins_list}</ul>"

        # Show message about enabling/disabling dependents
        plugin_ui_name = self.plugin_ui_names[plugin_name]
        if state:
            message = _(
                "Would you like to also enable the following plugins because "
                "they are required by <b>{}</b> to work?"
                "{}"
            ).format(plugin_ui_name, plugins_list)
        else:
            message = _(
                "Besides <b>{}</b>, the following plugins will also be "
                "disabled because they require it to work:"
                "{}"
                "Do you want to proceed?"
            ).format(plugin_ui_name, plugins_list)

        vmargin = "0.4em" if os.name == "nt" else "0.3em"
        style = (
            "<style>"
            "ul, li {{margin-left: -5px}}"
            "li {{margin-bottom: {}}}"
            "</style>"
        ).format(vmargin)

        answer = QMessageBox.warning(
            self,
            _("Warning"),
            style + message,
            QMessageBox.Yes | QMessageBox.No
        )

        # Enable/disable dependents
        if answer == QMessageBox.Yes:
            for plugin in plugins:
                cb = self.plugins_checkboxes[plugin][0]
                with self._disable_stateChanged(cb, plugin):
                    # Use click instead of setChecked because it also changes
                    # the associated checkbox option when clicking on Apply or
                    # Ok
                    cb.click()
        else:
            # Revert to previous state
            cb = self.plugins_checkboxes[plugin_name][0]
            with self._disable_stateChanged(cb, plugin_name):
                cb.click()

    @contextmanager
    def _disable_stateChanged(self, checkbox: QCheckBox, plugin_name: str):
        # Temporarily disconnect this signal to not call it when changing the
        # checkbox state programmatically.
        checkbox.stateChanged.disconnect()

        try:
            yield
        finally:
            # Reconnect slot again
            checkbox.stateChanged.connect(
                functools.partial(
                    self._on_plugin_state_changed, plugin_name=plugin_name
                )
            )
