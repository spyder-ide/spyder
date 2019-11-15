# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""
API to create an entry in Spyder Preferences dialog associated to a
given plugin.
"""
# Third-party imports
from qtpy.QtWidgets import QMessageBox
# Local imports
from spyder.config.base import _
from spyder.preferences.configdialog import SpyderConfigPage

class PluginConfigPage(SpyderConfigPage):
    """Plugin configuration dialog box page widget."""

    def __init__(self, plugin, parent):
        self.plugin = plugin
        self.main = parent.main
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

    def prompt_restart_required(self):
        """Prompt the user with a request to restart."""
        restart_opts = self.restart_options
        changed_opts = self.changed_options
        options = [restart_opts[o] for o in changed_opts if o in restart_opts]

        if len(options) == 1:
            msg_start = _("Spyder needs to restart to change the following "
                          "setting:")
        else:
            msg_start = _("Spyder needs to restart to change the following "
                          "settings:")
        msg_end = _("Do you wish to restart now?")

        msg_options = u""
        for option in options:
            msg_options += u"<li>{0}</li>".format(option)

        msg_title = _("Information")
        msg = u"{0}<ul>{1}</ul><br>{2}".format(msg_start, msg_options, msg_end)
        answer = QMessageBox.information(self, msg_title, msg,
                                         QMessageBox.Yes | QMessageBox.No)
        if answer == QMessageBox.Yes:
            self.restart()

    def restart(self):
        """Restart Spyder."""
        self.main.restart()
