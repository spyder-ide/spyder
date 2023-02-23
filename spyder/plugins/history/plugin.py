# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""
Console History Plugin.
"""

# Third party imports
from qtpy.QtCore import Signal

# Local imports
from spyder.api.plugins import Plugins, SpyderDockablePlugin
from spyder.api.plugin_registration.decorators import (
    on_plugin_available, on_plugin_teardown)
from spyder.api.translations import _
from spyder.config.base import get_conf_path
from spyder.plugins.history.confpage import HistoryConfigPage
from spyder.plugins.history.widgets import HistoryWidget


class HistoryLog(SpyderDockablePlugin):
    """
    History log plugin.
    """

    NAME = 'historylog'
    REQUIRES = [Plugins.Preferences, Plugins.Console]
    OPTIONAL = [Plugins.IPythonConsole]
    TABIFY = Plugins.IPythonConsole
    WIDGET_CLASS = HistoryWidget
    CONF_SECTION = NAME
    CONF_WIDGET_CLASS = HistoryConfigPage
    CONF_FILE = False

    # --- Signals
    # ------------------------------------------------------------------------
    sig_focus_changed = Signal()
    """
    This signal is emitted when the focus of the code editor storing history
    changes.
    """

    def __init__(self, parent=None, configuration=None):
        """Initialization."""
        super().__init__(parent, configuration)
        self.add_history(get_conf_path('history.py'))

    # --- SpyderDockablePlugin API
    # ------------------------------------------------------------------------
    @staticmethod
    def get_name():
        return _('History')

    def get_description(self):
        return _('Provide command history for IPython Consoles')

    def get_icon(self):
        return self.create_icon('history')

    def on_initialize(self):
        widget = self.get_widget()
        widget.sig_focus_changed.connect(self.sig_focus_changed)

    @on_plugin_available(plugin=Plugins.Preferences)
    def on_preferences_available(self):
        preferences = self.get_plugin(Plugins.Preferences)
        preferences.register_plugin_preferences(self)

    @on_plugin_available(plugin=Plugins.Console)
    def on_console_available(self):
        console = self.get_plugin(Plugins.Console)
        console.sig_refreshed.connect(self.refresh)

    @on_plugin_available(plugin=Plugins.IPythonConsole)
    def on_ipyconsole_available(self):
        ipyconsole = self.get_plugin(Plugins.IPythonConsole)
        ipyconsole.sig_append_to_history_requested.connect(
            self.append_to_history)

    @on_plugin_teardown(plugin=Plugins.Preferences)
    def on_preferences_teardown(self):
        preferences = self.get_plugin(Plugins.Preferences)
        preferences.deregister_plugin_preferences(self)

    @on_plugin_teardown(plugin=Plugins.Console)
    def on_console_teardown(self):
        console = self.get_plugin(Plugins.Console)
        console.sig_refreshed.disconnect(self.refresh)

    @on_plugin_teardown(plugin=Plugins.IPythonConsole)
    def on_ipyconsole_teardown(self):
        ipyconsole = self.get_plugin(Plugins.IPythonConsole)
        ipyconsole.sig_append_to_history_requested.disconnect(
            self.append_to_history)

    def update_font(self):
        color_scheme = self.get_color_scheme()
        font = self.get_font()
        self.get_widget().update_font(font, color_scheme)

    # --- Plubic API
    # ------------------------------------------------------------------------
    def refresh(self):
        """
        Refresh main widget.
        """
        self.get_widget().refresh()

    def add_history(self, filename):
        """
        Create history file.

        Parameters
        ----------
        filename: str
            History file.
        """
        self.get_widget().add_history(filename)

    def append_to_history(self, filename, command):
        """
        Append command to history file.

        Parameters
        ----------
        filename: str
            History file.
        command: str
            Command to append to history file.
        """
        self.get_widget().append_to_history(filename, command)
