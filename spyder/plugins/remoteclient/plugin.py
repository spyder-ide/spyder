# -*- coding: utf-8 -*-
#
# Copyright (c) 2009- Spyder Project Contributors
#
# Distributed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""
Remote Client Plugin.
"""

# Standard library imports
import logging

# Third-party imports
from qtpy.QtCore import Signal
import zmq
import asyncssh

# Local imports
from spyder.api.translations import _
from spyder.api.plugins import Plugins, SpyderPluginV2
from spyder.plugins.remoteclient.api import DeleteKernel, KernelInfo, KernelsList
from spyder.plugins.remoteclient.client.api import JupyterHubAPI


_logger = logging.getLogger(__name__)


class RemoteClient(SpyderPluginV2):
    """
    Remote client plugin.
    """

    NAME = "remoteclient"
    OPTIONAL = []
    CONF_SECTION = NAME
    CONF_FILE = False

    API_TOKEN = "GiJ96ujfLpPsq7oatW1IJuER01FbZsgyCM0xH6oMZXDAV6zUZsFy3xQBZakSBo6P"

    _SERVER_URL = "https://127.0.0.1:{port}"
    _START_SERVER_COMMAND = "spyder-remote-server --show-port"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.__ssh_connection: asyncssh.SSHClientConnection = None
        self.__ssh_options: asyncssh.SSHClientConnectionOptions = None
        self.__remote_server_process = None
        self._server_port = None

    # ---- SpyderPluginV2 API
    # -------------------------------------------------------------------------
    @staticmethod
    def get_name():
        return _("Remote Client")

    @staticmethod
    def get_description():
        return _("Connect to a remote machine.")

    @classmethod
    def get_icon(cls):
        return cls.create_icon('remoteclient')

    def on_initialize(self):
        pass

    def on_first_registration(self):
        pass

    def on_close(self, cancellable=True):
        """Stops remote server and close any opened connection."""
        pass

    # ---- Public API
    # -------------------------------------------------------------------------
    # --- Remote Server Methods
    async def install_remote_server(self):
        """Install remote server."""
        # Assuming installation command is known
        install_command = "install spyder-remote-server command"
        try:
            async with asyncssh.connect(options=self.__ssh_options) as conn:
                result = await conn.run(install_command)
                _logger.info(f"Install command output: {result.stdout}")
        except (OSError, asyncssh.Error) as e:
            _logger.error(f"Error installing remote server: {e}")

    async def start_remote_server(self, port):
        """Start remote server."""
        try:
            self.__ssh_connection = await asyncssh.connect(options=self.__ssh_options)
            self.__remote_server_process = await self.__ssh_connection.create_process(self._START_SERVER_COMMAND)
            port = self.__extract_server_port(self.__remote_server_process.stdout)
            _logger.info(f"Remote server started on port {port}")
        except (OSError, asyncssh.Error) as e:
            _logger.error(f"Error starting remote server: {e}")
            self.__remote_server_process = None

    async def stop_remote_server(self):
        """Stop remote server."""
        if self.__remote_server_process:
            self.__remote_server_process.terminate()
            await self.__remote_server_process.wait_closed()
            _logger.info("Remote server stopped")

    async def restart_remote_server(self, port):
        """Restart remote server."""
        await self.stop_remote_server()
        await self.start_remote_server(port)

    # --- Remote Server Kernel Methods
    async def _get_kernels(self):
        """Get opened kernels."""
        async with JupyterHubAPI(self._SERVER_URL, api_token=self.API_TOKEN) as hub:
            response = await hub.execute_get_service("spyder-service", "kernel")
        _logger.warning(f'spyder-service-kernel-get: {response}')
        return response

    async def get_kernel_info(self, kernel_key):
        """Get kernel info."""
        async with JupyterHubAPI(self._SERVER_URL, api_token=self.API_TOKEN) as hub:
            response = await hub.execute_get_service("spyder-service", f"kernel/{kernel_key}")
        _logger.info(f'spyder-service-kernel-get: {response}')
        return response

    async def terminate_kernel(self, kernel_key):
        """Terminate opened kernel."""
        async with JupyterHubAPI(self._SERVER_URL, api_token=self.API_TOKEN) as hub:
            response = await hub.execute_delete_service("spyder-service", f"kernel/{kernel_key}")
        _logger.info(f'spyder-service-kernel-delete: {response}')
        return response

    async def start_new_kernel(self):
        """Start new kernel."""
        async with JupyterHubAPI(self._SERVER_URL, api_token=self.API_TOKEN) as hub:
            response = await hub.execute_post_service("spyder-service", "kernel")
        _logger.info(f'spyder-service-kernel-post: {response}')
        return response

    # ---- Private API
    # -------------------------------------------------------------------------
    async def _ssh_is_connected(self):
        """Check if SSH connection is open."""
        if not self.__ssh_connection:
            return False

        if self.__ssh_connection.is_closed:
            return False

        return True

    async def _open_ssh_connection(self):
        """Open an SSH connection."""
        try:
            self.__ssh_connection = await asyncssh.connect(
                options=self.__ssh_options,
            )
        except (OSError, asyncssh.Error) as e:
            _logger.error(f"Failed to connect to {self.__ssh_options.hostname}: {e}")
            self.__ssh_connection = None

    async def _close_ssh_connection(self):
        """Close SSH connection."""
        if self.__ssh_connection:
            self.__ssh_connection.close()
            await self.__ssh_connection.wait_closed()
            self.__ssh_connection = None

    @staticmethod
    def __extract_server_port(server_stdout: asyncssh.SSHReader):
        # extract port from first line of stdout: "{port}"
        if (output := server_stdout.readline()):
            return output.splitlines()[0]
        
        raise ValueError("Failed to extract port from server stdout")