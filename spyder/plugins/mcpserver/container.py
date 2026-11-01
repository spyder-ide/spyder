# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""MCP server container."""

# Third-party imports
from qtpy.QtCore import Signal

# Local imports
from spyder.api.config.decorators import on_conf_change
from spyder.api.translations import _
from spyder.api.widgets.main_container import PluginMainContainer


class MCPServerActions:
    ToggleServer = "toggle_mcp_server_action"
    CopyConfig = "copy_mcp_config_action"


class MCPServerContainer(PluginMainContainer):

    sig_enabled_changed = Signal(bool)
    """
    This signal is emitted when the server is enabled or disabled.

    Parameters
    ----------
    enabled : bool
        Whether the server is enabled.
    """

    sig_copy_config_requested = Signal()
    """
    This signal is emitted to copy the configuration that agents use to
    connect to the server.
    """

    # ---- PluginMainContainer API
    # -------------------------------------------------------------------------
    def setup(self):
        self.toggle_server_action = self.create_action(
            MCPServerActions.ToggleServer,
            _("Enable MCP server for AI agents"),
            toggled=True,
            option="enabled",
        )

        self.copy_config_action = self.create_action(
            MCPServerActions.CopyConfig,
            _("Copy MCP server configuration for AI agents"),
            icon=self.create_icon("editcopy"),
            triggered=self.sig_copy_config_requested,
        )
        self.copy_config_action.setEnabled(False)

    def update_actions(self):
        pass

    # ---- Public API
    # -------------------------------------------------------------------------
    def set_server_running(self, running: bool) -> None:
        self.copy_config_action.setEnabled(running)

    # ---- Private API
    # -------------------------------------------------------------------------
    @on_conf_change(option="enabled")
    def _on_enabled_changed(self, value):
        self.sig_enabled_changed.emit(value)
