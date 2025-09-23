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
from __future__ import annotations
import logging
import typing

# Third-party imports
from qtpy.QtCore import Signal

# Local imports
from spyder.api.asyncdispatcher import AsyncDispatcher
from spyder.api.plugin_registration.decorators import (
    on_plugin_available,
    on_plugin_teardown,
)
from spyder.api.plugins import OptionalPlugins, Plugins, SpyderPluginV2
from spyder.api.translations import _
from spyder.plugins.mainmenu.api import (
    ApplicationMenus,
    ToolsMenuSections,
)
from spyder.plugins.remoteclient.api import (
    RemoteClientActions,
)
from spyder.plugins.remoteclient.api.manager.base import (
    SpyderRemoteAPIManagerBase,
)
from spyder.plugins.remoteclient.api.manager.jupyterhub import (
    SpyderRemoteJupyterHubAPIManager,
)
from spyder.plugins.remoteclient.api.manager.ssh import (
    SpyderRemoteSSHAPIManager,
)
from spyder.plugins.remoteclient.api.protocol import (
    ClientType,
    JupyterHubClientOptions,
    SSHClientOptions,
    ConnectionStatus,
)
from spyder.plugins.remoteclient.api.modules.file_services import (
    SpyderRemoteFileServicesAPI,
)
from spyder.plugins.remoteclient.api.modules.environ import (
    SpyderRemoteEnvironAPI,
)
from spyder.plugins.remoteclient.widgets import AuthenticationMethod
from spyder.plugins.remoteclient.widgets.container import RemoteClientContainer

if typing.TYPE_CHECKING:
    from spyder.plugins.remoteclient.api.modules.base import (
        SpyderBaseJupyterAPIType,
    )


_logger = logging.getLogger(__name__)


