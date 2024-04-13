# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
#
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""Remote client container."""

from qtpy.QtCore import Signal

from spyder.api.translations import _
from spyder.api.widgets.main_container import PluginMainContainer
from spyder.plugins.remoteclient.api import RemoteClientActions
from spyder.plugins.remoteclient.api.protocol import ConnectionInfo
from spyder.plugins.remoteclient.widgets.connectiondialog import (
    ConnectionDialog,
)


class RemoteClientContainer(PluginMainContainer):

    sig_start_server_requested = Signal(str)
    """
    This signal is used to request starting a remote server.

    Parameters
    ----------
    id: str
        Id of the server that will be started.
    """

    sig_stop_server_requested = Signal(str)
    """
    This signal is used to request stopping a remote server.

    Parameters
    ----------
    id: str
        Id of the server that will be stopped.
    """

    sig_connection_status_changed = Signal(dict)
    """
    This signal is used to update the status of a given connection.

    Parameters
    ----------
    info: ConnectionInfo
        Dictionary with the necessary info to update the status of a
        connection.
    """

    # ---- PluginMainContainer API
    # -------------------------------------------------------------------------
    def setup(self):

        self.create_action(
            RemoteClientActions.ManageConnections,
            _('Manage remote connections...'),
            icon=self._plugin.get_icon(),
            triggered=self._show_connection_dialog,
        )

        self.sig_connection_status_changed.connect(
            self._on_connection_status_changed
        )

    def update_actions(self):
        pass

    # ---- Private API
    # -------------------------------------------------------------------------
    def _show_connection_dialog(self):
        connection_dialog = ConnectionDialog(self)

        connection_dialog.sig_start_server_requested.connect(
            self.sig_start_server_requested
        )
        connection_dialog.sig_stop_server_requested.connect(
            self.sig_stop_server_requested
        )

        self.sig_connection_status_changed.connect(
            connection_dialog.sig_connection_status_changed
        )

        connection_dialog.show()

    def _on_connection_status_changed(self, info: ConnectionInfo):
        """Handle changes in connection status."""
        host_id = info["id"]
        status = info["status"]
        message = info["message"]

        # We need to save this info so that we can show the current status in
        # the connection dialog when it's closed and opened again.
        self.set_conf(f"{host_id}/status", status)
        self.set_conf(f"{host_id}/status_message", message)
