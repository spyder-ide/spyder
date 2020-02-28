# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""Online Help Plugin"""

# Standard library imports
import os.path as osp

# Third party imports
from qtpy.QtWidgets import QVBoxLayout

# Local imports
from spyder.config.base import _, get_conf_path
from spyder.api.plugins import SpyderPluginWidget
from spyder.py3compat import to_text_string
from spyder.plugins.onlinehelp.widgets import PydocBrowser


class OnlineHelp(SpyderPluginWidget):
    """Online Help Plugin."""

    CONF_SECTION = 'onlinehelp'
    CONF_FILE = False
    LOG_PATH = get_conf_path(CONF_SECTION)

    def __init__(self, parent):
        SpyderPluginWidget.__init__(self, parent)

        self.pydocbrowser = PydocBrowser(self, self.options_button)

        layout = QVBoxLayout()
        layout.addWidget(self.pydocbrowser)
        self.setLayout(layout)

        self.register_widget_shortcuts(self.pydocbrowser.find_widget)
        self.pydocbrowser.webview.set_zoom_factor(
            self.get_option('zoom_factor'))
        self.pydocbrowser.url_combo.setMaxCount(
            self.get_option('max_history_entries'))
        self.pydocbrowser.url_combo.addItems(self.load_history())

    #------ Public API ---------------------------------------------------------
    def load_history(self, obj=None):
        """Load history from a text file in user home directory"""
        if osp.isfile(self.LOG_PATH):
            history = [line.replace('\n', '')
                       for line in open(self.LOG_PATH, 'r').readlines()]
        else:
            history = []
        return history
    
    def save_history(self):
        """Save history to a text file in user home directory"""
        open(self.LOG_PATH, 'w').write("\n".join( \
                [to_text_string(self.pydocbrowser.url_combo.itemText(index))
                 for index in range(self.pydocbrowser.url_combo.count())]))

    #------ SpyderPluginWidget API ---------------------------------------------
    def toggle_view(self, checked):
        """Toggle view action."""
        if checked:
            if not self.pydocbrowser.is_server_running():
                self.pydocbrowser.initialize()
            self.dockwidget.show()
            self.dockwidget.raise_()
        else:
            self.dockwidget.hide()

    def get_plugin_title(self):
        """Return widget title"""
        return _('Online help')
    
    def get_focus_widget(self):
        """
        Return the widget to give focus to when
        this plugin's dockwidget is raised on top-level
        """
        self.pydocbrowser.url_combo.lineEdit().selectAll()
        return self.pydocbrowser.url_combo
        
    def closing_plugin(self, cancelable=False):
        """Perform actions before parent main window is closed"""
        self.save_history()
        self.set_option('zoom_factor',
                        self.pydocbrowser.webview.get_zoom_factor())
        return True

    def on_first_registration(self):
        """Action to be performed on first plugin registration"""
        self.tabify(self.main.help)
