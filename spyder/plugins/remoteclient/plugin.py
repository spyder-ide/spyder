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
from spyder.api.asyncdispatcher import AsyncDispatcher
from spyder.api.plugin_registration.decorators import (
    on_plugin_available,
    on_plugin_teardown,
)
from spyder.api.plugins import Plugins, SpyderPluginV2
from spyder.api.translations import _
from spyder.plugins.ipythonconsole.api import IPythonConsoleWidgetActions
from spyder.plugins.mainmenu.api import (
    ApplicationMenus,
    ConsolesMenuSections,
    ToolsMenuSections,
)
from spyder.plugins.remoteclient.api import (
    RemoteClientActions,
    RemoteClientMenus,
)
from spyder.plugins.remoteclient.api.client import SpyderRemoteClient
from spyder.plugins.remoteclient.api.protocol import (
    SSHClientOptions,
    ConnectionStatus,
)
from spyder.plugins.remoteclient.widgets.container import RemoteClientContainer

_logger = logging.getLogger(__name__)


class RemoteClient(SpyderPluginV2):
    """
    Remote client plugin.
    """

    NAME = "remoteclient"
    OPTIONAL = [Plugins.IPythonConsole, Plugins.MainMenu]
    CONF_SECTION = NAME
    CONTAINER_CLASS = RemoteClientContainer
    CONF_FILE = False

    CONF_SECTION_SERVERS = "servers"

    # ---- Signals
    sig_server_log = Signal(dict)

    sig_connection_established = Signal(str)
    sig_connection_lost = Signal(str)
    sig_connection_status_changed = Signal(dict)

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
        return cls.create_icon("remote_server")

    def on_initialize(self):
        self._reset_status()
        self._is_consoles_menu_added = False

        container = self.get_container()

        container.sig_start_server_requested.connect(self.start_remote_server)
        container.sig_stop_server_requested.connect(self.stop_remote_server)

        self.sig_connection_status_changed.connect(
            container.sig_connection_status_changed
        )

    def on_first_registration(self):
        pass

    def on_close(self, cancellable=True):
        """Stops remote server and close any opened connection."""
        for client in self._remote_clients.values():
            AsyncDispatcher(client.close, early_return=False)()

    @on_plugin_available(plugin=Plugins.MainMenu)
    def on_mainmenu_available(self):
        mainmenu = self.get_plugin(Plugins.MainMenu)

        action = self.get_action(RemoteClientActions.ManageConnections)
        mainmenu.add_item_to_application_menu(
            action,
            menu_id=ApplicationMenus.Tools,
            section=ToolsMenuSections.External,
            before_section=ToolsMenuSections.Extras
        )

        if (
            self.is_plugin_available(Plugins.IPythonConsole)
            and not self._is_consoles_menu_added
        ):
            self._add_remote_consoles_menu()

    @on_plugin_teardown(plugin=Plugins.MainMenu)
    def on_mainmenu_teardown(self):
        mainmenu = self.get_plugin(Plugins.MainMenu)

        mainmenu.remove_item_from_application_menu(
            RemoteClientActions.ManageConnections,
            menu_id=ApplicationMenus.Tools
        )

        if self._is_consoles_menu_added:
            mainmenu.remove_item_from_application_menu(
                RemoteClientMenus.RemoteConsoles,
                menu_id=ApplicationMenus.Consoles
            )

    @on_plugin_available(plugin=Plugins.IPythonConsole)
    def on_ipython_console_available(self):
        if (
            self.is_plugin_available(Plugins.MainMenu)
            and not self._is_consoles_menu_added
        ):
            self._add_remote_consoles_menu()

    # ---- Public API
    # -------------------------------------------------------------------------
    # --- Remote Server Methods
    def get_remote_server(self, config_id):
        """Get remote server."""
        if config_id in self._remote_clients:
            return self._remote_clients[config_id]

    @AsyncDispatcher.dispatch()
    async def _install_remote_server(self, config_id):
        """Install remote server."""
        if config_id in self._remote_clients:
            client = self._remote_clients[config_id]
            await client.connect_and_install_remote_server()

    @AsyncDispatcher.dispatch()
    async def start_remote_server(self, config_id):
        """Start remote server."""
        if config_id not in self._remote_clients:
            self.load_client_from_id(config_id)

        client = self._remote_clients[config_id]
        await client.connect_and_ensure_server()

    @AsyncDispatcher.dispatch()
    async def stop_remote_server(self, config_id):
        """Stop remote server."""
        if config_id in self._remote_clients:
            client = self._remote_clients[config_id]
            await client.close()

    @AsyncDispatcher.dispatch()
    async def ensure_remote_server(self, config_id):
        """Ensure remote server is running and installed."""
        if config_id in self._remote_clients:
            client = self._remote_clients[config_id]
            await client.connect_and_ensure_server()

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
        options = SSHClientOptions(
            **self.get_conf(self.CONF_SECTION_SERVERS, {}).get(config_id, {})
        )

        # We couldn't find saved options for config_id
        if not options:
            return {}

        if options["client_keys"]:
            passpharse = self.get_conf(f"{config_id}/passpharse", secure=True)

            # Passphrase is optional
            if passpharse:
                options["passpharse"] = passpharse
        elif options["config"]:
            # TODO: Check how this needs to be handled
            pass
        else:
            # Password is mandatory in this case
            password = self.get_conf(f"{config_id}/password", secure=True)
            options["password"] = password

        # Default for now
        options["platform"] = "linux"

        return options

    def get_loaded_servers(self):
        """Get configured remote servers."""
        return self._remote_clients.keys()

    def get_config_ids(self):
        """Get configured remote servers ids."""
        return self.get_conf(self.CONF_SECTION_SERVERS, {}).keys()

    # ---- Private API
    # -------------------------------------------------------------------------
    # --- Remote Server Kernel Methods
    @Slot(str)
    @AsyncDispatcher.dispatch()
    async def get_kernels(self, config_id):
        """Get opened kernels."""
        if config_id in self._remote_clients:
            client = self._remote_clients[config_id]
            kernels_list = await client.list_kernels()
            return kernels_list

    @Slot(str)
    @AsyncDispatcher.dispatch()
    async def get_kernel_info(self, config_id, kernel_id):
        """Get kernel info."""
        if config_id in self._remote_clients:
            client = self._remote_clients[config_id]
            kernel_info = await client.get_kernel_info(kernel_id)
            return kernel_info

    @Slot(str)
    @AsyncDispatcher.dispatch()
    async def terminate_kernel(self, config_id, kernel_id):
        """Terminate opened kernel."""
        if config_id in self._remote_clients:
            client = self._remote_clients[config_id]
            delete_kernel = await client.terminate_kernel(kernel_id)
            return delete_kernel

    @Slot(str)
    @AsyncDispatcher.dispatch()
    async def start_new_kernel(self, config_id):
        """Start new kernel."""
        if config_id in self._remote_clients:
            client = self._remote_clients[config_id]
            kernel_info = await client.start_new_kernel_ensure_server()
            return kernel_info

    @Slot(str)
    @AsyncDispatcher.dispatch()
    async def restart_kernel(self, config_id, kernel_id):
        """Restart kernel."""
        if config_id in self._remote_clients:
            client = self._remote_clients[config_id]
            status = await client.restart_kernel(kernel_id)
            return status

    @Slot(str)
    @AsyncDispatcher.dispatch()
    async def interrupt_kernel(self, config_id, kernel_id):
        """Interrupt kernel."""
        if config_id in self._remote_clients:
            client = self._remote_clients[config_id]
            status = await client.interrupt_kernel(kernel_id)
            return status

    def _reset_status(self):
        """Reset status of servers."""
        for config_id in self.get_config_ids():
            self.set_conf(f"{config_id}/status", ConnectionStatus.Inactive)
            self.set_conf(f"{config_id}/status_message", "")

    def _add_remote_consoles_menu(self):
        """Add remote consoles submenu to the Consoles menu."""
        container = self.get_container()
        container.create_remote_consoles_submenu()

        menu = container.get_menu(RemoteClientMenus.RemoteConsoles)
        mainmenu = self.get_plugin(Plugins.MainMenu)
        mainmenu.add_item_to_application_menu(
            menu,
            menu_id=ApplicationMenus.Consoles,
            section=ConsolesMenuSections.New,
            before=IPythonConsoleWidgetActions.ConnectToKernel
        )

        self._is_consoles_menu_added = True
