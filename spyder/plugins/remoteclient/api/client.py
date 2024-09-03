# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

from __future__ import annotations
import asyncio
import json
import logging
import socket

import asyncssh

from spyder.api.translations import _
from spyder.config.base import get_debug_level
from spyder.plugins.remoteclient.api.jupyterhub import JupyterAPI
from spyder.plugins.remoteclient.api.protocol import (
    ConnectionInfo,
    ConnectionStatus,
    KernelConnectionInfo,
    KernelInfo,
    RemoteClientLog,
    SSHClientOptions,
)
from spyder.plugins.remoteclient.api.ssh import SpyderSSHClient
from spyder.plugins.remoteclient.utils.installation import (
    get_installer_command,
    SERVER_ENV,
)


class SpyderRemoteClientLoggerHandler(logging.Handler):
    def __init__(self, client, *args, **kwargs):
        self._client = client
        super().__init__(*args, **kwargs)

        log_format = "%(message)s &#8212; %(asctime)s"
        formatter = logging.Formatter(
            log_format, datefmt="%H:%M:%S %d/%m/%Y"
        )
        self.setFormatter(formatter)

    def emit(self, record):
        self._client._plugin.sig_client_message_logged.emit(
            RemoteClientLog(
                id=self._client.config_id,
                message=self.format(record),
                level=record.levelno,
                created=record.created,
            )
        )


