# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""Spyder completion container."""

# Standard library imports

# Third-party imports
from qtpy.QtCore import Signal
from qtpy.QtWidgets import QMessageBox

# Local imports
from spyder.api.widgets import PluginMainContainer


class CompletionContainer(PluginMainContainer):
    """Stateless class used to store graphical widgets."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.statusbars = {}

    def setup(self, options=None):
        pass

    def update_actions(self):
        pass

    def on_option_update(self, _option, _value):
        pass

    def show_widget(self, Widget):
        widget = Widget(self)

        if isinstance(widget, QMessageBox):
            if hasattr(widget, 'sig_restart_spyder'):
                widget.sig_restart_spyder.connect(self.sig_restart_requested)
            widget.exec_()

    def register_statusbars(self, statusbar_map):
        for status_key in statusbar_map:
            StatusBar = statusbar_map[status_key]
            self.statusbars[status_key] = StatusBar(self)

    def all_statusbars(self):
        return [self.statusbars[k] for k in self.statusbars]

    def statusbar_rpc(self, status_key, method, args, kwargs):
        statusbar = self.statusbars[status_key]
        call = getattr(statusbar, method)
        call(*args, **kwargs)
