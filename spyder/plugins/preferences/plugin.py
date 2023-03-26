# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""
Spyder preferences plugin.

This plugin is in charge of managing preference pages and tabs for all plugins
in Spyder, both internal and external.
"""

# Standard library imports
import os
import logging
from typing import Union

# Third-party imports
from packaging.version import parse, Version
from qtpy.QtGui import QIcon
from qtpy.QtCore import Slot
from qtpy.QtWidgets import QMessageBox

# Local imports
from spyder.api.plugins import Plugins, SpyderPluginV2, SpyderPlugin
from spyder.api.plugin_registration.decorators import (
    on_plugin_available, on_plugin_teardown)
from spyder.config.base import _
from spyder.config.main import CONF_VERSION
from spyder.config.user import NoDefault
from spyder.plugins.mainmenu.api import ApplicationMenus, ToolsMenuSections
from spyder.plugins.preferences.widgets.container import (
    PreferencesActions, PreferencesContainer)
from spyder.plugins.pythonpath.api import PythonpathActions
from spyder.plugins.toolbar.api import ApplicationToolbars, MainToolbarSections

logger = logging.getLogger(__name__)

BaseType = Union[int, float, bool, complex, str, bytes]
IterableType = Union[list, tuple]
BasicType = Union[BaseType, IterableType]


class Preferences(SpyderPluginV2):
    """
    Spyder preferences plugin.

    This class manages all the preference pages and tabs for all internal
    and external plugins, as well enabling other plugins to add configurations
    to other sections.
    """

    NAME = 'preferences'
    CONF_SECTION = 'preferences'
    OPTIONAL = [Plugins.MainMenu, Plugins.Toolbar]
    CONF_FILE = False
    CONTAINER_CLASS = PreferencesContainer
    CAN_BE_DISABLED = False

    NEW_API = 'new'
    OLD_API = 'old'

    def __init__(self, parent, configuration=None):
        super().__init__(parent, configuration)
        self.config_pages = {}
        self.config_tabs = {}

    def register_plugin_preferences(
            self, plugin: Union[SpyderPluginV2, SpyderPlugin]) -> None:
        if (hasattr(plugin, 'CONF_WIDGET_CLASS') and
                plugin.CONF_WIDGET_CLASS is not None):
            # New API
            Widget = plugin.CONF_WIDGET_CLASS

            self.config_pages[plugin.NAME] = (self.NEW_API, Widget, plugin)

            plugin_conf_version = plugin.CONF_VERSION or CONF_VERSION
            plugin_conf_version = parse(plugin_conf_version)

            # Check if the plugin adds new configuration options to other
            # sections
            if plugin.ADDITIONAL_CONF_OPTIONS is not None:
                for conf_section in plugin.ADDITIONAL_CONF_OPTIONS:
                    conf_keys = plugin.ADDITIONAL_CONF_OPTIONS[conf_section]
                    for conf_key in conf_keys:
                        new_value = conf_keys[conf_key]
                        self.check_version_and_merge(
                            conf_section, conf_key, new_value,
                            plugin_conf_version, plugin)

            # Check if the plugin declares any additional configuration tabs
            if plugin.ADDITIONAL_CONF_TABS is not None:
                for plugin_name in plugin.ADDITIONAL_CONF_TABS:
                    tabs_to_add = plugin.ADDITIONAL_CONF_TABS[plugin_name]
                    plugin_tabs = self.config_tabs.get(plugin_name, [])
                    plugin_tabs += tabs_to_add
                    self.config_tabs[plugin_name] = plugin_tabs

        elif (hasattr(plugin, 'CONFIGWIDGET_CLASS') and
                plugin.CONFIGWIDGET_CLASS is not None):
            # Old API
            Widget = plugin.CONFIGWIDGET_CLASS

            self.config_pages[plugin.CONF_SECTION] = (
                self.OLD_API, Widget, plugin)

    def deregister_plugin_preferences(
            self, plugin: Union[SpyderPluginV2, SpyderPlugin]):
        """Remove a plugin preference page and additional configuration tabs."""
        name = (getattr(plugin, 'NAME', None) or
                    getattr(plugin, 'CONF_SECTION', None))

        # Remove configuration page for the plugin
        self.config_pages.pop(name)

        # Remove additional configuration tabs that the plugin did introduce
        if isinstance(plugin, SpyderPluginV2):
            for plugin_name in (plugin.ADDITIONAL_CONF_TABS or []):
                tabs = plugin.ADDITIONAL_CONF_TABS[plugin_name]
                for tab in tabs:
                    self.config_tabs[plugin_name].remove(tab)

    def check_version_and_merge(
        self,
        conf_section: str,
        conf_key: str,
        new_value: BasicType,
        current_version: Version,
        plugin
    ):
        """Add a versioned additional option to a configuration section."""
        current_value = self.get_conf(
            conf_key, section=conf_section, default=None)
        section_additional = self.get_conf('additional_configuration',
                                           section=conf_section,
                                           default={})
        plugin_additional = section_additional.get(plugin.NAME, {})

        if conf_key in plugin_additional:
            conf_key_info = plugin_additional[conf_key]
            prev_default = conf_key_info['default']
            prev_version = parse(conf_key_info['version'])

            allow_replacement = current_version > prev_version
            allow_deletions = current_version.major > prev_version.major
            new_value = self.merge_defaults(prev_default, new_value,
                                            allow_replacement, allow_deletions)
            new_default = new_value

            if current_value != NoDefault:
                new_value = self.merge_configurations(current_value, new_value)

            self.set_conf(
                conf_key, new_value, section=conf_section)

            conf_key_info['version'] = str(current_version)
            conf_key_info['default'] = new_default
            plugin_additional[conf_key] = conf_key_info
            section_additional[plugin.NAME] = plugin_additional

            self.set_conf(
                'additional_configuration', section_additional,
                section=conf_section)
        else:
            plugin_additional[conf_key] = {
                'version': str(current_version),
                'default': new_value
            }
            section_additional[plugin.NAME] = plugin_additional

            self.set_conf(
                'additional_configuration', section_additional,
                section=conf_section)

            if current_value != NoDefault:
                new_value = self.merge_configurations(current_value, new_value)

            self.set_conf(
                conf_key, new_value, section=conf_section)


    def merge_defaults(self, prev_default: BasicType,
                       new_default: BasicType,
                       allow_replacement: bool = False,
                       allow_deletions: bool = False) -> BasicType:
        """Compare and merge two versioned values."""
        prev_type = type(prev_default)
        new_type = type(new_default)

        if prev_type is dict and new_type is dict:
            # Merge two dicts case
            for new_key in new_default:
                if new_key in prev_default:
                    current_subvalue = prev_default[new_key]
                    new_subvalue = new_default[new_key]
                    prev_default[new_key] = self.merge_defaults(
                        current_subvalue, new_subvalue,
                        allow_replacement, allow_deletions)
                else:
                    # Additions are allowed everytime
                    prev_default[new_key] = new_default[new_key]

            if allow_deletions:
                for old_key in list(prev_default.keys()):
                    if old_key not in new_default:
                        prev_default.pop(old_key)

            return prev_default
        elif prev_default != new_default:
            if allow_replacement:
                return new_default
            else:
                return prev_default
        else:
            return prev_default

    def merge_configurations(
            self, current_value: BasicType, new_value: BasicType) -> BasicType:
        """
        Recursively match and merge a new configuration value into a
        previous one.
        """
        current_type = type(current_value)
        new_type = type(new_value)
        iterable_types = {list, tuple}
        base_types = {int, float, bool, complex, str, bytes}

        if current_type is dict and new_type is dict:
            # Merge two dicts case
            for new_key in new_value:
                if new_key in current_value:
                    current_subvalue = current_value[new_key]
                    new_subvalue = new_value[new_key]
                    current_value[new_key] = self.merge_configurations(
                        current_subvalue, new_subvalue)
                else:
                    current_value[new_key] = new_value[new_key]
            return current_value
        elif current_type in iterable_types and new_type in iterable_types:
            # Merge two lists/tuples case
            return current_type(list(current_value) + list(new_value))
        elif (current_type == new_type and
                current_type in base_types and new_type in base_types):
            # Replace the values directly
            return new_value
        elif current_type in iterable_types and new_type in base_types:
            # Add a value to a list or tuple
            return current_type((list(current_value) + [new_value]))
        elif current_value is None:
            # Assigns the new value if it doesn't exist
            return new_value
        else:
            logger.warning(f'The value {current_value} cannot be replaced'
                           f'by {new_value}')
            return current_value

    def open_dialog(self, prefs_dialog_size):
        container = self.get_container()
        container.create_dialog(
            self.config_pages, self.config_tabs, prefs_dialog_size,
            self.get_main())

    # ---------------- Public Spyder API required methods ---------------------
    @staticmethod
    def get_name() -> str:
        return _('Preferences')

    def get_description(self) -> str:
        return _('This plugin provides access to Spyder preferences page')

    def get_icon(self) -> QIcon:
        return self.create_icon('configure')

    def on_initialize(self):
        container = self.get_container()
        main = self.get_main()

        container.sig_show_preferences_requested.connect(
            lambda: self.open_dialog(main.prefs_dialog_size))
        container.sig_reset_preferences_requested.connect(self.reset)

    @on_plugin_available(plugin=Plugins.MainMenu)
    def on_main_menu_available(self):
        container = self.get_container()
        main_menu = self.get_plugin(Plugins.MainMenu)

        main_menu.add_item_to_application_menu(
            container.show_action,
            menu_id=ApplicationMenus.Tools,
            section=ToolsMenuSections.Tools,
        )

        main_menu.add_item_to_application_menu(
            container.reset_action,
            menu_id=ApplicationMenus.Tools,
            section=ToolsMenuSections.Extras,
        )

    @on_plugin_available(plugin=Plugins.Toolbar)
    def on_toolbar_available(self):
        container = self.get_container()
        toolbar = self.get_plugin(Plugins.Toolbar)
        toolbar.add_item_to_application_toolbar(
            container.show_action,
            toolbar_id=ApplicationToolbars.Main,
            section=MainToolbarSections.ApplicationSection,
            before=PythonpathActions.Manager
        )

    @on_plugin_teardown(plugin=Plugins.MainMenu)
    def on_main_menu_teardown(self):
        main_menu = self.get_plugin(Plugins.MainMenu)

        main_menu.remove_item_from_application_menu(
            PreferencesActions.Show,
            menu_id=ApplicationMenus.Tools,
        )

        main_menu.remove_item_from_application_menu(
            PreferencesActions.Reset,
            menu_id=ApplicationMenus.Tools,
        )

    @on_plugin_teardown(plugin=Plugins.Toolbar)
    def on_toolbar_teardown(self):
        toolbar = self.get_plugin(Plugins.Toolbar)
        toolbar.remove_item_from_application_toolbar(
            PreferencesActions.Show,
            toolbar_id=ApplicationToolbars.Main
        )

    @Slot()
    def reset(self):
        answer = QMessageBox.warning(self.main, _("Warning"),
             _("Spyder will restart and reset to default settings: <br><br>"
               "Do you want to continue?"),
             QMessageBox.Yes | QMessageBox.No)
        if answer == QMessageBox.Yes:
            os.environ['SPYDER_RESET'] = 'True'
            self.sig_restart_requested.emit()

    def on_close(self, cancelable=False):
        container = self.get_container()
        if container.is_preferences_open():
            container.close_preferences()
        return True
