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
import contextlib

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
    sig_server_stopped = Signal(str)
    sig_server_renamed = Signal(str)
    sig_client_message_logged = Signal(dict)

    sig_connection_established = Signal(str)
    sig_connection_lost = Signal(str)
    sig_connection_status_changed = Signal(dict)

    _sig_kernel_started = Signal(object, dict)

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

        # Container signals
        container.sig_start_server_requested.connect(self.start_remote_server)
        container.sig_stop_server_requested.connect(self.stop_remote_server)
        container.sig_stop_server_requested.connect(self.sig_server_stopped)
        container.sig_server_renamed.connect(self.sig_server_renamed)
        container.sig_create_ipyclient_requested.connect(
            self.create_ipyclient_for_server
        )
        container.sig_shutdown_kernel_requested.connect(self._shutdown_kernel)
        container.sig_interrupt_kernel_requested.connect(
            self._interrupt_kernel
        )

        # Plugin signals
        self.sig_connection_status_changed.connect(
            container.sig_connection_status_changed
        )
        self.sig_client_message_logged.connect(
            container.sig_client_message_logged
        )
        self._sig_kernel_started.connect(container.on_kernel_started)

    def on_first_registration(self):
        pass

    def on_close(self, cancellable=True):
        """Stops remote server and close any opened connection."""
        for client in self._remote_clients.values():
            AsyncDispatcher(
                client.close, loop="asyncssh", early_return=False
            )()

    @on_plugin_available(plugin=Plugins.MainMenu)
    def on_mainmenu_available(self):
        mainmenu = self.get_plugin(Plugins.MainMenu)

        action = self.get_action(RemoteClientActions.ManageConnections)
        mainmenu.add_item_to_application_menu(
            action,
            menu_id=ApplicationMenus.Tools,
            section=ToolsMenuSections.External,
            before_section=ToolsMenuSections.Extras,
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
            menu_id=ApplicationMenus.Tools,
        )

        if self._is_consoles_menu_added:
            mainmenu.remove_item_from_application_menu(
                RemoteClientMenus.RemoteConsoles,
                menu_id=ApplicationMenus.Consoles,
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

    @AsyncDispatcher.dispatch(loop="asyncssh")
    async def _install_remote_server(self, config_id):
        """Install remote server."""
        if config_id in self._remote_clients:
            client = self._remote_clients[config_id]
            await client.connect_and_install_remote_server()

    @AsyncDispatcher.dispatch(loop="asyncssh")
    async def start_remote_server(self, config_id):
        """Start remote server."""
        if config_id not in self._remote_clients:
            self.load_client_from_id(config_id)

        client = self._remote_clients[config_id]
        await client.connect_and_ensure_server()

    @AsyncDispatcher.dispatch(loop="asyncssh")
    async def stop_remote_server(self, config_id):
        """Stop remote server."""
        if config_id in self._remote_clients:
            client = self._remote_clients[config_id]
            await client.close()

    @AsyncDispatcher.dispatch(loop="asyncssh")
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
        options = self.get_conf(self.CONF_SECTION_SERVERS, {}).get(
            config_id, {}
        )

        # We couldn't find saved options for config_id
        if not options:
            return {}

        if options["client_keys"]:
            passpharse = self.get_conf(f"{config_id}/passpharse", secure=True)
            options["client_keys"] = [options["client_keys"]]

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

        return SSHClientOptions(**options)

    def get_loaded_servers(self):
        """Get configured remote servers."""
        return self._remote_clients.keys()

    def get_config_ids(self):
        """Get configured remote servers ids."""
        return self.get_conf(self.CONF_SECTION_SERVERS, {}).keys()

    @Slot(str)
    def create_ipyclient_for_server(self, config_id):
        """Create a new IPython console client for a server."""
        auth_method = self.get_conf(f"{config_id}/auth_method")
        hostname = self.get_conf(f"{config_id}/{auth_method}/name")

        ipyconsole = self.get_plugin(Plugins.IPythonConsole)
        ipyclient = ipyconsole.create_client_for_kernel(
            # The connection file will be supplied when connecting a remote
            # kernel to this client
            connection_file="",
            # We use the server name as hostname because for clients it's the
            # attribute used by the IPython console to set their tab name.
            hostname=hostname,
            # These values are not necessary at this point.
            sshkey=None,
            password=None,
            # We save the server id in the client to perform on it operations
            # related to this plugin.
            server_id=config_id,
            # This is necessary because it takes a while before getting a
            # response from the server with the kernel id that will be
            # associated to this client. So, if users could close it before
            # that then it'll not be possible to shutdown that kernel unless
            # the server is stopped as well.
            can_close=False,
        )

        # IMPORTANT NOTE: We use a signal here instead of calling directly
        # container.on_kernel_started because doing that generates segfaults
        # and odd issues (e.g. the Variable Explorer not working).
        future = self._start_new_kernel(config_id)
        future.add_done_callback(
            lambda future: self._sig_kernel_started.emit(
                ipyclient, future.result()
            )
        )

    # ---- Private API
    # -------------------------------------------------------------------------
    # --- Remote Server Kernel Methods
    @Slot(str)
    @AsyncDispatcher.dispatch(loop="asyncssh")
    async def get_kernels(self, config_id) -> list:
        """Get opened kernels."""
        if config_id in self._remote_clients:
            client = self._remote_clients[config_id]
            return await client.list_kernels()
        return []

    @AsyncDispatcher.dispatch(loop="asyncssh")
    async def _get_kernel_info(self, config_id, kernel_id) -> dict:
        """Get kernel info."""
        if config_id in self._remote_clients:
            client = self._remote_clients[config_id]
            return await client.get_kernel_info_ensure_server(kernel_id)
        return {}

    @AsyncDispatcher.dispatch(loop="asyncssh")
    async def _shutdown_kernel(self, config_id, kernel_id):
        """Shutdown a running kernel."""
        if config_id in self._remote_clients:
            client = self._remote_clients[config_id]
            with contextlib.suppress(Exception):
                await client.terminate_kernel(kernel_id)

    @AsyncDispatcher.dispatch(loop="asyncssh")
    async def _start_new_kernel(self, config_id):
        """Start new kernel."""
        if config_id not in self._remote_clients:
            self.load_client_from_id(config_id)

        client = self._remote_clients[config_id]
        return await client.start_new_kernel_ensure_server()

    @AsyncDispatcher.dispatch(loop="asyncssh")
    async def _restart_kernel(self, config_id, kernel_id) -> bool:
        """Restart kernel."""
        if config_id in self._remote_clients:
            client = self._remote_clients[config_id]
            with contextlib.suppress(Exception):
                return await client.restart_kernel(kernel_id)

        return False

    @AsyncDispatcher.dispatch(loop="asyncssh")
    async def _interrupt_kernel(self, config_id, kernel_id):
        """Interrupt kernel."""
        if config_id in self._remote_clients:
            client = self._remote_clients[config_id]
            await client.interrupt_kernel(kernel_id)

    def _reset_status(self):
        """Reset status of servers."""
        for config_id in self.get_config_ids():
            self.set_conf(f"{config_id}/status", ConnectionStatus.Inactive)
            self.set_conf(f"{config_id}/status_message", "")

    def _add_remote_consoles_menu(self):
        """Add remote consoles submenu to the Consoles menu."""
        container = self.get_container()
        container.setup_remote_consoles_submenu(render=False)

        menu = container.get_menu(RemoteClientMenus.RemoteConsoles)
        mainmenu = self.get_plugin(Plugins.MainMenu)
        mainmenu.add_item_to_application_menu(
            menu,
            menu_id=ApplicationMenus.Consoles,
            section=ConsolesMenuSections.New,
            before=IPythonConsoleWidgetActions.ConnectToKernel,
        )

        self._is_consoles_menu_added = True
