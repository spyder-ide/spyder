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
from spyder.api.fonts import SpyderFontType
from spyder.api.plugins import Plugins, SpyderDockablePlugin
from spyder.api.plugin_registration.decorators import (
    on_plugin_available, on_plugin_teardown)
from spyder.api.shellconnect.mixins import ShellConnectPluginMixin
from spyder.api.translations import _
from spyder.plugins.history.confpage import HistoryConfigPage
from spyder.plugins.history.widgets import HistoryWidget


class HistoryLog(SpyderDockablePlugin, ShellConnectPluginMixin):
    """
    History log plugin.
    """

    NAME = 'historylog'
    REQUIRES = [Plugins.Console, Plugins.IPythonConsole, Plugins.Preferences]
    TABIFY = Plugins.IPythonConsole
    WIDGET_CLASS = HistoryWidget
    CONF_SECTION = NAME
    CONF_WIDGET_CLASS = HistoryConfigPage
    CONF_FILE = False

    # ---- Signals
    # ------------------------------------------------------------------------
    sig_focus_changed = Signal()
    """
    This signal is emitted when the focus of the code editor storing history
    changes.
    """

    def __init__(self, parent=None, configuration=None):
        """Initialization."""
        SpyderDockablePlugin.__init__(self, parent, configuration)

        # Combined with ShellConnectPluginMixin via multiple inheritance;
        # set up its state here since SpyderDockablePlugin.__init__ doesn't
        # reach it.
        ShellConnectPluginMixin.__init__(self)

    # ---- SpyderDockablePlugin API
    # ------------------------------------------------------------------------
    @staticmethod
    def get_name():
        return _('History')

    @staticmethod
    def get_description():
        return _('View command history for the IPython console.')

    @classmethod
    def get_icon(cls):
        return cls.create_icon('history')

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

    @on_plugin_teardown(plugin=Plugins.Preferences)
    def on_preferences_teardown(self):
        preferences = self.get_plugin(Plugins.Preferences)
        preferences.deregister_plugin_preferences(self)

    @on_plugin_teardown(plugin=Plugins.Console)
    def on_console_teardown(self):
        console = self.get_plugin(Plugins.Console)
        console.sig_refreshed.disconnect(self.refresh)

    def register_ipythonconsole(self, ipythonconsole):
        super().register_ipythonconsole(ipythonconsole)
        ipythonconsole.sig_append_to_history_requested.connect(
            self.append_to_history
        )

    def unregister_ipythonconsole(self, ipythonconsole):
        super().unregister_ipythonconsole(ipythonconsole)
        ipythonconsole.sig_append_to_history_requested.disconnect(
            self.append_to_history
        )

    def update_font(self):
        color_scheme = self.get_color_scheme()
        font = self.get_font(SpyderFontType.Monospace)
        self.get_widget().update_font(font, color_scheme)

    # ---- Public API
    # ------------------------------------------------------------------------
    def refresh(self):
        """
        Refresh main widget.
        """
        self.get_widget().refresh()

    def append_to_history(self, shellwidget, command):
        """
        Append a command to the history of a console.

        Parameters
        ----------
        shellwidget: spyder.plugins.ipythonconsole.widgets.ShellWidget
            Shell widget of the console where the command was entered.
        command: str
            Command to append.
        """
        self.get_widget().append_to_history(shellwidget, command)