class RemoteClient(SpyderPluginV2):
    """
    Remote client plugin.
    """

    NAME = "remoteclient"
    OPTIONAL = [Plugins.MainMenu, OptionalPlugins.EnvManager]
    CONF_SECTION = NAME
    CONTAINER_CLASS = RemoteClientContainer
    CONF_FILE = False

    CONF_SECTION_SERVERS = "servers"

    # ---- Signals
    sig_server_stopped = Signal(str)
    sig_server_renamed = Signal(str)
    sig_server_changed = Signal()
    sig_client_message_logged = Signal(dict)

    sig_connection_established = Signal(str)
    sig_connection_lost = Signal(str)
    sig_connection_status_changed = Signal(dict)

    sig_version_mismatch = Signal(str, str)

    # For remote envs
    sig_create_env_requested = Signal(str, str, str, list)
    """
    Signal to request creating a Python environment in the remote machine.

    Parameters
    ----------
    config_id: str
        Machine identifier.
    env_name: str
        Environment name.
    python_version: str
        Python version of the environment.
    packages_list: list[str]
        List of packages.
    """

    sig_import_env_requested = Signal(str, str, str)
    """
    Signal to request importing a Python environment in the remote machine.

    Parameters
    ----------
    config_id: str
        Machine identifier.
    import_file_path: str
        Path to the file that will be used to import the environment.
    env_name: str
        Environment name.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self._remote_clients: dict[str, SpyderRemoteAPIManagerBase] = {}

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
        container = self.get_container()

        # Container signals
        container.sig_start_server_requested.connect(self.start_remote_server)
        container.sig_stop_server_requested.connect(self.stop_remote_server)
        container.sig_stop_server_requested.connect(self.sig_server_stopped)
        container.sig_server_renamed.connect(self.sig_server_renamed)
        container.sig_server_changed.connect(self.sig_server_changed)
        container.sig_server_updated.connect(self.load_client_from_id)

        # Plugin signals
        self.sig_connection_status_changed.connect(
            container.sig_connection_status_changed
        )
        self.sig_client_message_logged.connect(
            container.sig_client_message_logged
        )
        self.sig_version_mismatch.connect(container.on_server_version_mismatch)

    def on_first_registration(self):
        pass

    def on_close(self, cancellable=True):
        """Stops remote server and close any opened connection."""
        while self._remote_clients:
            client = self._remote_clients.popitem()[1]
            AsyncDispatcher(
                loop="asyncssh",
                early_return=False,
            )(client.close)()

    @on_plugin_available(plugin=Plugins.MainMenu)
    def on_mainmenu_available(self):
        mainmenu = self.get_plugin(Plugins.MainMenu)

        action = self.get_action(RemoteClientActions.ManageConnections)
        mainmenu.add_item_to_application_menu(
            action,
            menu_id=ApplicationMenus.Tools,
            section=ToolsMenuSections.Managers,
            before_section=ToolsMenuSections.Preferences,
        )

    @on_plugin_teardown(plugin=Plugins.MainMenu)
    def on_mainmenu_teardown(self):
        mainmenu = self.get_plugin(Plugins.MainMenu)

        mainmenu.remove_item_from_application_menu(
            RemoteClientActions.ManageConnections,
            menu_id=ApplicationMenus.Tools,
        )

    @on_plugin_available(plugin=OptionalPlugins.EnvManager)
    def on_envmanager_available(self):
        envmanager = self.get_plugin(OptionalPlugins.EnvManager)
        envmanager.sig_set_default_kernel_spec_requested.connect(
            self.set_default_kernel_spec
        )

    @on_plugin_teardown(plugin=OptionalPlugins.EnvManager)
    def on_envmanager_teardown(self):
        envmanager = self.get_plugin(OptionalPlugins.EnvManager)
        envmanager.sig_set_default_kernel_spec_requested.disconnect(
            self.set_default_kernel_spec
        )

    # ---- Public API
    # -------------------------------------------------------------------------
    # --- Remote Server Methods
    def get_remote_server(self, config_id):
        """Get remote server."""
        if config_id in self._remote_clients:
            return self._remote_clients[config_id]

    @AsyncDispatcher(loop="asyncssh")
    async def _install_remote_server(self, config_id):
        """Install remote server."""
        if config_id in self._remote_clients:
            client = self._remote_clients[config_id]
            await client.connect_and_install_remote_server()

    def start_remote_server(self, config_id):
        """Start remote server."""
        if config_id not in self._remote_clients:
            self.load_client_from_id(config_id)

        @AsyncDispatcher(loop="asyncssh")
        async def _start_client():
            client = self._remote_clients[config_id]
            await client.connect_and_ensure_server()
        _start_client()

    @AsyncDispatcher(loop="asyncssh")
    async def stop_remote_server(self, config_id):
        """Stop remote server."""
        if client := self._remote_clients.pop(config_id, None):
            await client.close()

    @AsyncDispatcher(loop="asyncssh")
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
        client_type = self.get_conf(
            f"{config_id}/client_type", default=ClientType.SSH
        )
        if client_type == ClientType.SSH:
            options = self._load_ssh_client_options(config_id)
            self.load_ssh_client(config_id, options)
        elif client_type == ClientType.JupyterHub:
            options = self._load_jupyterhub_client_options(config_id)
            self.load_jupyterhub_client(config_id, options)
        else:
            msg = (
                f"Unknown client type '{client_type}' for server "
                f"'{config_id}'. Please check your configuration."
            )
            raise ValueError(msg)

    def load_ssh_client(self, config_id: str, options: SSHClientOptions):
        """Load SSH remote server."""
        if config_id in self._remote_clients:
            self._remote_clients[config_id].options.update(options)
        else:
            self._remote_clients[config_id] = SpyderRemoteSSHAPIManager(
                config_id, options, _plugin=self
            )

        _logger.debug(
            "Remote SSH client for '%s' loaded with options: %s",
            config_id,
            options,
        )

    def load_jupyterhub_client(
        self, config_id: str, options: JupyterHubClientOptions,
    ):
        """Load JupyterHub remote server."""
        if config_id in self._remote_clients:
            self._remote_clients[config_id].options.update(options)
        else:
            self._remote_clients[config_id] = SpyderRemoteJupyterHubAPIManager(
                config_id, options, _plugin=self
            )

        _logger.debug(
            "Remote JupyterHub client for '%s' loaded with options: %s",
            config_id,
            options,
        )

    def _load_jupyterhub_client_options(self, config_id):
        """Load JupyterHub remote server configuration."""
        options = JupyterHubClientOptions(
            url=self.get_conf(f"{config_id}/url"),
            token=self.get_conf(f"{config_id}/token", secure=True)
        )

        return options

    def _load_ssh_client_options(self, config_id):
        """Load remote server configuration."""
        auth_method = self.get_conf(f"{config_id}/auth_method")

        options = SSHClientOptions(
            host=self.get_conf(
                f"{config_id}/{auth_method}/address"
            ),
            port=self.get_conf(f"{config_id}/{auth_method}/port"),
            username=self.get_conf(
                f"{config_id}/{auth_method}/username"
            ),
        )

        if client_keys := self.get_conf(f"{config_id}/keyfile", ""):
            options["client_keys"] = [client_keys]
            if passphrase := self.get_conf(
                f"{config_id}/passphrase", "", secure=True
            ):
                options["passphrase"] = passphrase
        elif config := self.get_conf(f"{config_id}/configfile"):
            options["config"] = config
        else:
            # Password is mandatory in this case
            password = self.get_conf(f"{config_id}/password", secure=True)
            options["password"] = password

        # Default for now
        options["platform"] = "linux"

        # Don't require the host to be known to connect to it
        options["known_hosts"] = None

        return SSHClientOptions(**options)

    def get_loaded_servers(self):
        """Get configured remote servers."""
        return self._remote_clients.keys()

    def get_config_ids(self):
        """Get configured remote servers ids."""
        return self.get_conf(self.CONF_SECTION_SERVERS, {}).keys()

    def get_server_name(self, config_id):
        """Get configured remote server name."""
        client_type = self.get_conf(
            f"{config_id}/client_type", default=ClientType.SSH
        )
        if client_type == ClientType.SSH:
            auth_method = self.get_conf(f"{config_id}/auth_method")
            return self.get_conf(f"{config_id}/{auth_method}/name")
        if client_type == ClientType.JupyterHub:
            return self.get_conf(
                f"{config_id}/{AuthenticationMethod.JupyterHub}/name"
            )

        msg = (
            f"Unknown client type '{client_type}' for server '{config_id}'. "
            f"Please check your configuration."
        )
        raise ValueError(msg)

    def set_default_kernel_spec(self, name: str, server_id: str):
        """Set the default kernel spec for a remote server.

        This method sets the default kernel spec for a remote server
        identified by `server_id`. The kernel spec is used to determine
        which kernel spec is used when starting a new console on that server.

        Parameters
        ----------
        name: str
            Name of the kernel spec to set as default.
        server_id: str
            Identifier of the remote server for which to set
            the default kernel spec.

        Raises
        ------
        ValueError
            If the server_id does not exist in the configuration.
        """
        configs = self.get_conf(self.CONF_SECTION_SERVERS, {})
        if server_id not in configs:
            msg = f"Configuration for remote server '{server_id}' not found."
            raise ValueError(msg)

        configs[server_id]["default_kernel_spec"] = name

        self.set_conf(self.CONF_SECTION_SERVERS, configs)

        if server_id in self._remote_clients:
            server_options = self._remote_clients[server_id].options
            server_options["default_kernel_spec"] = name

    # --- API Methods
    @staticmethod
    def register_api(kclass: typing.Type[SpyderBaseJupyterAPIType]):
        """
        Register Remote Client API.

        This method is used to register a new API class that will be used to
        interact with the remote server. It can be used as a decorator.

        Parameters
        ----------
        kclass: Type[SpyderBaseJupyterAPI]
            Class to be registered.

        Returns
        -------
        Type[SpyderBaseJupyterAPI]
            Class that was registered.
        """
        return SpyderRemoteAPIManagerBase.register_api(kclass)

    def get_api(
        self, config_id: str, api: str | typing.Type[SpyderBaseJupyterAPIType]
    ):
        """
        Get the API for a remote server.

        Get the registered API class for a given remote server.

        Parameters
        ----------
        config_id: str
            Configuration id of the remote server.
        api: str | Type[SpyderBaseJupyterAPI]
            API class to be retrieved.

        Returns
        -------
        SpyderBaseJupyterAPI
            API class instance.
        """
        if config_id not in self._remote_clients:
            self.load_client_from_id(config_id)

        client = self._remote_clients[config_id]

        return client.get_api(api)

    def get_file_api(self, config_id):
        """Get file API."""
        if config_id not in self._remote_clients:
            self.load_client_from_id(config_id)

        client = self._remote_clients[config_id]

        return client.get_api(SpyderRemoteFileServicesAPI)

    def get_environ_api(self, config_id):
        """Get environment API."""
        if config_id not in self._remote_clients:
            self.load_client_from_id(config_id)

        client = self._remote_clients[config_id]

        return client.get_api(SpyderRemoteEnvironAPI)

    def get_jupyter_api(self, config_id):
        """Get Jupyter API."""
        if config_id not in self._remote_clients:
            self.load_client_from_id(config_id)

        client = self._remote_clients[config_id]

        return client.get_jupyter_api()

    # ---- Private API
    # -------------------------------------------------------------------------
    # --- Remote Server Kernel Methods
    def _reset_status(self):
        """Reset status of servers."""
        for config_id in self.get_config_ids():
            self.set_conf(f"{config_id}/status", ConnectionStatus.Inactive)
            self.set_conf(f"{config_id}/status_message", "")
