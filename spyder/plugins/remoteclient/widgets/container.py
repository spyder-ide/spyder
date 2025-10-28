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

# Third-party imports
from qtpy import PYSIDE2, PYSIDE6
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

    sig_server_updated = Signal(str)
    """
    This signal is used to inform that a remote server was updated.
    Parameters
    ----------
    id: str
        Id of the server that was updated.
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
        self._connection_dialog = None

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

        def _dialog_finished(result_code):
            """Restore dialog instance variable."""
            if PYSIDE2 or PYSIDE6:
                self._connection_dialog.disconnect(None, None, None)
            else:
                self._connection_dialog.disconnect()

            self._connection_dialog = None

        if self._connection_dialog is None:
            # Create dialog
            self._connection_dialog = dlg = ConnectionDialog(self)

            # Connect signals
            dlg.sig_start_server_requested.connect(
                self.sig_start_server_requested
            )
            dlg.sig_stop_server_requested.connect(
                self.sig_stop_server_requested
            )
            dlg.sig_abort_connection_requested.connect(
                self._plugin._abort_connection
            )
            dlg.sig_connections_changed.connect(self.sig_server_changed)
            dlg.sig_server_renamed.connect(self.sig_server_renamed)
            dlg.sig_server_updated.connect(self.sig_server_updated)
            dlg.sig_create_env_requested.connect(
                self._plugin.sig_create_env_requested
            )
            dlg.sig_import_env_requested.connect(
                self._plugin.sig_import_env_requested
            )

            # Destroy dialog after it's closed
            dlg.finished.connect(_dialog_finished)

            # Show dialog
            dlg.show()
        else:
            self._connection_dialog.show()
            self._connection_dialog.activateWindow()
            self._connection_dialog.raise_()
            self._connection_dialog.setFocus()

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
