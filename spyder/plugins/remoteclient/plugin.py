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
    sig_server_log = Signal(dict)

    sig_connection_established = Signal(str)
    sig_connection_lost = Signal(str)

    sig_kernel_list = Signal(dict)
    sig_kernel_started = Signal(dict)
    sig_kernel_info = Signal(dict)
    sig_kernel_terminated = Signal(dict)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self._remote_clients: dict[str, SpyderRemoteClient] = {}

    # ---- SpyderPluginV2 API
    # -------------------------------------------------------------------------
    @staticmethod
    def get_name():
        return _("Remote client")

    @staticmethod
    def get_description():
        return _("Connect to remote machines to run code on them.")

    @classmethod
    def get_icon(cls):
        return cls.create_icon('remoteclient')

    def on_initialize(self):
        pass

    def on_first_registration(self):
        pass

    def on_close(self, cancellable=True):
        """Stops remote server and close any opened connection."""
        for client in self._remote_clients.values():
            AsSync(client.close)()

    # ---- Public API
    # -------------------------------------------------------------------------
    # --- Remote Server Methods
    def get_remote_server(self, config_id):
        """Get remote server."""
        if config_id in self._remote_clients:
            return self._remote_clients[config_id]

    @AsSync
    async def install_remote_server(self, config_id):
        """Install remote server."""
        if config_id in self._remote_clients:
            client = self._remote_clients[config_id]
            return await client.connect_and_install_remote_server()

    @AsSync
    async def start_remote_server(self, config_id):
        """Start remote server."""
        if config_id in self._remote_clients:
            server = self._remote_clients[config_id]
            return await server.connect_and_start_server()

    @AsSync
    async def stop_remote_server(self, config_id):
        """Stop remote server."""
        if config_id in self._remote_clients:
            client = self._remote_clients[config_id]
            await client.stop_remote_server()

    def restart_remote_server(self, config_id):
        """Restart remote server."""
        self.stop_remote_server(config_id)
        self.start_remote_server(config_id)

    # --- Configuration Methods
    def load_client_from_id(self, config_id):
        """Load remote server from configuration id."""
        options = self.load_conf(config_id)
        self.load_client(config_id, options)    

    def load_client(self, config_id: str, options: SSHClientOptions):
        """Load remote server."""
        client = SpyderRemoteClient(config_id, options, _plugin=self)
        self._remote_clients[config_id] = client

    def load_conf(self, config_id):
        """Load remote server configuration."""
        return SSHClientOptions(**self.get_conf(
            self.CONF_SECTION_SERVERS, {}
        ).get(config_id, {}))

    def get_loaded_servers(self):
        """Get configured remote servers."""
        return self._remote_clients.keys()

    def get_conf_ids(self):
        """Get configured remote servers ids."""
        return self.get_conf(self.CONF_SECTION_SERVERS, {}).keys()

    # ---- Private API
    # -------------------------------------------------------------------------
    # --- Remote Server Kernel Methods
    @Slot(str)
    @AsSync
    async def get_kernels(self, config_id):
        """Get opened kernels."""
        if config_id in self._remote_clients:
            client = self._remote_clients[config_id]
            kernels_list = await client.get_kernels()
            self.sig_kernel_list.emit(kernels_list)
            return kernels_list

    @Slot(str)
    @AsSync
    async def get_kernel_info(self, config_id, kernel_key):
        """Get kernel info."""
        if config_id in self._remote_clients:
            client = self._remote_clients[config_id]
            kernel_info = await client.get_kernel_info(kernel_key)
            self.sig_kernel_info.emit(kernel_info)
            return kernel_info

    @Slot(str)
    @AsSync
    async def terminate_kernel(self, config_id, kernel_key):
        """Terminate opened kernel."""
        if config_id in self._remote_clients:
            client = self._remote_clients[config_id]
            delete_kernel = await client.terminate_kernel(kernel_key)
            self.sig_kernel_terminated.emit(delete_kernel)
            return delete_kernel

    @Slot(str)
    @AsSync
    async def start_new_kernel(self, config_id):
        """Start new kernel."""
        if config_id in self._remote_clients:
            client = self._remote_clients[config_id]
            kernel_connection_info = await client.start_new_kernel()
            self.sig_kernel_started.emit(kernel_connection_info)
            return kernel_connection_info
