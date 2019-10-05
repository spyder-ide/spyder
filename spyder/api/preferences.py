# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""
API to create an entry in Spyder Preferences dialog associated to a
given plugin.
"""

# Local imports
from spyder.preferences.configdialog import SpyderConfigPage

class PluginConfigPage(SpyderConfigPage):
    """Plugin configuration dialog box page widget."""

    def __init__(self, plugin, parent):
        self.plugin = plugin
        self.get_option = plugin.get_option
        self.set_option = plugin.set_option
        self.get_font = plugin.get_font
        self.apply_settings = plugin.apply_plugin_settings
        SpyderConfigPage.__init__(self, parent)

    def get_name(self):
        """
        Return plugin name to use in preferences page title, and
        message boxes.

        Normally you do not have to reimplement it, as soon as the
        plugin name in preferences page will be the same as the plugin
        title.
        """
        return self.plugin.get_plugin_title()

    def get_icon(self):
        """
        Return plugin icon to use in preferences page.

        Normally you do not have to reimplement it, as soon as the
        plugin icon in preferences page will be the same as the plugin
        icon.
        """
        return self.plugin.get_plugin_icon()

    def setup_page(self):
        """Setup configuration page widget

        You should implement this method and set the layout of the
        preferences page.

        layout = QVBoxLayout()
        layout.addWidget(...)
        ...
        self.setLayout(layout)
        """
        raise NotImplementedError
