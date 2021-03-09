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
from spyder.api.translations import get_translation
from spyder.config.base import get_conf_path
from spyder.plugins.onlinehelp.widgets import PydocBrowser

# Localization
_ = get_translation('spyder')


# --- Plugin
# ----------------------------------------------------------------------------
class OnlineHelp(SpyderDockablePlugin):
    """
    Online Help Plugin.
    """

    NAME = 'onlinehelp'
    TABIFY = Plugins.Help
    CONF_SECTION = NAME
    CONF_FILE = False
    WIDGET_CLASS = PydocBrowser
    LOG_PATH = get_conf_path(NAME)

    # --- Signals
    # ------------------------------------------------------------------------
    sig_load_finished = Signal()
    """
    This signal is emitted to indicate the help page has finished loading.
    """

    # --- SpyderDockablePlugin API
    # ------------------------------------------------------------------------
    def get_name(self):
        return _('Online help')

    def get_description(self):
        return _(
            'Browse and search the currently installed modules interactively.')

    def get_icon(self):
        return self.create_icon('help')

    def on_close(self, cancelable=False):
        self.save_history()
        self.set_conf('zoom_factor',
                      self.get_widget().get_zoom_factor())
        return True

    def register(self):
        widget = self.get_widget()
        widget.load_history(self.load_history())
        widget.sig_load_finished.connect(self.sig_load_finished)

    def update_font(self):
        self.get_widget().reload()

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
