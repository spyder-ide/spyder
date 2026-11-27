# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""
MCP server plugin.

Exposes to AI agents, through the Model Context Protocol,
the methods that plugins mark with :func:`spyder.api.plugins.expose`. Other
plugins don't depend on this one: it collects the exposed methods of every
plugin as they become available. The HTTP server runs in a subprocess, which
forwards tool calls to this plugin.
"""

# Standard library imports
import json
import logging
import secrets
import time

# Third-party imports
from qtpy.QtCore import Signal
from qtpy.QtWidgets import QApplication

# Local imports
from spyder.api.plugins import (
    Plugins,
    SpyderPluginV2,
    current_caller,
    expose,
)
from spyder.api.plugin_registration.decorators import (
    on_plugin_available,
    on_plugin_teardown,
)
from spyder.api.plugin_registration.registry import PLUGIN_REGISTRY
from spyder.api.translations import _
from spyder.plugins.mainmenu.api import ApplicationMenus, ToolsMenuSections
from spyder.plugins.mcpserver.api import MCPTool
from spyder.plugins.mcpserver.bridge import (
    CLIENT_ID_HEADER,
    CLIENT_NAME_HEADER,
    NOTES_PATH,
)
from spyder.plugins.mcpserver.client import MCPServerClient
from spyder.plugins.mcpserver.container import (
    MCPServerActions,
    MCPServerContainer,
)
from spyder.plugins.mcpserver.dispatcher import ArgumentAsker, ToolDispatcher
from spyder.plugins.mcpserver.exposed import tools_from_plugin
from spyder.utils.misc import select_port

logger = logging.getLogger(__name__)


class MCPServer(SpyderPluginV2):
    """MCP server plugin."""

    NAME = "mcp_server"
    OPTIONAL = [Plugins.MainMenu, Plugins.Projects]
    CONTAINER_CLASS = MCPServerContainer
    CONF_SECTION = NAME
    CONF_FILE = False

    sig_server_started = Signal(str)
    """
    This signal is emitted when the server is accepting connections.

    Parameters
    ----------
    url : str
        URL of the MCP endpoint.
    """

    sig_server_stopped = Signal()
    """This signal is emitted when the server stops."""

    # ---- SpyderPluginV2 API
    # -------------------------------------------------------------------------
    @staticmethod
    def get_name():
        return _("MCP server")

    @staticmethod
    def get_description():
        return _(
            "Let AI agents interact with Spyder through the Model Context "
            "Protocol."
        )

    @classmethod
    def get_icon(cls):
        return cls.create_icon("python")

    def on_initialize(self):
        self._tools: dict[str, MCPTool] = {}

        # Tool names and plugin instance of each plugin whose exposed
        # methods were collected
        self._collected: dict[str, tuple[list[str], int]] = {}

        self._dispatcher = ToolDispatcher(self._get_available_tools)

        # Port of the last server started, to restart it on the same one
        self._server_port: int | None = None
        self._restarts: list[float] = []

        # Value of the "enabled" option last applied, since Spyder also
        # notifies options that didn't change (e.g. when it sets the main
        # interpreter)
        self._enabled = self.get_conf("enabled")

        # Whether other plugins started the server for their own clients
        # (e.g. agent sessions), so it keeps running for them
        self._used_by_plugins = False
        self._client = MCPServerClient(
            self,
            self._get_available_tools,
            self._dispatcher.call,
            self._dispatcher.take_notes,
        )
        self._client.sig_server_ready.connect(self._on_server_ready)
        self._client.sig_server_stopped.connect(self._on_server_stopped)

        container = self.get_container()
        container.sig_enabled_changed.connect(self._on_enabled_changed)
        container.sig_copy_config_requested.connect(self.copy_config)

        PLUGIN_REGISTRY.sig_plugin_ready.connect(self._on_plugin_ready)
        self._collect_available_plugins()

    def on_mainwindow_visible(self):
        self._collect_available_plugins()
        if self.get_conf("enabled"):
            self._start_server()

    def on_close(self, cancelable=False):
        try:
            PLUGIN_REGISTRY.sig_plugin_ready.disconnect(self._on_plugin_ready)
        except (TypeError, RuntimeError):
            pass
        self.stop_server()

    @on_plugin_available(plugin=Plugins.MainMenu)
    def on_main_menu_available(self):
        main_menu = self.get_plugin(Plugins.MainMenu)
        container = self.get_container()
        for action in [
            container.toggle_server_action,
            container.copy_config_action,
        ]:
            main_menu.add_item_to_application_menu(
                action,
                menu_id=ApplicationMenus.Tools,
                section=ToolsMenuSections.Managers,
                before_section=ToolsMenuSections.Preferences,
            )

    @on_plugin_teardown(plugin=Plugins.MainMenu)
    def on_main_menu_teardown(self):
        main_menu = self.get_plugin(Plugins.MainMenu)
        for action_id in [
            MCPServerActions.ToggleServer,
            MCPServerActions.CopyConfig,
        ]:
            main_menu.remove_item_from_application_menu(
                action_id, menu_id=ApplicationMenus.Tools
            )

    @on_plugin_available(plugin=Plugins.Projects)
    def on_projects_available(self):
        projects = self.get_plugin(Plugins.Projects)
        projects.sig_project_loaded.connect(self._on_project_loaded)
        projects.sig_project_closed.connect(self._on_project_closed)

    @on_plugin_teardown(plugin=Plugins.Projects)
    def on_projects_teardown(self):
        projects = self.get_plugin(Plugins.Projects)
        projects.sig_project_loaded.disconnect(self._on_project_loaded)
        projects.sig_project_closed.disconnect(self._on_project_closed)

    # ---- Public API
    # -------------------------------------------------------------------------
    def register_tool(self, tool: MCPTool) -> None:
        """
        Make ``tool`` available to AI agents.

        Parameters
        ----------
        tool : MCPTool
            Tool to register. Its name must be unique.
        """
        if tool.name in self._tools:
            raise ValueError(f"MCP tool {tool.name!r} is already registered")
        self._tools[tool.name] = tool

    def unregister_tool(self, name: str) -> None:
        """Remove the tool called ``name``."""
        self._tools.pop(name, None)

    def get_tools(self) -> list[MCPTool]:
        """Return the tools available to agents."""
        return list(self._get_available_tools().values())

    def register_client(self, client_id: str, name: str) -> None:
        """
        Register a client before it calls any tool (e.g. an agent session a
        plugin starts), so it gets notes about what happens in Spyder from
        the start.
        """
        self._dispatcher.register_client(client_id, name)

    def unregister_client(self, client_id: str) -> None:
        """Forget a client, e.g. when its agent session ends."""
        self._dispatcher.unregister_client(client_id)

    def notify_clients(self, message: str, exclude: str | None = None) -> None:
        """
        Tell clients (except ``exclude``, e.g. the one that caused it) about
        something that happened in Spyder that may affect them. They get it
        with the result of their next tool call, or from the endpoint at
        :meth:`get_notes_url`.
        """
        self._dispatcher.notify_clients(message, exclude)

    def get_notes_url(self) -> str | None:
        """
        URL where clients get their notes outside of tool calls (e.g. from
        an agent's hooks), with ``?client=<id>`` and the same authorization
        header as the MCP endpoint. ``None`` if the server isn't running.
        """
        url = self.get_url()
        if url is None:
            return None
        return url.rsplit("/", 1)[0] + NOTES_PATH

    @expose(read_only=True)
    def list_agent_sessions(self) -> list:
        """
        List the AI agent sessions connected to Spyder, including yours,
        with their name and whether they're running a Spyder tool now. Use
        it to coordinate with them, e.g. before restarting a console or
        opening a project, which affect everyone. list_consoles shows which
        consoles each one runs code in.
        """
        caller = current_caller()
        sessions = []
        for client in self._dispatcher.get_clients():
            you = caller is not None and client.id == caller.id
            # Your own call to this tool doesn't count
            running = self._dispatcher.get_running_calls(client.id) - you
            sessions.append(
                {"name": client.name, "you": you, "busy": running > 0}
            )
        return sessions

    def get_clients(self) -> list:
        """
        Return the clients (e.g. agent sessions) that have called
        tools, as :class:`spyder.api.plugins.Caller` objects.
        """
        return self._dispatcher.get_clients()

    def set_client_argument(self, client_id: str, name: str, value) -> None:
        """
        Set the value of a tool argument used by default when a client
        doesn't give it, e.g. ``console_id`` for the console an agent session
        works in. ``None`` removes it.

        Parameters
        ----------
        client_id : str
            Id of the client, as sent in the ``X-Spyder-Client-Id`` header.
        name : str
            Name of the argument.
        value : Any
            Its value, or ``None`` to remove it.
        """
        self._dispatcher.set_client_argument(client_id, name, value)

    def get_client_argument(self, client_id: str, name: str):
        """Return the default value of a tool argument for a client."""
        return self._dispatcher.get_client_argument(client_id, name)

    def get_busy_clients(self) -> set:
        """
        Return the ids of the clients with tool calls running, e.g. to ask
        the user before closing an agent session that is working.
        """
        return self._dispatcher.get_busy_clients()

    def register_argument_asker(
        self, name: str, asker: ArgumentAsker | None
    ) -> None:
        """
        Set a function that asks the user for the value of a tool argument
        when a client calls a tool that changes state without giving it and
        without a default (e.g. which console an agent session should
        run code in). ``None`` removes it.

        See :data:`spyder.plugins.mcpserver.dispatcher.ArgumentAsker`.
        """
        self._dispatcher.register_argument_asker(name, asker)

    def start_server(self) -> None:
        """
        Start the MCP server subprocess for a plugin's clients (e.g. agent
        sessions).

        It keeps running while Spyder runs, even if the user turns off the
        option to enable it (which only controls whether it starts with
        Spyder for other agents).
        """
        self._used_by_plugins = True
        self._start_server()

    def _start_server(self, port: int | None = None) -> None:
        """
        Start the MCP server subprocess.

        Parameters
        ----------
        port : int, optional
            Port to use if it's free. By default, the one in the settings.
        """
        token = self.get_conf("token")
        if not token:
            token = secrets.token_urlsafe(32)
            self.set_conf("token", token)

        if port is None:
            port = self.get_conf("port")
        free_port = select_port(default_port=port)
        if free_port != port:
            logger.warning(
                "Port %s is in use, starting the MCP server on port %s. "
                "Agents configured with the old port need to be updated.",
                port,
                free_port,
            )

        self._server_port = free_port
        self._client.start(self.get_conf("host"), free_port, token)

    def stop_server(self) -> None:
        """Stop the MCP server subprocess."""
        self._client.stop()

    def is_server_running(self) -> bool:
        """Whether the server is running and accepting connections."""
        return self._client.url is not None

    def get_url(self) -> str | None:
        """Return the URL of the MCP endpoint if the server is running."""
        return self._client.url

    def get_connection_info(
        self,
        client_id: str | None = None,
        client_name: str | None = None,
    ) -> dict | None:
        """
        Return the information needed to connect to the server, or ``None``
        if it's not running.

        Parameters
        ----------
        client_id : str, optional
            Unique id of the client (e.g. an agent session), sent with its
            tool calls so tools can tell clients apart. Clients without one
            are identified by their MCP session.
        client_name : str, optional
            Name of the client shown to users, e.g. ``Agent 2``.

        Returns
        -------
        dict
            With the ``url`` of the endpoint and the HTTP ``headers`` to send.
        """
        url = self.get_url()
        if url is None:
            return None

        headers = {"Authorization": f"Bearer {self.get_conf('token')}"}
        if client_id is not None:
            headers[CLIENT_ID_HEADER] = client_id
            if client_name is not None:
                headers[CLIENT_NAME_HEADER] = client_name
        return {"url": url, "headers": headers}

    def get_config(self) -> dict | None:
        """
        Return the configuration that agents use to connect to the server,
        in the ``mcpServers`` format that most of them read, or ``None`` if
        it isn't running.
        """
        info = self.get_connection_info()
        if info is None:
            return None
        return {
            "mcpServers": {
                "spyder": {
                    "type": "http",
                    "url": info["url"],
                    "headers": info["headers"],
                }
            }
        }

    def copy_config(self) -> None:
        """Copy the configuration to connect to the server, as JSON."""
        config = self.get_config()
        if config is not None:
            QApplication.clipboard().setText(json.dumps(config, indent=2))

    # ---- Private API
    # -------------------------------------------------------------------------
    def _get_available_tools(self) -> dict[str, MCPTool]:
        """Return the tools whose plugin is available, by name."""
        return {
            name: tool
            for name, tool in self._tools.items()
            if tool.plugin is None
            or PLUGIN_REGISTRY.is_plugin_available(tool.plugin)
        }

    def _on_plugin_ready(self, plugin_name: str, omit_conf: bool) -> None:
        self._collect_tools(plugin_name)

    def _collect_available_plugins(self) -> None:
        for plugin_name in list(PLUGIN_REGISTRY):
            if PLUGIN_REGISTRY.is_plugin_available(plugin_name):
                self._collect_tools(plugin_name)

    def _collect_tools(self, plugin_name: str) -> None:
        """Register the exposed methods of a plugin as tools."""
        try:
            plugin = PLUGIN_REGISTRY.get_plugin(plugin_name)
        except Exception:
            return

        # Plugins can be recreated (e.g. after disabling and enabling them),
        # so collect them again if their instance changed
        names, instance_id = self._collected.get(plugin_name, ([], None))
        if instance_id == id(plugin):
            return
        for name in names:
            self.unregister_tool(name)

        names = []
        for tool in tools_from_plugin(plugin, plugin_name):
            if tool.name in self._tools:
                logger.error(
                    "Can't expose %s to agents from plugin %s: another "
                    "plugin already exposes a method with that name. Use "
                    "expose(name=...) to give it a different one.",
                    tool.name,
                    plugin_name,
                )
                continue
            self.register_tool(tool)
            names.append(tool.name)

        self._collected[plugin_name] = (names, id(plugin))
        if names:
            logger.debug(
                "Exposed to agents from %s: %s", plugin_name, ", ".join(names)
            )

    def _on_enabled_changed(self, enabled: bool) -> None:
        if enabled == self._enabled:
            return
        self._enabled = enabled
        if enabled:
            self._start_server()
        elif not self._used_by_plugins:
            self.stop_server()

    def _on_server_ready(self, url: str) -> None:
        self.get_container().set_server_running(True)
        self.sig_server_started.emit(url)

    def _on_server_stopped(self, returncode: int) -> None:
        self.get_container().set_server_running(False)
        self.sig_server_stopped.emit()

        # Restart it if it exited without being stopped (the client logs
        # why), on the same port so connected agents can reconnect. Give up
        # if it keeps exiting.
        if not self._client.exited_unexpectedly:
            return
        now = time.monotonic()
        self._restarts = [t for t in self._restarts if now - t < 60]
        if len(self._restarts) >= 3:
            logger.error(
                "The MCP server keeps exiting, so it won't be restarted."
            )
            return
        self._restarts.append(now)
        logger.warning("Restarting the MCP server")
        self._start_server(port=self._server_port)

    # ---- Notes about Spyder's state for agents
    # -------------------------------------------------------------------------
    @staticmethod
    def _describe_actor() -> tuple[str, str | None]:
        """Who is doing what Spyder is doing now, and their client id."""
        caller = current_caller()
        if caller is None:
            return "The user", None
        return caller.name, caller.id

    def _on_project_loaded(self, path: str) -> None:
        projects = self.get_plugin(Plugins.Projects, error=False)
        if projects is not None and projects.get_active_project_path():
            path = projects.get_active_project_path()
        who, client_id = self._describe_actor()

        self.notify_clients(
            f"{who} opened the project {path}. Opening a project restarts "
            f"Spyder's IPython consoles, so the variables, imports and "
            f"figures created in them before are probably gone: check "
            f"list_consoles and list_variables before relying on earlier "
            f"results.",
            exclude=client_id,
        )

    def _on_project_closed(self, path) -> None:
        if not isinstance(path, str) or not path:
            return
        who, client_id = self._describe_actor()

        self.notify_clients(
            f"{who} closed the project {path}. Closing a project restarts "
            f"Spyder's IPython consoles, so the variables, imports and "
            f"figures created in them before are probably gone.",
            exclude=client_id,
        )
