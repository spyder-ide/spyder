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
import logging
import sys

# Third-party imports
import keyring
from qtpy import PYSIDE2, PYSIDE6
from qtpy.QtCore import Signal
from qtpy.QtWidgets import QMessageBox

# Local imports
from spyder.api.asyncdispatcher import AsyncDispatcher
from spyder.api.plugins import Plugins
from spyder.api.translations import _
from spyder.api.widgets.main_container import PluginMainContainer
from spyder.plugins.ipythonconsole.api import (
    IPythonConsoleWidgetActions,
    IPythonConsoleWidgetMenus,
    IPythonConsoleWidgetTabsContextMenuSections,
)
from spyder.plugins.remoteclient import SPYDER_REMOTE_MAX_VERSION
from spyder.plugins.remoteclient.api import (
    MAX_CLIENT_MESSAGES,
    RemoteClientActions,
    RemoteClientMenus,
    RemoteConsolesMenuSections,
)
from spyder.plugins.remoteclient.api.protocol import ConnectionInfo
from spyder.plugins.remoteclient.widgets.connectiondialog import (
    ConnectionDialog,
)


# Logging
logger = logging.getLogger(__name__)


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
        self._keyring_checked = False
        self._keyring_fails = False
        self._remote_consoles_menu = None

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
        self.sig_server_changed.connect(self.setup_remote_consoles_submenu)

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

    def setup_remote_consoles_submenu(self, render=True):
        """Create the remote consoles submenu in the Consoles app one."""
        ipyconsole = self._plugin.get_plugin(Plugins.IPythonConsole)

        self._remote_consoles_menu = self.create_menu(
            RemoteClientMenus.RemoteConsoles,
            _("New console in remote server")
        )

        self._remote_consoles_menu.clear_actions()

        self.add_item_to_menu(
            self.get_action(RemoteClientActions.ManageConnections),
            menu=self._remote_consoles_menu,
            section=RemoteConsolesMenuSections.ManagerSection,
        )

        for config_id in self._plugin.get_config_ids():
            name = self._plugin.get_server_name(config_id)

            action = self.create_action(
                name=config_id,
                text=f"New console in {name} server",
                icon=self.create_icon("ipython_console"),
                triggered=functools.partial(
                    ipyconsole.create_client_for_server,
                    config_id,
                ),
                overwrite=True,
            )
            self.add_item_to_menu(
                action,
                menu=self._remote_consoles_menu,
                section=RemoteConsolesMenuSections.ConsolesSection,
            )

        self.add_item_to_menu(
            self._remote_consoles_menu,
            self.get_menu(
                IPythonConsoleWidgetMenus.TabsContextMenu,
                plugin=Plugins.IPythonConsole,
            ),
            section=IPythonConsoleWidgetTabsContextMenuSections.Consoles,
            before=IPythonConsoleWidgetActions.ConnectToKernel,
        )

        # This is necessary to reposition the menu correctly when rebuilt
        if render:
            self._remote_consoles_menu.render()

    def setup_server_consoles_submenu(self, config_id: str):
        """Add remote kernel specs to the remote consoles submenu."""
        if self._remote_consoles_menu is None:
            self._remote_consoles_menu = self.create_menu(
                RemoteClientMenus.RemoteConsoles,
                _("New console in remote server")
            )

        for action in self._remote_consoles_menu.get_actions():
            action_id = getattr(action, "action_id", None)
            if (
                action_id is None
                or action_id == config_id
                or not action_id.startswith(config_id)
            ):
                continue

            self._remote_consoles_menu.remove_action(action_id)

        server_name = self._plugin.get_server_name(config_id)

        self.__get_remote_kernel_specs(config_id).connect(
            self.__add_kernels_specs_callback(config_id, server_name),
        )

    def clear_server_consoles_submenu(self, config_id: str):
        """Clear the remote consoles submenu."""
        if self._remote_consoles_menu is None:
            return

        for action in self._remote_consoles_menu.get_actions():
            action_id = getattr(action, "action_id", None)
            if (
                action_id is None
                or action_id == config_id
                or not action_id.startswith(config_id)
            ):
                continue

            self._remote_consoles_menu.remove_action(action.action_id)

    # ---- Private API
    # -------------------------------------------------------------------------
    def _show_connection_dialog(self):
        # Check if it's possible to save credentials securely before showing
        # the dialog.
        # Fixes spyder-ide/spyder#25635
        if sys.platform.startswith("linux"):
            # This only happens on Linux because users cannot have installed
            # the packages needed by keyring.
            if not self._keyring_checked:
                # We only need to do this check once per session
                kr = keyring.get_keyring()
                if isinstance(kr, keyring.backends.fail.Keyring):
                    self._keyring_fails = True

                self._keyring_checked = True

            if self._keyring_fails:
                QMessageBox.critical(
                    self,
                    _("Remote connections error"),
                    _(
                        "This functionality is not available in your system "
                        "because it's not possible to save your server "
                        "credentials securely.<br><br>"
                        "Please install <tt>kwallet</tt> or "
                        "<tt>libsecret</tt> and restart Spyder to enable it."
                    ),
                    QMessageBox.Ok,
                )
                return

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

    @AsyncDispatcher(loop="asyncssh")
    async def __get_remote_kernel_specs(self, config_id: str):
        """Get kernel specs from remote Jupyter API."""
        async with self._plugin.get_jupyter_api(
            config_id
        ) as jupyter_api:
            return (
                await jupyter_api.list_kernel_specs(),
                jupyter_api.manager.options.get("default_kernel_spec")
            )

    def __add_kernels_specs_callback(self, config_id: str, server_name: str):
        """Callback to add remote kernel specs."""
        @AsyncDispatcher.QtSlot
        def callback(future):
            try:
                result = future.result()
                if result[0]:
                    self._add_remote_kernel_spec_action(
                        config_id, server_name, *result,
                    )
            except Exception:
                logger.exception("Failed to get remote kernel specs")

        return callback

    def _add_remote_kernel_spec_action(
        self,
        config_id: str,
        server_name: str,
        kernel_specs: dict,
        default_spec_name: str | None = None,
    ):
        """Add remote kernel spec actions to the remote consoles submenu."""
        default_spec_name = default_spec_name or kernel_specs['default']
        for spec_name, spec_info in kernel_specs['kernelspecs'].items():
            if spec_name == default_spec_name:
                # Skip the default kernel spec, as it is already handled by the
                # default action in the remote consoles menu.
                continue

            # Create an action for each kernel spec
            spec_display_name = (
                spec_info["spec"].get("display_name")
                or spec_info["name"]
            )
            action = self.create_action(
                name=f"{config_id}_{spec_name}",
                text=f"{spec_display_name} ({server_name})",
                tip=(f"New console with {spec_display_name}"
                     f" at {server_name} server"),
                icon=self.create_icon("ipython_console"),
                triggered=functools.partial(
                    self.create_ipyclient_for_server,
                    config_id,
                    spec_name,
                ),
                overwrite=True,
            )
            self.add_item_to_menu(
                action,
                menu=self._remote_consoles_menu,
                section=RemoteConsolesMenuSections.ConsolesSection,
            )

        self._remote_consoles_menu.render()
