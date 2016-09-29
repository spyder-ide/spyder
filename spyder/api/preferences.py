# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""
Preferences API.
"""

# Local imports
from spyder.plugins.configdialog import SpyderConfigPage

class PluginConfigPage(SpyderConfigPage):
    """Plugin configuration dialog box page widget"""
    def __init__(self, plugin, parent):
        self.plugin = plugin
        self.get_option = plugin.get_option
        self.set_option = plugin.set_option
        self.get_font = plugin.get_plugin_font
        self.apply_settings = plugin.apply_plugin_settings
        SpyderConfigPage.__init__(self, parent)

    def get_name(self):
        return self.plugin.get_plugin_title()

    def get_icon(self):
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
