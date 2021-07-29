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
from spyder.api.plugin_registration.decorators import on_plugin_available
from spyder.api.translations import get_translation
from spyder.plugins.history.confpage import HistoryConfigPage
from spyder.plugins.history.widgets import HistoryWidget

# Localization
_ = get_translation('spyder')


class HistoryLog(SpyderDockablePlugin):
    """
    History log plugin.
    """

    NAME = 'historylog'
    REQUIRES = [Plugins.Preferences, Plugins.Editor, Plugins.Console]
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

    # --- SpyderDockablePlugin API
    # ------------------------------------------------------------------------
    def get_name(self):
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