class SpyderRemoteClient:
    """Class to manage a remote server and its kernels."""

    JUPYTER_SERVER_TIMEOUT = 5  # seconds

    _extra_options = ["platform", "id"]

    START_SERVER_COMMAND = f"/${{HOME}}/.local/bin/micromamba run -n {SERVER_ENV} spyder-server --jupyter-server"
    CHECK_SERVER_COMMAND = f"/${{HOME}}/.local/bin/micromamba run -n {SERVER_ENV} spyder-server -h"
    GET_SERVER_INFO_COMMAND = f"/${{HOME}}/.local/bin/micromamba run -n {SERVER_ENV} spyder-server --get-running-info"

    def __init__(self, conf_id, options: SSHClientOptions, _plugin=None):
        self._config_id = conf_id
        self.options = options
        self._plugin = _plugin

        self.__server_installed = asyncio.Event()
        self.__server_started = asyncio.Event()
        self.__connection_established = asyncio.Event()
        self.__installing_server = False
        self.__starting_server = False
        self.__creating_connection = False

        self._ssh_connection: asyncssh.SSHClientConnection = None
        self._remote_server_process: asyncssh.SSHClientProcess = None
        self._port_forwarder: asyncssh.SSHListener = None
        self._server_info = {}

        # For logging
        self._logger = logging.getLogger(
            f"{__name__}.{self.__class__.__name__}({self.config_id})"
        )

        if not get_debug_level():
            self._logger.setLevel(logging.DEBUG)

        if self._plugin is not None:
            self._logger.addHandler(SpyderRemoteClientLoggerHandler(self))

    def __emit_connection_status(self, status, message):
        if self._plugin is not None:
            self._plugin.sig_connection_status_changed.emit(
                ConnectionInfo(
                    id=self.config_id, status=status, message=message
                )
            )

    @property
    def _api_token(self):
        return self._server_info.get("token")

    @property
    def server_port(self):
        return self._server_info.get("port")

    @property
    def server_pid(self):
        return self._server_info.get("pid")

    @property
    def server_started(self):
        return self.__server_started.is_set() and not self.__starting_server

    @property
    def ssh_is_connected(self):
        """Check if SSH connection is open."""
        return (
            self.__connection_established.is_set()
            and not self.__creating_connection
        )

    @property
    def port_is_forwarded(self):
        """Check if local port is forwarded."""
        return self._port_forwarder is not None

    @property
    def config_id(self):
        """Return the configuration ID"""
        return self._config_id

    @property
    def server_url(self):
        """Return server URL

        Get the server URL with the fowarded local port that
        is used to connect to the spyder-remote-server.

        Returns
        -------
        str
            JupyterHub server URL

        Raises
        ------
        ValueError
            If the local port is not set.
        """
        if not self.local_port:
            raise ValueError("Local port is not set")
        return f"http://127.0.0.1:{self.local_port}"

    @property
    def api_token(self):
        if not self._api_token:
            raise ValueError("API token is not set")
        return self._api_token

    @property
    def peer_host(self):
        if not self.ssh_is_connected:
            return None

        return self._ssh_connection.get_extra_info("peername")[0]

    @property
    def peer_port(self):
        if not self.ssh_is_connected:
            return None

        return self._ssh_connection.get_extra_info("peername")[1]

    @property
    def peer_username(self):
        if not self.ssh_is_connected:
            return None

        return self._ssh_connection.get_extra_info("username")

    @property
    def client_factory(self):
        """Return the client factory."""
        return lambda: SpyderSSHClient(self)

    async def close(self):
        """Closes the remote server and the SSH connection."""
        self.__emit_connection_status(
            ConnectionStatus.Stopping,
            _("We're closing the connection. Please be patient"),
        )

        await self.stop_remote_server()
        await self.close_port_forwarder()
        await self.close_ssh_connection()

    def _handle_connection_lost(self, exc: Exception | None = None):
        self.__connection_established.clear()
        self.__server_started.clear()
        self._port_forwarder = None
        if exc:
            self._logger.error(
                f"Connection to {self.peer_host} was lost",
                exc_info=exc,
            )
            self.__emit_connection_status(
                status=ConnectionStatus.Error,
                message=_("The connection was lost"),
            )

    async def get_server_info(self):
        """Check if the remote server is running."""
        if self._ssh_connection is None:
            self._logger.debug("ssh connection was not established")
            return None

        try:
            output = await self._ssh_connection.run(
                self.GET_SERVER_INFO_COMMAND, check=True
            )
        except asyncssh.TimeoutError:
            self._logger.error("Getting server info timed out")
            return None
        except asyncssh.misc.ChannelOpenError:
            self._logger.error(
                "The connection is closed, so it's not possible to get the "
                "server info"
            )
            return None
        except asyncssh.ProcessError as err:
            self._logger.debug(f"Error getting server info: {err.stderr}")
            return None

        try:
            info = json.loads(output.stdout.splitlines()[-1])
        except json.JSONDecodeError:
            self._logger.debug(
                f"Error parsing server info, received: {output.stdout}"
            )
            return None

        return info

    # -- Connection and server management
    async def connect_and_install_remote_server(self) -> bool:
        """Connect to the remote server and install the server."""
        if await self.create_new_connection():
            return await self.install_remote_server()

        return False

    async def connect_and_start_server(self) -> bool:
        """Connect to the remote server and start the server."""
        if await self.create_new_connection():
            return await self.start_remote_server()

        return False

    async def ensure_connection_and_server(self) -> bool:
        """
        Ensure the SSH connection is open and the remote server is running.
        """
        if self.ssh_is_connected and not self.server_started:
            return await self.ensure_server()

        if not self.ssh_is_connected:
            return await self.connect_and_ensure_server()

        return True

    async def connect_and_ensure_server(self) -> bool:
        """
        Connect to the remote server and ensure it is installed and running.
        """
        if await self.create_new_connection() and not self.server_started:
            return await self.ensure_server()

        if self.server_started:
            return True

        return False

    async def ensure_connection(self) -> bool:
        """Ensure the SSH connection is open."""
        if self.ssh_is_connected:
            return True

        return await self.create_new_connection()

    async def ensure_server(self, *, check_installed=True) -> bool:
        """Ensure remote server is installed and running."""
        if self.server_started:
            return True

        if check_installed and not await self.ensure_server_installed():
            return False

        return await self.start_remote_server()

    async def start_remote_server(self):
        """Start remote server."""
        if self.__starting_server:
            await self.__server_started.wait()
            return True

        self.__starting_server = True
        try:
            if await self.__start_remote_server():
                self.__server_started.set()
                return True
        finally:
            self.__starting_server = False

        self.__server_started.clear()
        return False

    async def __start_remote_server(self):
        """Start remote server."""
        if not self.ssh_is_connected:
            self._logger.error("SSH connection is not open")
            return False

        if info := await self.get_server_info():
            self._logger.warning(
                f"Remote server is already running for {self.peer_host}"
            )

            self._logger.debug("Checking server info")
            if self._server_info != info:
                self._server_info = info
                self._logger.info(
                    "Different server info, updating info "
                    f"for {self.peer_host}"
                )
                if await self.forward_local_port():
                    self.__emit_connection_status(
                        ConnectionStatus.Active,
                        _("The connection was established successfully"),
                    )
                    return True

                self._logger.error(
                    "Error forwarding local port, server might not be "
                    "reachable"
                )
                self.__emit_connection_status(
                    ConnectionStatus.Error,
                    _("It was not possible to forward the local port"),
                )

            self.__emit_connection_status(
                ConnectionStatus.Active,
                _("The connection was established successfully"),
            )

            return True

        self._logger.debug(f"Starting remote server for {self.peer_host}")
        try:
            self._remote_server_process = (
                await self._ssh_connection.create_process(
                    self.START_SERVER_COMMAND,
                    stderr=asyncssh.STDOUT,
                )
            )
        except (OSError, asyncssh.Error, ValueError) as e:
            self._logger.error(f"Error starting remote server: {e}")
            self._remote_server_process = None
            self.__emit_connection_status(
                ConnectionStatus.Error, _("Error starting the remote server")
            )
            return False

        _time = 0
        while (info := await self.get_server_info()) is None and _time < 5:
            await asyncio.sleep(1)
            _time += 1

        if info is None:
            self._logger.error("Faield to get server info")
            self.__emit_connection_status(
                ConnectionStatus.Error, _("Error getting server info")
            )
            return False

        self._server_info = info

        self._logger.info(
            f"Remote server started for {self.peer_host} at port "
            f"{self.server_port}"
        )

        if await self.forward_local_port():
            self.__emit_connection_status(
                ConnectionStatus.Active,
                _("The connection was established successfully"),
            )
            return True

        self._logger.error("Error forwarding local port.")

        self.__emit_connection_status(
            ConnectionStatus.Error,
            _("It was not possible to forward the local port"),
        )
        return False

    async def ensure_server_installed(self) -> bool:
        """Ensure remote server is installed."""
        if not await self.check_server_installed():
            return await self.install_remote_server()

        return True

    async def check_server_installed(self) -> bool:
        """Check if remote server is installed."""
        if not self.ssh_is_connected:
            self._logger.error("SSH connection is not open")
            return False

        try:
            await self._ssh_connection.run(
                self.CHECK_SERVER_COMMAND, check=True
            )
        except asyncssh.ProcessError as err:
            self._logger.warning(
                f"spyder-remote-server is not installed: {err.stderr}"
            )
            return False
        except asyncssh.TimeoutError:
            self._logger.error(
                "Checking if spyder-remote-server is installed timed out"
            )
            return False

        self._logger.debug(
            f"spyder-remote-server is installed on {self.peer_host}"
        )

        return True

    async def install_remote_server(self) -> bool:
        """Install remote server."""
        if self.__installing_server:
            await self.__server_installed.wait()
            return True

        self.__installing_server = True
        try:
            if await self.__install_remote_server():
                self.__server_installed.set()
                return True
        finally:
            self.__installing_server = False

        self.__server_installed.clear()
        return False

    async def __install_remote_server(self):
        """Install remote server."""
        if not self.ssh_is_connected:
            self._logger.error("SSH connection is not open")
            return False

        self._logger.debug(
            f"Installing spyder-remote-server on {self.peer_host}"
        )
        command = get_installer_command(self.options["platform"])
        if not command:
            self._logger.error(
                f"Cannot install spyder-remote-server on "
                f"{self.options['platform']} automatically. Please install it "
                f"manually."
            )
            return False

        try:
            await self._ssh_connection.run(command, check=True)
        except asyncssh.ProcessError as err:
            self._logger.error(f"Instalation script failed: {err.stderr}")
            return False
        except asyncssh.TimeoutError:
            self._logger.error("Instalation script timed out")
            return False

        self._logger.info(
            f"Successfully installed spyder-remote-server on {self.peer_host}"
        )

        return True

    async def create_new_connection(self) -> bool:
        if self.__creating_connection:
            await self.__connection_established.wait()
            return True

        self.__creating_connection = True
        try:
            if await self.__create_new_connection():
                self.__connection_established.set()
                return True
        finally:
            self.__creating_connection = False

        self.__connection_established.clear()
        return False

    async def __create_new_connection(self) -> bool:
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
        if self.ssh_is_connected:
            self._logger.debug(
                f"Atempting to create a new connection with an existing for "
                f"{self.peer_host}"
            )
            await self.close_ssh_connection()

        self.__emit_connection_status(
            ConnectionStatus.Connecting,
            _("We're establishing the connection. Please be patient"),
        )

        conect_kwargs = {
            k: v
            for k, v in self.options.items()
            if k not in self._extra_options
        }
        self._logger.debug("Opening SSH connection")
        try:
            self._ssh_connection = await asyncssh.connect(
                **conect_kwargs, client_factory=self.client_factory
            )
        except (OSError, asyncssh.Error) as e:
            self._logger.error(f"Failed to open ssh connection: {e}")

            self.__emit_connection_status(
                ConnectionStatus.Error,
                _("It was not possible to open a connection to this machine"),
            )
            return False

        self._logger.info(f"SSH connection opened for {self.peer_host}")

        return True

    async def forward_local_port(self):
        """Forward local port."""
        if not self.server_port:
            self._logger.error("Server port is not set")
            return False

        if not self.ssh_is_connected:
            self._logger.error("SSH connection is not open")
            return False

        self._logger.debug(
            f"Forwarding an free local port to remote port {self.server_port}"
        )

        if self._port_forwarder:
            self._logger.warning(
                f"Port forwarder is already open for host {self.peer_host} "
                f"with local port {self.local_port} and remote port "
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

        self.local_port = local_port

        self._logger.debug(
            f"Forwarded local port {local_port} to remote server at "
            f"{server_host}:{self.server_port}"
        )

        return True

    async def close_port_forwarder(self):
        """Close port forwarder."""
        if self.port_is_forwarded:
            self._logger.debug(
                f"Closing port forwarder for host {self.peer_host} with local "
                f"port {self.local_port}"
            )
            self._port_forwarder.close()
            await self._port_forwarder.wait_closed()
            self._port_forwarder = None
            self._logger.debug(
                f"Port forwarder closed for host {self.peer_host} with local "
                f"port {self.local_port}"
            )

    async def stop_remote_server(self):
        """Close remote server."""
        if not self.server_started:
            self._logger.warning(
                f"Remote server is not running for {self.peer_host}"
            )
            return False

        if not self.ssh_is_connected:
            self._logger.error("SSH connection is not open")
            return False

        # bug in jupyterhub, need to send SIGINT twice
        self._logger.debug(
            f"Stopping remote server for {self.peer_host} with pid "
            f"{self._server_info['pid']}"
        )
        try:
            async with JupyterAPI(
                self.server_url, api_token=self.api_token
            ) as jupyter:
                await jupyter.shutdown_server()
        except Exception as err:
            self._logger.exception(
                "Error stopping remote server", exc_info=err
            )

        if (
            self._remote_server_process
            and not self._remote_server_process.is_closing()
        ):
            self._remote_server_process.terminate()
            await self._remote_server_process.wait_closed()

        self.__server_started.clear()
        self._remote_server_process = None
        self._logger.info(f"Remote server process closed for {self.peer_host}")
        return True

    async def close_ssh_connection(self):
        """Close SSH connection."""
        if not self.ssh_is_connected:
            self._logger.debug("SSH connection is not open")
            return

        self._logger.debug(f"Closing SSH connection for {self.peer_host}")
        self._ssh_connection.close()
        await self._ssh_connection.wait_closed()
        self._ssh_connection = None
        self._logger.info("SSH connection closed")
        self.__connection_established.clear()
        self.__emit_connection_status(
            ConnectionStatus.Inactive,
            _("The connection was closed successfully"),
        )

    # --- Kernel Management
    async def start_new_kernel_ensure_server(
        self, _retries=5
    ) -> KernelConnectionInfo:
        """Launch a new kernel ensuring the remote server is running.

        Parameters
        ----------
        options : SSHClientOptions
            The options to use for the SSH connection.

        Returns
        -------
        KernelConnectionInfo
            The kernel connection information.
        """
        if not await self.ensure_connection_and_server():
            self._logger.error(
                "Cannot launch kernel, remote server is not running"
            )
            return {}

        # This is necessary to avoid an error when the server has not started
        # before
        await asyncio.sleep(1)
        kernel_id = await self.start_new_kernel()

        retries = 0
        while not kernel_id and retries < _retries:
            await asyncio.sleep(1)
            kernel_id = await self.start_new_kernel()
            self._logger.debug(
                f"Server might not be ready yet, retrying kernel launch "
                f"({retries + 1}/{_retries})"
            )
            retries += 1

        return kernel_id

    async def get_kernel_info_ensure_server(
        self, kernel_id, _retries=5
    ) -> KernelConnectionInfo:
        """Launch a new kernel ensuring the remote server is running.

        Parameters
        ----------
        options : SSHClientOptions
            The options to use for the SSH connection.

        Returns
        -------
        KernelConnectionInfo
            The kernel connection information.
        """
        if not await self.ensure_connection_and_server():
            self._logger.error(
                "Cannot launch kernel, remote server is not running"
            )
            return {}

        # This is necessary to avoid an error when the server has not started
        # before
        await asyncio.sleep(1)
        kernel_info = await self.get_kernel_info(kernel_id)

        retries = 0
        while not kernel_info and retries < _retries:
            await asyncio.sleep(1)
            kernel_info = await self.get_kernel_info(kernel_id)
            self._logger.debug(
                f"Server might not be ready yet, retrying kernel launch "
                f"({retries + 1}/{_retries})"
            )
            retries += 1

        return kernel_info

    async def start_new_kernel(self, kernel_spec=None) -> KernelInfo:
        """Start new kernel."""
        async with JupyterAPI(
            self.server_url, api_token=self.api_token
        ) as jupyter:
            response = await jupyter.create_kernel(kernel_spec=kernel_spec)
        self._logger.info(f"Kernel started with ID {response['id']}")
        return response

    async def list_kernels(self) -> list[KernelInfo]:
        """List kernels."""
        async with JupyterAPI(
            self.server_url, api_token=self.api_token
        ) as jupyter:
            response = await jupyter.list_kernels()

        self._logger.info(f"Kernels listed for {self.peer_host}")
        return response

    async def get_kernel_info(self, kernel_id) -> KernelInfo:
        """Get kernel info."""
        async with JupyterAPI(
            self.server_url, api_token=self.api_token
        ) as jupyter:
            response = await jupyter.get_kernel(kernel_id=kernel_id)

        self._logger.info(f"Kernel info retrieved for ID {kernel_id}")
        return response

    async def terminate_kernel(self, kernel_id) -> bool:
        """Terminate kernel."""
        async with JupyterAPI(
            self.server_url, api_token=self.api_token
        ) as jupyter:
            response = await jupyter.delete_kernel(kernel_id=kernel_id)

        self._logger.info(f"Kernel terminated for ID {kernel_id}")
        return response

    async def interrupt_kernel(self, kernel_id) -> bool:
        """Interrupt kernel."""
        async with JupyterAPI(
            self.server_url, api_token=self.api_token
        ) as jupyter:
            response = await jupyter.interrupt_kernel(kernel_id=kernel_id)

        self._logger.info(f"Kernel interrupted for ID {kernel_id}")
        return response

    async def restart_kernel(self, kernel_id) -> bool:
        """Restart kernel."""
        async with JupyterAPI(
            self.server_url, api_token=self.api_token
        ) as jupyter:
            response = await jupyter.restart_kernel(kernel_id=kernel_id)

        self._logger.info(f"Kernel restarted for ID {kernel_id}")
        return response

    @staticmethod
    def get_free_port():
        """Request a free port from the OS."""
        with socket.socket() as s:
            s.bind(("", 0))
            return s.getsockname()[1]
