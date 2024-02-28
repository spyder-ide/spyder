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
from qtpy.QtCore import Signal, Slot

# Local imports
from spyder.api.translations import _
from spyder.api.plugins import Plugins, SpyderPluginV2
from spyder.plugins.remoteclient.api.protocol import KernelConnectionInfo, DeleteKernel, KernelInfo, KernelsList, SSHClientOptions
from spyder.plugins.remoteclient.api.client import SpyderRemoteClient
from spyder.api.utils import AsSync

_logger = logging.getLogger(__name__)


class RemoteClient(SpyderPluginV2):
    """
    Remote client plugin.
    """

    NAME = "remoteclient"
    OPTIONAL = []
    CONF_SECTION = NAME
    CONF_FILE = False

    CONF_SECTION_SERVERS = 'servers'

    # ---- Signals
    sig_connection_established = Signal()
    sig_connection_lost = Signal()

    sig_kernel_list = Signal(KernelsList)
    sig_kernel_started = Signal(KernelConnectionInfo)
    sig_kernel_info = Signal(KernelInfo)
    sig_kernel_terminated = Signal(DeleteKernel)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self._remote_servers: dict[str, SpyderRemoteClient] = {}

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

    # ---- Public API
    # -------------------------------------------------------------------------
    # --- Remote Server Methods
    def get_remote_server(self, config_id):
        """Get remote server."""
        if config_id in self._remote_servers:
            return self._remote_servers[config_id]

    @AsSync.as_sync
    async def install_remote_server(self, config_id):
        """Install remote server."""
        if config_id in self._remote_servers:
            server = self._remote_servers[config_id]
            await server.install_remote_server()

    @AsSync.as_sync
    async def start_remote_server(self, config_id):
        """Start remote server."""
        if config_id in self._remote_servers:
            server = self._remote_servers[config_id]
            await server.connect_and_start_server()
            self.sig_connection_established.emit()

    @AsSync.as_sync
    async def stop_remote_server(self, config_id):
        """Stop remote server."""
        if config_id in self._remote_servers:
            server = self._remote_servers[config_id]
            await server.close()
            self.sig_connection_lost.emit()

    def restart_remote_server(self, config_id):
        """Restart remote server."""
        self.stop_remote_server(config_id)
        self.start_remote_server(config_id)

    # --- Configuration Methods
    def load_server_from_id(self, config_id):
        """Load remote server from configuration id."""
        options = self.load_conf(config_id)
        self.load_server(config_id, options)    

    def load_server(self, config_id: str, options: SSHClientOptions):
        """Load remote server."""
        server = SpyderRemoteClient(options)
        self._remote_servers[config_id] = server

    def load_conf(self, config_id):
        """Load remote server configuration."""
        return SSHClientOptions(**self.get_conf(
            self.CONF_SECTION_SERVERS, {}
        ).get(config_id, {}))

    def get_loaded_servers(self):
        """Get configured remote servers."""
        return self._remote_servers.keys()

    def get_conf_ids(self):
        """Get configured remote servers ids."""
        return self.get_conf(self.CONF_SECTION_SERVERS, {}).keys()

    # ---- Private API
    # -------------------------------------------------------------------------
    # --- Remote Server Kernel Methods
    @Slot(str)
    @AsSync.as_sync
    async def get_kernels(self, config_id):
        """Get opened kernels."""
        if config_id in self._remote_servers:
            server = self._remote_servers[config_id]
            kernels_list = await server.get_kernels()
            self.sig_kernel_list.emit(kernels_list)
            return kernels_list

    @Slot(str)
    @AsSync.as_sync
    async def get_kernel_info(self, config_id, kernel_key):
        """Get kernel info."""
        if config_id in self._remote_servers:
            server = self._remote_servers[config_id]
            kernel_info = await server.get_kernel_info(kernel_key)
            self.sig_kernel_info.emit(kernel_info)
            return kernel_info

    @Slot(str)
    @AsSync.as_sync
    async def terminate_kernel(self, config_id, kernel_key):
        """Terminate opened kernel."""
        if config_id in self._remote_servers:
            server = self._remote_servers[config_id]
            delete_kernel = await server.terminate_kernel(kernel_key)
            self.sig_kernel_terminated.emit(delete_kernel)
            return delete_kernel

    @Slot(str)
    @AsSync.as_sync
    async def start_new_kernel(self, config_id):
        """Start new kernel."""
        if config_id in self._remote_servers:
            server = self._remote_servers[config_id]
            kernel_connection_info = await server.start_new_kernel()
            self.sig_kernel_started.emit(kernel_connection_info)
            return kernel_connection_info
