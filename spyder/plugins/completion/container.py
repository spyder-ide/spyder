# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""Spyder completion container."""

# Standard library imports

# Third-party imports
from qtpy.QtWidgets import QMessageBox

# Local imports
from spyder.api.widgets.main_container import PluginMainContainer


class CompletionContainer(PluginMainContainer):
    """Stateless class used to store graphical widgets."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.statusbar_widgets = {}

    def setup(self, options=None):
        pass

    def update_actions(self):
        pass

    def show_widget(self, Widget):
        widget = Widget(self)

        if isinstance(widget, QMessageBox):
            if hasattr(widget, 'sig_restart_spyder'):
                widget.sig_restart_spyder.connect(self.sig_restart_requested)
            widget.exec_()

    def register_statusbar_widgets(self, statusbar_classes):
        for StatusBar in statusbar_classes:
            statusbar = StatusBar(self)
            self.statusbar_widgets[statusbar.ID] = statusbar

    def all_statusbar_widgets(self):
        return [self.statusbar_widgets[k] for k in self.statusbar_widgets]

    def statusbar_rpc(self, status_key: str, method: str, args: tuple,
                      kwargs: dict):
        """
        Perform a remote call on the status bar with ID `status_key`.

        Parameters
        ----------
        status_key: str
            Identifier of the status call that should recieve the method call.
        method: str
            Name of the method.
        args: tuple
            Positional arguments of the method call.
        kwargs: dict
            Optional arguments of the method call.
        """
        statusbar = self.statusbar_widgets[status_key]
        call = getattr(statusbar, method)
        call(*args, **kwargs)
