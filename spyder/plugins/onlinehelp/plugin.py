# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""Online Help Plugin"""

# Standard library imports
import os.path as osp

# Third party imports
from qtpy.QtCore import Signal

# Local imports
from spyder.api.plugins import Plugins, SpyderDockablePlugin
from spyder.api.plugin_registration.decorators import on_plugin_available
from spyder.api.translations import _
from spyder.config.base import get_conf_path
from spyder.plugins.application.api import ApplicationActions
from spyder.plugins.onlinehelp.widgets import PydocBrowser


# --- Plugin
# ----------------------------------------------------------------------------
class OnlineHelp(SpyderDockablePlugin):
    """
    Online Help Plugin.
    """

    NAME = 'onlinehelp'
    REQUIRES = [Plugins.Application]
    TABIFY = [Plugins.VariableExplorer, Plugins.Help]
    CONF_SECTION = NAME
    CONF_FILE = False
    WIDGET_CLASS = PydocBrowser
    LOG_PATH = get_conf_path(NAME)
    REQUIRE_WEB_WIDGETS = True
    CAN_HANDLE_SEARCH_ACTIONS = True

    # --- Signals
    # ------------------------------------------------------------------------
    sig_load_finished = Signal()
    """
    This signal is emitted to indicate the help page has finished loading.
    """

    # --- SpyderDockablePlugin API
    # ------------------------------------------------------------------------
    @staticmethod
    def get_name():
        return _('Online help')

    @staticmethod
    def get_description():
        return _(
            "Browse and search documentation for installed Python modules "
            "interactively."
        )

    @classmethod
    def get_icon(cls):
        return cls.create_icon('online_help')

    def on_close(self, cancelable=False):
        self.save_history()
        self.set_conf('zoom_factor',
                      self.get_widget().get_zoom_factor())
        return True

    def on_initialize(self):
        widget = self.get_widget()
        widget.load_history(self.load_history())
        widget.sig_load_finished.connect(self.sig_load_finished)

    @on_plugin_available(plugin=Plugins.Application)
    def on_application_available(self):
        # Setup Search actions
        self._enable_search_action(ApplicationActions.FindText, True)
        self._enable_search_action(ApplicationActions.FindNext, True)
        self._enable_search_action(ApplicationActions.FindPrevious, True)
        # Replace action is set disabled since the `FindReplace` widget created
        # by the main widget has `enable_replace=False`
        self._enable_search_action(ApplicationActions.ReplaceText, False)

    def update_font(self):
        self.get_widget().reload()

    # --- Private API
    # ------------------------------------------------------------------------
    def _enable_search_action(self, action_name: str, enabled: bool) -> None:
        """Enable or disable search action for this plugin."""
        application = self.get_plugin(Plugins.Application, error=False)
        if application:
            application.enable_search_action(action_name, enabled, self.NAME)

    # --- Public API
    # ------------------------------------------------------------------------
    def load_history(self):
        """
        Load history from a text file in the Spyder configuration directory.
        """
        if osp.isfile(self.LOG_PATH):
            with open(self.LOG_PATH, 'r') as fh:
                lines = fh.read().split('\n')

            history = [line.replace('\n', '') for line in lines]
        else:
            history = []

        return history

    def save_history(self):
        """
        Save history to a text file in the Spyder configuration directory.
        """
        data = "\n".join(self.get_widget().get_history())
        with open(self.LOG_PATH, 'w') as fh:
            fh.write(data)

    def find(self) -> None:
        find_widget = self.get_widget().find_widget
        find_widget.show()
        find_widget.search_text.setFocus()

    def find_next(self) -> None:
        self.get_widget().find_widget.find_next()

    def find_previous(self) -> None:
        self.get_widget().find_widget.find_previous()
