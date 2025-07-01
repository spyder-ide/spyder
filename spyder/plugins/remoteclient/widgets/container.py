# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
#
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""Remote client container."""

# Standard library imports
from __future__ import annotations
from collections import deque
import functools

# Third-party imports
from qtpy.QtCore import Signal
from qtpy.QtWidgets import QMessageBox

# Local imports
from spyder.api.translations import _
from spyder.api.widgets.main_container import PluginMainContainer
from spyder.plugins.remoteclient import SPYDER_REMOTE_MAX_VERSION
from spyder.plugins.remoteclient.api import (
    MAX_CLIENT_MESSAGES,
    RemoteClientActions,
)
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

    sig_server_renamed = Signal(str)
    """
    This signal is used to inform that a remote server was renamed.

    Parameters
    ----------
    id: str
        Id of the server that was renamed.
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

    sig_server_changed = Signal()
    """
    Signal that a remote server was deleted or added
    """

    sig_client_message_logged = Signal(dict)
    """
    This signal is used to inform that a client has logged a connection
    message.

    Parameters
    ----------
    log: RemoteClientLog
        Dictionary that contains the log message and its metadata.
    """

    # ---- PluginMainContainer API
    # -------------------------------------------------------------------------
    def setup(self):
        # Attributes
        self.client_logs: dict[str, deque] = {}

        # Widgets
        self.create_action(
            RemoteClientActions.ManageConnections,
            _("Manage remote connections"),
            icon=self._plugin.get_icon(),
            triggered=self._show_connection_dialog,
        )

        # Signals
        self.sig_connection_status_changed.connect(
            self._on_connection_status_changed
        )
        self.sig_client_message_logged.connect(self._on_client_message_logged)

    def update_actions(self):
        pass

    # ---- Public API
    # -------------------------------------------------------------------------
    def on_server_version_mismatch(self, config_id, version: str):
        """
        Actions to take when there's a mismatch between the
        spyder-remote-services version installed in the server and the one
        supported by Spyder.
        """
        server_name = self._plugin.get_server_name(config_id)

        QMessageBox.critical(
            self,
            _("Remote server error"),
            _(
                "The version of <tt>spyder-remote-services</tt> on the "
                "remote host <b>{server}</b> (<b>{srs_version}</b>) is newer "
                "than the latest Spyder supports (<b>{max_version}</b>)."
                "<br><br>"
                "Please update Spyder to be able to connect to this host."
            ).format(
                server=server_name,
                srs_version=version,
                max_version=SPYDER_REMOTE_MAX_VERSION,
            ),
            QMessageBox.Ok,
        )

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
        connection_dialog.sig_connections_changed.connect(
            self.sig_server_changed
        )
        connection_dialog.sig_server_renamed.connect(self.sig_server_renamed)

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

    def _on_client_message_logged(self, message: dict):
        """Actions to take when a client message is logged."""
        msg_id = message["id"]

        # Create deque if not available
        if not self.client_logs.get(msg_id):
            self.client_logs[msg_id] = deque([], MAX_CLIENT_MESSAGES)

        # Add message to deque
        self.client_logs[msg_id].append(message)
