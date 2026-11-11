# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""Container of the legacy completion plugin."""

# Third-party imports
from qtpy.QtWidgets import QMessageBox

# Local imports
from spyder.api.widgets.main_container import PluginMainContainer


class CompletionContainer(PluginMainContainer):
    """Hosts the dialogs legacy providers ask to show."""

    def setup(self, options=None):
        pass

    def update_actions(self):
        pass

    def show_widget(self, Widget):
        """Show a dialog built by ``Widget(parent)``."""
        widget = Widget(self)

        if isinstance(widget, QMessageBox):
            if hasattr(widget, 'sig_restart_spyder'):
                widget.sig_restart_spyder.connect(self.sig_restart_requested)
            widget.exec_()
