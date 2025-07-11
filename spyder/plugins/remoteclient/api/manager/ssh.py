# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""
spyder.plugins.remoteclient.api.manager
=======================================

Remote Client Plugin API Manager.
"""

from __future__ import annotations

import asyncio
import json

import asyncssh
from packaging.version import Version

from spyder.api.translations import _
from spyder.plugins.remoteclient import (
    SPYDER_REMOTE_MAX_VERSION,
    SPYDER_REMOTE_MIN_VERSION,
)
from spyder.plugins.remoteclient.api.manager.base import (
    SpyderRemoteAPIManagerBase,
)
from spyder.plugins.remoteclient.api.protocol import (
    ConnectionStatus,
    SSHClientOptions,
)
from spyder.plugins.remoteclient.api.ssh import SpyderSSHClient
from spyder.plugins.remoteclient.utils.installation import (
    SERVER_ENV,
    get_installer_command,
    get_server_version_command,
)


class SpyderRemoteSSHAPIManager(SpyderRemoteAPIManagerBase):
    """Class to manage a remote SSH server and its APIs."""

    _extra_options = ["platform", "id", "default_kernel_spec"]

    START_SERVER_COMMAND = (
        f"/${{HOME}}/.local/bin/micromamba run -n {SERVER_ENV} spyder-server"
    )
    GET_SERVER_INFO_COMMAND = (
        f"/${{HOME}}/.local/bin/micromamba run"
        f" -n {SERVER_ENV} spyder-server info"
    )

    def __init__(self, conf_id, options: SSHClientOptions, _plugin=None):
        super().__init__(conf_id, options, _plugin)

        self._ssh_connection: asyncssh.SSHClientConnection = None
        self._remote_server_process: asyncssh.SSHClientProcess = None
        self._port_forwarder: asyncssh.SSHListener = None
        self._server_info = {}
        self._local_port = None

    @property
    def api_token(self):
        return self._server_info.get("token")

    @property
    def server_port(self):
        return self._server_info.get("port")

    @property
    def server_pid(self):
        return self._server_info.get("pid")

    @property
    def port_is_forwarded(self):
        """Check if local port is forwarded."""
        return self._port_forwarder is not None

    @property
    def server_url(self):
        if not self._local_port:
            raise ValueError("Local port is not set")
        return f"http://127.0.0.1:{self._local_port}"

    @property
    def peer_host(self):
        if self._ssh_connection is not None:
            return self._ssh_connection.get_extra_info("peername")[0]
        else:
            return None

    @property
    def peer_port(self):
        if not self.connected:
            return None

        return self._ssh_connection.get_extra_info("peername")[1]

    @property
    def peer_username(self):
        if not self.connected:
            return None

        return self._ssh_connection.get_extra_info("username")

    @property
    def client_factory(self):
        """Return the client factory."""
        return lambda: SpyderSSHClient(self)

    async def get_server_info(self):
        """Check if the remote server is running."""
        if self._ssh_connection is None:
            self.logger.debug("ssh connection was not established")
            return None

        try:
            output = await self._ssh_connection.run(
                self.GET_SERVER_INFO_COMMAND, check=True
            )
        except asyncssh.TimeoutError:
            self.logger.error("Getting server info timed out")
            return None
        except asyncssh.misc.ChannelOpenError:
            self.logger.error(
                "The connection is closed, so it's not possible to get the "
                "server info"
            )
            return None
        except asyncssh.ProcessError as err:
            self.logger.debug(f"Error getting server info: {err.stderr}")
            return None

        try:
            info = json.loads(output.stdout.splitlines()[-1])
        except (json.JSONDecodeError, IndexError):
            self.logger.debug(f"Issue parsing server info: {output.stdout}")
            return None

        return info

    async def _start_remote_server(self):
        """Start remote server."""
        if not self.connected:
            self.logger.error("SSH connection is not open")
            self._emit_connection_status(
                ConnectionStatus.Error,
                _("The SSH connection is not open"),
            )
            return False

        if info := await self.get_server_info():
            self.logger.warning(
                f"Remote server is already running for {self.peer_host}"
            )

            self.logger.debug("Checking server info")
            if self._server_info != info:
                self._server_info = info
                self.logger.info(
                    "Different server info, updating info "
                    f"for {self.peer_host}"
                )
                if await self.forward_local_port():
                    self._emit_connection_status(
                        ConnectionStatus.Active,
                        _("The connection was established successfully"),
                    )
                    return True

                self.logger.error(
                    "Error forwarding local port, server might not be "
                    "reachable"
                )
                self._emit_connection_status(
                    ConnectionStatus.Error,
                    _("It was not possible to forward the local port"),
                )

            self._emit_connection_status(
                ConnectionStatus.Active,
                _("The connection was established successfully"),
            )

            return True

        self.logger.debug(f"Starting remote server for {self.peer_host}")
        try:
            self._remote_server_process = (
                await self._ssh_connection.create_process(
                    self.START_SERVER_COMMAND,
                    stderr=asyncssh.STDOUT,
                )
            )
        except (OSError, asyncssh.Error, ValueError) as e:
            self.logger.error(f"Error starting remote server: {e}")
            self._remote_server_process = None
            self._emit_connection_status(
                ConnectionStatus.Error, _("Error starting the remote server")
            )
            return False

        _time = 0
        while (info := await self.get_server_info()) is None and _time < 5:
            await asyncio.sleep(1)
            _time += 1

        if info is None:
            self.logger.error("Faield to get server info")
            self._emit_connection_status(
                ConnectionStatus.Error,
                _(
                    "There was an error when trying to get the remote server "
                    "information"
                ),
            )
            return False

        self._server_info = info

        self.logger.info(
            f"Remote server started for {self.peer_host} at port "
            f"{self.server_port}"
        )

        if await self.forward_local_port():
            self._emit_connection_status(
                ConnectionStatus.Active,
                _("The connection was established successfully"),
            )
            return True

        self.logger.error("Error forwarding local port.")
        self._emit_connection_status(
            ConnectionStatus.Error,
            _("It was not possible to forward the local port"),
        )
        return False

    async def ensure_server_installed(self) -> bool:
        """Check remote server version."""
        if not self.connected:
            self.logger.error("SSH connection is not open")
            self._emit_connection_status(
                ConnectionStatus.Error,
                _("The SSH connection is not open"),
            )
            return False

        commnad = get_server_version_command(self.options["platform"])

        try:
            output = await self._ssh_connection.run(commnad, check=True)
        except asyncssh.ProcessError as err:
            # Server is not installed
            self.logger.warning(f"Issue checking server version: {err.stderr}")
            return await self.install_remote_server()

        version = output.stdout.splitlines()[-1].strip()

        if Version(version) >= Version(SPYDER_REMOTE_MAX_VERSION):
            self.logger.error(
                f"Server version mismatch: {version} is greater than "
                f"the maximum supported version {SPYDER_REMOTE_MAX_VERSION}"
            )
            self._emit_version_mismatch(version)
            self._emit_connection_status(
                status=ConnectionStatus.Error,
                message=_("Error connecting to the remote server"),
            )
            return False

        if Version(version) < Version(SPYDER_REMOTE_MIN_VERSION):
            self.logger.warning(
                f"Server version mismatch: {version} is lower than "
                f"the minimum supported version {SPYDER_REMOTE_MIN_VERSION}. "
                f"A more recent version will be installed."
            )
            return await self.install_remote_server()

        self.logger.info(f"Supported Server version: {version}")

        return True

    async def _install_remote_server(self):
        """Install remote server."""
        if not self.connected:
            self.logger.error("SSH connection is not open")
            self._emit_connection_status(
                ConnectionStatus.Error,
                _("The SSH connection is not open"),
            )
            return False

        self.logger.debug(
            f"Installing spyder-remote-server on {self.peer_host}"
        )

        try:
            command = get_installer_command(self.options["platform"])
        except NotImplementedError:
            self.logger.exception(
                f"Cannot install spyder-remote-server on "
                f"{self.options['platform']} automatically. Please install it "
                f"manually."
            )
            self._emit_connection_status(
                status=ConnectionStatus.Error,
                message=_("There was an error installing the remote server"),
            )
            return False

        try:
            await self._ssh_connection.run(command, check=True)
        except asyncssh.ProcessError as err:
            self.logger.exception(f"Installation script failed: {err.stderr}")
            self._emit_connection_status(
                status=ConnectionStatus.Error,
                message=_("There was an error installing the remote server"),
            )
            return False

        self.logger.info(
            f"Successfully installed spyder-remote-server on {self.peer_host}"
        )

        return True

    async def _create_new_connection(self) -> bool:
        """Creates a new SSH connection to the remote server machine.

        Args
        ----
        options: dict[str, str]
            The options to use for the SSH connection.

        Returns
        -------
        bool
            True if the connection was successful, False otherwise.
        """
        if self.connected:
            self.logger.debug(
                f"Atempting to create a new connection with an existing for "
                f"{self.peer_host}"
            )
            await self.close_connection()

        self._emit_connection_status(
            ConnectionStatus.Connecting,
            _("We're establishing the connection. Please be patient"),
        )

        connect_kwargs = {
            k: v
            for k, v in self.options.items()
            if k not in self._extra_options
        }
        self.logger.debug("Opening SSH connection")
        try:
            self._ssh_connection = await asyncssh.connect(
                **connect_kwargs, client_factory=self.client_factory
            )
        except (OSError, asyncssh.Error) as e:
            self.logger.error(f"Failed to open ssh connection: {e}")
            self._emit_connection_status(
                ConnectionStatus.Error,
                _("It was not possible to open a connection to this machine"),
            )
            return False

        self.logger.info(f"SSH connection opened for {self.peer_host}")

        return True

    async def forward_local_port(self):
        """Forward local port."""
        if not self.server_port:
            self.logger.error("Server port is not set")
            self._emit_connection_status(
                status=ConnectionStatus.Error,
                message=_("The server port is not set"),
            )
            return False

        if not self.connected:
            self.logger.error("SSH connection is not open")
            self._emit_connection_status(
                status=ConnectionStatus.Error,
                message=_("The SSH connection is not open"),
            )
            return False

        self.logger.debug(
            f"Forwarding an free local port to remote port {self.server_port}"
        )

        if self._port_forwarder:
            self.logger.warning(
                f"Port forwarder is already open for host {self.peer_host} "
                f"with local port {self._local_port} and remote port "
                f"{self.server_port}"
            )
            await self.close_port_forwarder()

        local_port = self.get_free_port()

        server_host = self._server_info["hostname"]

        self._port_forwarder = await self._ssh_connection.forward_local_port(
            "",
            local_port,
            server_host,
            self.server_port,
        )

        self._local_port = local_port

        self.logger.debug(
            f"Forwarded local port {local_port} to remote server at "
            f"{server_host}:{self.server_port}"
        )

        return True

    async def close_port_forwarder(self):
        """Close port forwarder."""
        if self.port_is_forwarded:
            self.logger.debug(
                f"Closing port forwarder for host {self.peer_host} with local "
                f"port {self._local_port}"
            )
            self._port_forwarder.close()
            await self._port_forwarder.wait_closed()
            self._port_forwarder = None
            self.logger.debug(
                f"Port forwarder closed for host {self.peer_host} with local "
                f"port {self._local_port}"
            )

    async def close_connection(self):
        """Close SSH connection."""
        if not self.connected:
            self.logger.debug("SSH connection is not open")
            return

        await self.close_port_forwarder()
        self.logger.debug(f"Closing SSH connection for {self.peer_host}")
        self._ssh_connection.close()
        await self._ssh_connection.wait_closed()
        self._ssh_connection = None
        self.logger.info("SSH connection closed")
        self._reset_connection_stablished()
        self._emit_connection_status(
            ConnectionStatus.Inactive,
            _("The connection was closed successfully"),
        )
