# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
#
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""Switcher Main Container."""

# Third-party imports
from qtpy.QtCore import Signal

# Spyder imports
from spyder.api.config.decorators import on_conf_change
from spyder.api.translations import _
from spyder.api.widgets.main_container import PluginMainContainer
from spyder.plugins.switcher.widgets.switcher import Switcher


class SwitcherContainer(PluginMainContainer):

    # Signals

    # Dismissed switcher
    sig_rejected = Signal()
    # Search/Filter text changes
    sig_text_changed = Signal()
    # Current item changed
    sig_item_changed = Signal()
    # List item selected, mode and cleaned search text
    sig_item_selected = Signal()
    sig_mode_selected = Signal()

    # --- PluginMainContainer API
    # ------------------------------------------------------------------------
    def setup(self):
        self.switcher = Switcher(self)
        self.switcher.sig_rejected.connect(self.sig_rejected)
        self.switcher.sig_text_changed.connect(self.sig_text_changed)
        self.switcher.sig_item_changed.connect(self.sig_item_changed)
        self.switcher.sig_item_selected.connect(self.sig_item_selected)
        self.switcher.sig_mode_selected.connect(self.sig_mode_selected)

    def update_actions(self):
        pass

    # --- Public API
    # ------------------------------------------------------------------------
