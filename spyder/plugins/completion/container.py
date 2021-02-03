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
from spyder.api.widgets import PluginMainContainer


class CompletionContainer(PluginMainContainer):
    """Stateless class used to store graphical widgets."""

    def setup(self, options=None):
        pass

    def update_actions(self):
        pass

    def on_option_update(self, _option, _value):
        pass

    def show_widget(self, Widget):
        widget = Widget(self)

        if isinstance(widget, QMessageBox):
            widget.exec_()
