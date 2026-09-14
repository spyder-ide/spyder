# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""Container hosting the language services status bar widgets."""

from __future__ import annotations

# Third-party imports
from lsprotocol import types as lsp
from qtpy.QtWidgets import QMessageBox

# Local imports
from spyder.api.widgets.main_container import PluginMainContainer


class LanguageServicesContainer(PluginMainContainer):
    """Owner of the status bar widgets created for providers."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.statusbar_widgets = {}
        self.provider_statusbars: dict[str, list[str]] = {}

    def setup(self, options=None):
        pass

    def update_actions(self):
        pass

    def show_widget(self, Widget):
        """Show a dialog built by ``Widget(parent)``."""
        widget = Widget(self)
        if isinstance(widget, QMessageBox):
            if hasattr(widget, "sig_restart_spyder"):
                widget.sig_restart_spyder.connect(self.sig_restart_requested)
            widget.exec_()

    def show_message(self, params: lsp.ShowMessageParams):
        """Show a ``window/showMessage`` notification in a message box."""
        icons = {
            lsp.MessageType.Error: QMessageBox.Critical,
            lsp.MessageType.Warning: QMessageBox.Warning,
            lsp.MessageType.Info: QMessageBox.Information,
        }
        box = QMessageBox(self)
        box.setIcon(icons.get(params.type, QMessageBox.NoIcon))
        box.setWindowTitle("Spyder")
        box.setText(params.message)
        box.exec_()

    def register_statusbar_widgets(self, statusbar_classes, provider):
        """Instantiate ``statusbar_classes`` for ``provider`` and return
        their ids."""
        ids = []
        for StatusBar in statusbar_classes:
            statusbar = StatusBar(self, provider)
            self.statusbar_widgets[statusbar.ID] = statusbar
            ids.append(statusbar.ID)
        self.provider_statusbars[provider.NAME] = ids
        return ids

    def all_statusbar_widgets(self):
        return list(self.statusbar_widgets.values())

    def remove_statusbar_widget(self, status_key):
        self.statusbar_widgets.pop(status_key, None)

    def get_provider_statusbar_keys(self, provider_name):
        return self.provider_statusbars.get(provider_name, [])
