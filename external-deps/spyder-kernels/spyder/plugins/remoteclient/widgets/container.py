# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
#
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""Remote client container."""

import json

from qtpy.QtCore import Signal

from spyder.api.translations import _
from spyder.api.widgets.main_container import PluginMainContainer
from spyder.plugins.ipythonconsole.utils.kernel_handler import KernelHandler
from spyder.plugins.remoteclient.api import (
    RemoteClientActions,
    RemoteClientMenus,
    RemoteConsolesMenuSections,
)
from spyder.plugins.remoteclient.api.protocol import ConnectionInfo
from spyder.plugins.remoteclient.widgets import AuthenticationMethod
from spyder.plugins.remoteclient.widgets.connectiondialog import (
    ConnectionDialog,
)
from spyder.utils.workers import WorkerManager


class RemoteClientContainer(PluginMainContainer):

    _sig_kernel_restarted = Signal((object, bool), (object, dict))
    """
    This private signal is used to inform that a kernel restart took place in
    the server.

    Parameters
    ----------
    ipyclient: ClientWidget
        An IPython console client widget (the first parameter in both
        signatures).
    response: bool or dict
        Response returned by the server. It can a bool when the kernel is
        restarted by the user (signature 1) or a dict when it's restarted
        automatically after it dies while running some code or it's killed (
        signature 2).
    """

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

    sig_create_ipyclient_requested = Signal(str)
    """
    This signal is used to request starting an IPython console client for a
    remote server.

    Parameters
    ----------
    id: str
        Id of the server for which a client will be created.
    """

    sig_shutdown_kernel_requested = Signal(str, str)
    """
    This signal is used to request shutting down a kernel.

    Parameters
    ----------
    id: str
        Id of the server for which a kernel shutdown will be requested.
    kernel_id: str
        Id of the kernel which will be shutdown in the server.
    """

    sig_interrupt_kernel_requested = Signal(str, str)
    """
    This signal is used to request interrupting a kernel.

    Parameters
    ----------
    id: str
        Id of the server for which a kernel interrupt will be requested.
    kernel_id: str
        Id of the kernel which will be shutdown in the server.
    """

    # ---- PluginMainContainer API
    # -------------------------------------------------------------------------
    def setup(self):
        # Widgets
        self.create_action(
            RemoteClientActions.ManageConnections,
            _('Manage remote connections...'),
            icon=self._plugin.get_icon(),
            triggered=self._show_connection_dialog,
        )

        self._remote_consoles_menu = self.create_menu(
            RemoteClientMenus.RemoteConsoles,
            _("New console in remote server")
        )

        # Signals
        self.sig_connection_status_changed.connect(
            self._on_connection_status_changed
        )
        self._sig_kernel_restarted[object, bool].connect(
            self._on_kernel_restarted
        )
        self._sig_kernel_restarted[object, dict].connect(
            self._on_kernel_restarted_after_died
        )

        # Worker manager to open ssh tunnels in threads
        self._worker_manager = WorkerManager(max_threads=5)

    def update_actions(self):
        pass

    def on_close(self):
        self._worker_manager.terminate_all()

    # ---- Public API
    # -------------------------------------------------------------------------
    def setup_remote_consoles_submenu(self, render=True):
        """Create the remote consoles submenu in the Consoles app one."""
        self._remote_consoles_menu.clear_actions()

        self.add_item_to_menu(
            self.get_action(RemoteClientActions.ManageConnections),
            menu=self._remote_consoles_menu,
            section=RemoteConsolesMenuSections.ManagerSection
        )

        servers = self.get_conf("servers", default={})
        for config_id in servers:
            auth_method = self.get_conf(f"{config_id}/auth_method")
            name = self.get_conf(f"{config_id}/{auth_method}/name")

            action = self.create_action(
                name=config_id,
                text=f"New console in {name} server",
                icon=self.create_icon('ipython_console'),
                triggered=(
                    lambda checked, config_id=config_id:
                    self.sig_create_ipyclient_requested.emit(config_id)
                ),
                overwrite=True
            )
            self.add_item_to_menu(
                action,
                menu=self._remote_consoles_menu,
                section=RemoteConsolesMenuSections.ConsolesSection
            )

        # This is necessary to reposition the menu correctly when rebuilt
        if render:
            self._remote_consoles_menu.render()

    def on_kernel_started(self, ipyclient, kernel_info):
        """
        Actions to take when a remote kernel was started for an IPython console
        client.
        """
        config_id = ipyclient.server_id

        # It's only at this point that we can allow users to close the client.
        ipyclient.can_close = True

        # Get authentication method
        auth_method = self.get_conf(f"{config_id}/auth_method")

        # Handle failures to launch a kernel
        if not kernel_info:
            name = self.get_conf(f"{config_id}/{auth_method}/name")
            ipyclient.show_kernel_error(
                _(
                    "There was an error connecting to the server <b>{}</b>"
                ).format(name)
            )
            return

        # Connect client's signals
        ipyclient.kernel_id = kernel_info["id"]
        self._connect_ipyclient_signals(ipyclient)

        # Set hostname in the format expected by KernelHandler
        address = self.get_conf(f"{config_id}/{auth_method}/address")
        username = self.get_conf(f"{config_id}/{auth_method}/username")
        port = self.get_conf(f"{config_id}/{auth_method}/port")
        hostname = f"{username}@{address}:{port}"

        # Get password or keyfile/passphrase
        if auth_method == AuthenticationMethod.Password:
            password = self.get_conf(f"{config_id}/password", secure=True)
            sshkey = None
        elif auth_method == AuthenticationMethod.KeyFile:
            sshkey = self.get_conf(f"{config_id}/{auth_method}/keyfile")
            passpharse = self.get_conf(f"{config_id}/passpharse", secure=True)
            if passpharse:
                password = passpharse
            else:
                password = None
        else:
            # TODO: Handle the ConfigFile method here
            pass

        # Generate local connection file from kernel info
        connection_file = KernelHandler.new_connection_file()
        with open(connection_file, "w") as f:
            json.dump(kernel_info["connection_info"], f)

        # Open tunnel to the kernel. Connecting the ipyclient to the kernel
        # will be finished after that takes place.
        self._open_tunnel_to_kernel(
            ipyclient, connection_file, hostname, sshkey, password
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
            self.setup_remote_consoles_submenu
        )
        connection_dialog.sig_server_renamed.connect(
            self.sig_server_renamed
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

    def _connect_ipyclient_signals(self, ipyclient):
        """
        Connect the signals to shutdown, interrupt and restart the kernel of an
        IPython console client to the signals and methods declared here for
        remote kernel management.
        """
        ipyclient.sig_shutdown_kernel_requested.connect(
            self.sig_shutdown_kernel_requested
        )
        ipyclient.sig_interrupt_kernel_requested.connect(
            self.sig_interrupt_kernel_requested
        )
        ipyclient.sig_restart_kernel_requested.connect(
            lambda: self._request_kernel_restart(ipyclient)
        )
        ipyclient.sig_kernel_died.connect(
            lambda: self._get_kernel_info(ipyclient)
        )

    def _open_tunnel_to_kernel(
        self,
        ipyclient,
        connection_file,
        hostname,
        sshkey,
        password,
        restart=False,
        clear=True,
    ):
        """
        Open an SSH tunnel to a remote kernel.

        Notes
        -----
        * We do this in a worker to avoid blocking the UI.
        """
        with open(connection_file, "r") as f:
            connection_info = json.load(f)

        worker = self._worker_manager.create_python_worker(
            KernelHandler.tunnel_to_kernel,
            connection_info,
            hostname,
            sshkey,
            password,
        )

        # Save variables necessary to make the connection in the worker
        worker.ipyclient = ipyclient
        worker.connection_file = connection_file
        worker.hostname = hostname
        worker.sshkey = sshkey
        worker.password = password
        worker.restart = restart
        worker.clear = clear

        # Start worker
        worker.sig_finished.connect(self._finish_kernel_connection)
        worker.start()

    def _finish_kernel_connection(self, worker, output, error):
        """Finish connecting an IPython console client to a remote kernel."""
        # Handle errors
        if error:
            worker.ipyclient.show_kernel_error(str(error))
            return

        # Create KernelHandler
        kernel_handler = KernelHandler.from_connection_file(
            worker.connection_file,
            worker.hostname,
            worker.sshkey,
            worker.password,
            kernel_ports=output,
        )

        # Connect client to the kernel
        if not worker.restart:
            worker.ipyclient.connect_kernel(kernel_handler)
        else:
            worker.ipyclient.replace_kernel(
                kernel_handler, shutdown_kernel=False, clear=worker.clear
            )

    def _request_kernel_restart(self, ipyclient):
        """
        Request a kernel restart to the server for an IPython console client
        and handle its response.
        """
        future = self._plugin._restart_kernel(
            ipyclient.server_id, ipyclient.kernel_id
        )

        future.add_done_callback(
            lambda future: self._sig_kernel_restarted[object, bool].emit(
                ipyclient, future.result()
            )
        )

    def _on_kernel_restarted(self, ipyclient, response, clear=True):
        """Actions to take when the kernel was restarted by the server."""
        if response:
            kernel_handler = ipyclient.kernel_handler
            self._open_tunnel_to_kernel(
                ipyclient,
                kernel_handler.connection_file,
                kernel_handler.hostname,
                kernel_handler.sshkey,
                kernel_handler.password,
                restart=True,
                clear=clear,
            )
        else:
            ipyclient.kernel_restarted_failure_message()

    def _get_kernel_info(self, ipyclient):
        """
        Get kernel info corresponding to an IPython console client from the
        server.

        If we get a response, it means the kernel is alive.
        """
        future = self._plugin._get_kernel_info(
            ipyclient.server_id, ipyclient.kernel_id
        )

        future.add_done_callback(
            lambda future: self._sig_kernel_restarted[object, dict].emit(
                ipyclient, future.result()
            )
        )

    def _on_kernel_restarted_after_died(self, ipyclient, response):
        """
        Actions to take when the kernel was automatically restarted after it
        died.
        """
        # We don't clear the console in this case because it can contain
        # important results that users would like to check
        self._on_kernel_restarted(ipyclient, response, clear=False)
